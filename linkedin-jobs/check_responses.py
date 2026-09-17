#!/usr/bin/env python3
"""
Check applied/saved jobs on LinkedIn and cross-reference with search results.
Does NOT claim to detect recruiter replies — LinkedIn blocks automated access
to messaging/notifications. Provides direct links for manual checking.

Usage:
  D:\\Conda\\python.exe check_responses.py
  D:\\Conda\\python.exe check_responses.py --json-only   # skip HTML
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.txt"
OUTPUT_FILE = SKILL_DIR / "responses.json"
MATCHED_JSON = SKILL_DIR / "matched_jobs.json"
RESPONSES_HTML = SKILL_DIR / "职位回复列表.html"

# ---- cookie parsing ----

def parse_cookies(filepath):
    cookies = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("curl") or line.startswith("-"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            name = parts[0].strip()
            value = parts[1].strip()
            domain = parts[2].strip()
            path = parts[3].strip() if len(parts) > 3 else "/"
            expires_str = parts[4].strip()
            secure = parts[8].strip() if len(parts) > 8 else ""
            http_only = parts[7].strip() if len(parts) > 7 else ""

            expires = -1
            if expires_str and expires_str != "会话":
                try:
                    dt = datetime.strptime(
                        expires_str.replace("T", " ").split(".")[0],
                        "%Y-%m-%d %H:%M:%S"
                    )
                    expires = int(dt.timestamp())
                except ValueError:
                    pass

            cookie = {
                "name": name,
                "value": value,
                "domain": domain.lstrip("."),
                "path": path,
                "httpOnly": "✓" in http_only,
                "secure": "✓" in secure,
                "sameSite": "None",
            }
            if expires > 0:
                cookie["expires"] = expires
            cookies.append(cookie)
    return cookies


# ---- categorization ----

GENERIC_PATTERNS = [
    "general interest", "general apply", "general consideration",
    "general opportunity", "general employment", "general job app",
    "general resume", "general submission",
    "any position", "submit a resume", "submit your resume",
    "submit your application", "upload your resume",
    "join our talent community", "join the", "dream team",
    "stay in touch", "keep me in mind",
    "future opportunities", "future open positions", "future open",
    "interested in future", "open submission", "open resume submission",
    "create your own role", "all other roles",
    "don't see", "don't fit", "no perfect role", "not see a current",
    "not posted yet", "reach out anyway",
    "resume inbox", "spontaneous application",
    "expressed interest", "expression of interest", "intrigued? apply",
    "apply now", "apply anyway", "apply anyways",
    "apply here", "click here", "property meld join our team",
    "adpro - if you don't", "early career opportunities",
]


def categorize(title):
    """Tag an entry as 'specific' (real job) or 'talent_community' (open submission)."""
    t = title.lower().strip()
    for kw in GENERIC_PATTERNS:
        if kw in t:
            return "talent_community"
    return "specific"


# ---- page scrapers ----

def _scroll_and_find_cards(page):
    """Scroll to load all lazy content, return card elements."""
    last_count = 0
    for i in range(12):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.2)
        try:
            buttons = page.query_selector_all("button")
            for btn in buttons:
                text = (btn.inner_text() or "").lower()
                if "show more" in text or "see more" in text or "load more" in text:
                    btn.click()
                    time.sleep(2)
                    break
        except Exception:
            pass
        current = len(page.query_selector_all(".job-card-container, .scaffold-layout__list-item, [data-job-id]"))
        if current == last_count and i >= 4:
            break
        last_count = current

    card_selectors = [
        ".jobs-my-job-list__item",
        ".jobs-applied-job-item",
        ".job-card-container",
        ".scaffold-layout__list-item",
        "li.jobs-search-results__list-item",
        "[data-job-id]",
        ".job-search-card",
        ".base-search-card",
        ".artdeco-card",
    ]
    for sel in card_selectors:
        cards = page.query_selector_all(sel)
        if cards and len(cards) > 3:
            return cards, sel
    return [], ""


def _extract_cards(cards, source_tag, max_cards):
    """Parse card elements into job dicts."""
    results = []
    processed = 0
    for card in cards:
        if processed >= max_cards:
            break
        try:
            title_el = (
                card.query_selector(".job-card-list__title") or
                card.query_selector(".base-search-card__title") or
                card.query_selector(".job-card-container__link") or
                card.query_selector("h3") or
                card.query_selector("a")
            )
            title = title_el.inner_text().strip() if title_el else ""
            if not title:
                continue

            company_el = (
                card.query_selector(".job-card-container__company-name") or
                card.query_selector(".base-search-card__subtitle") or
                card.query_selector(".artdeco-entity-lockup__subtitle") or
                card.query_selector("h4")
            )
            company = company_el.inner_text().strip() if company_el else ""

            link_el = card.query_selector("a")
            url_out = ""
            if link_el:
                href = link_el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = "https://www.linkedin.com" + href
                url_out = href.split("?")[0]

            job_id = ""
            jid_match = re.search(r'/jobs/view/(\d+)', url_out)
            if jid_match:
                job_id = jid_match.group(1)

            results.append({
                "title": title,
                "company": company,
                "url": url_out,
                "job_id": job_id,
                "category": categorize(title),
                "source": source_tag,
            })
            processed += 1
        except Exception:
            continue
    return results


def scrape_current_page(page, label, source_tag, max_cards=200):
    """Scrape cards from the current page (no navigation)."""
    print(f"\n[{label}] 解析当前页面...")
    cards, sel = _scroll_and_find_cards(page)
    if not cards:
        body_text = page.inner_text("body")[:800]
        print(f"    卡片不足, 页面文本: {body_text[:400]}")
        return []
    print(f"    找到 {len(cards)} 张卡片 (selector: {sel})")
    results = _extract_cards(cards, source_tag, max_cards)
    specific = sum(1 for r in results if r["category"] == "specific")
    community = sum(1 for r in results if r["category"] == "talent_community")
    print(f"    提取 {len(results)} 条 (具体岗位 {specific}, 人才社区 {community})")
    return results


def scrape_job_list(page, url, label, source_tag, max_cards=200):
    """Navigate to a LinkedIn job list page and scrape all cards."""
    print(f"\n[{label}] 访问 {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=25000)
    time.sleep(4)

    current_url = page.url.lower()
    print(f"    URL: {current_url[:100]}")
    if "login" in current_url or "sign-in" in current_url:
        print("    ❌ 需要重新登录")
        return []
    page_text = page.inner_text("body")[:500].lower()
    if "登录以查看" in page_text or "sign in to see" in page_text:
        print("    ❌ 页面要求登录（Cookie 无效）")
        return []

    return scrape_current_page(page, label, source_tag, max_cards)


def check_notifications(page):
    """Try to fetch notifications via LinkedIn's Voyager API (in-browser fetch)."""
    results = []
    print("\n[通知] 尝试 Voyager API...")

    try:
        # Extract CSRF token — LinkedIn stores it in JSESSIONID cookie
        csrf_token = page.evaluate("""
            () => {
                // Try meta tag first
                const meta = document.querySelector('meta[name="csrf-token"]');
                if (meta && meta.content) return meta.content;
                // Try window globals
                if (window.csrf_token) return window.csrf_token;
                // Fallback: JSESSIONID from cookie
                const match = document.cookie.match(/JSESSIONID="?([^";]+)"?/);
                if (match) return match[1].replace(/^ajax:/, '');
                return '';
            }
        """)
        print(f"    CSRF token: {csrf_token[:30] if csrf_token else '(空)'}...")

        resp = page.evaluate("""
            async (csrfToken) => {
                try {
                    const headers = {
                        'Accept': 'application/vnd.linkedin.normalized+json+2.1',
                        'x-restli-protocol-version': '2.0.0',
                        'csrf-token': csrfToken,
                    };
                    // Try the notifications API via the newer endpoint
                    let resp = await fetch(
                        'https://www.linkedin.com/voyager/api/notifications?count=30&start=0',
                        { headers, credentials: 'include' }
                    );
                    if (resp.ok) return await resp.json();
                    // Fallback: try messaging conversations
                    resp = await fetch(
                        'https://www.linkedin.com/voyager/api/messaging/conversations?q=recent&count=20',
                        { headers, credentials: 'include' }
                    );
                    if (resp.ok) {
                        const data = await resp.json();
                        return { _fallback: 'messaging', elements: data.elements || [] };
                    }
                    return { _error: 'HTTP ' + resp.status };
                } catch(e) {
                    return { _error: e.message };
                }
            }
        """, csrf_token)

        if resp and not resp.get("_error"):
            elements = resp.get("elements", resp.get("data", []))
            if not elements:
                elements = resp.get("included", [])
            print(f"    API 返回 {len(elements)} 条通知")
            for item in elements[:30]:
                try:
                    # Voyager format: actor, body, createdDate
                    actor = item.get("actor", item.get("*actor", {}))
                    actor_name = ""
                    if isinstance(actor, dict):
                        actor_name = actor.get("name", actor.get("miniName", ""))
                        if isinstance(actor_name, dict):
                            actor_name = actor_name.get("text", "")
                    if isinstance(actor, str):
                        actor_name = actor

                    body = item.get("body", item.get("message", ""))
                    if isinstance(body, dict):
                        body = body.get("text", "")

                    created = item.get("createdDate", item.get("created", ""))
                    if isinstance(created, dict):
                        created = created.get("text", "")

                    combined = f"{actor_name} {body}".lower()
                    is_job_related = any(kw in combined for kw in [
                        "applied", "application", "viewed", "position",
                        "recruiter", "hiring", "message", "opportunity",
                        "interview", "offer", "interested",
                        "投递", "申请", "查看", "招聘", "面试", "消息", "回复",
                    ])

                    if actor_name or body:
                        results.append({
                            "sender": str(actor_name)[:80] if actor_name else "LinkedIn",
                            "preview": str(body)[:200] if body else "",
                            "time": str(created) if created else "",
                            "is_recruiter": is_job_related,
                            "source": "voyager-api",
                            "url": "",
                        })
                except Exception:
                    continue
        else:
            print(f"    API 错误: {resp.get('_error', 'unknown')}")
    except Exception as e:
        print(f"    API 异常: {str(e)[:120]}")

    recruiter_count = sum(1 for r in results if r.get("is_recruiter"))
    print(f"    职位相关通知: {recruiter_count} / 共 {len(results)} 条")
    return results


# ---- HTML generation ----

def generate_html(applied, saved, notifications, cross_refs):
    """Generate HTML report. Honest about what we can/cannot detect."""
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    specific_applied = [a for a in applied if a["category"] == "specific"]
    community_applied = [a for a in applied if a["category"] == "talent_community"]
    specific_saved = [s for s in saved if s["category"] == "specific"]
    community_saved = [s for s in saved if s["category"] == "talent_community"]

    def card_html(entry, border_color):
        badge = ""
        if entry["category"] == "talent_community":
            badge = '<span style="background:#6e7681;color:#fff;font-size:10px;padding:1px 6px;border-radius:4px;">人才社区</span>'
        url = entry.get("url", "#")
        return f"""
        <div class="card" style="border-left:3px solid {border_color};">
            <div class="card-title">
                <a href="{url}" target="_blank">{entry.get("title", "?")}</a> {badge}
            </div>
            <div class="card-meta">
                <span>{entry.get("company", "?")}</span>
            </div>
        </div>"""

    applied_cards = "".join(card_html(a, "#d29922") for a in applied[:100])
    saved_cards = "".join(card_html(s, "#30363d") for s in saved[:100])
    cross_cards = ""
    for ref in cross_refs[:30]:
        color = "#3fb950" if ref["match_type"] == "applied" else "#58a6ff"
        label = "已投递" if ref["match_type"] == "applied" else "已保存"
        url = ref.get("applied_url") or ref.get("saved_url") or ref.get("search_url", "#")
        cross_cards += f"""
        <div class="card" style="border-left:3px solid {color};">
            <div class="card-title">
                <a href="{ref.get('search_url', '#')}" target="_blank">{ref.get('search_title', '?')}</a>
                <span style="color:{color};font-size:12px;font-weight:600;">{label}</span>
            </div>
            <div class="card-meta">
                <span>{ref.get('company', '?')} · 评分 {ref.get('score', 0)}</span>
            </div>
        </div>"""

    notif_cards = ""
    recruiter_notifs = [n for n in notifications if n.get("is_recruiter")]
    for n in recruiter_notifs[:10]:
        notif_cards += f"""
        <div class="card" style="border-left:3px solid #f85149;">
            <div class="card-title">{n.get('sender', '?')}</div>
            <div class="card-preview">{n.get('preview', '')[:150]}</div>
            <div class="card-meta"><span>{n.get('time', '')}</span></div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LinkedIn 申请追踪 — {date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif; background:#0d1117; color:#c9d1d9; padding:20px; max-width:1000px; margin:0 auto; }}
h1 {{ color:#58a6ff; font-size:22px; margin-bottom:4px; }}
.subtitle {{ color:#8b949e; font-size:13px; margin-bottom:20px; }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }}
.stat {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px 16px; text-align:center; min-width:80px; }}
.stat-num {{ font-size:26px; font-weight:700; }}
.stat-label {{ font-size:11px; color:#8b949e; margin-top:2px; }}
.stat-ok .stat-num {{ color:#3fb950; }}
.stat-warn .stat-num {{ color:#d29922; }}
.stat-alert .stat-num {{ color:#f85149; }}
.section {{ margin-bottom:24px; }}
.section-title {{ font-size:16px; font-weight:600; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid #21262d; }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 14px; margin-bottom:6px; }}
.card:hover {{ border-color:#58a6ff; }}
.card-title {{ font-size:14px; font-weight:600; margin-bottom:4px; }}
.card-title a {{ color:#58a6ff; text-decoration:none; }}
.card-title a:hover {{ text-decoration:underline; }}
.card-meta {{ font-size:12px; color:#8b949e; }}
.card-preview {{ font-size:13px; color:#8b949e; margin:4px 0; line-height:1.5; }}
.note {{ background:#1a1f2b; border:1px solid #30363d; border-radius:8px; padding:14px; margin-bottom:20px; font-size:13px; color:#8b949e; }}
.note a {{ color:#58a6ff; }}
.footer {{ text-align:center; color:#484f58; font-size:11px; margin-top:40px; padding:20px; }}
</style>
</head>
<body>
<h1>LinkedIn 申请追踪</h1>
<div class="subtitle">更新于 {date_str}</div>

<div class="note">
    此页面展示你在 LinkedIn 上的投递记录。<br>
    查看招聘者回复请直接打开
    <a href="https://www.linkedin.com/messaging/" target="_blank">LinkedIn 消息</a> 或
    <a href="https://www.linkedin.com/notifications/" target="_blank">通知页面</a>。
</div>

<div class="stats">
<div class="stat stat-warn"><div class="stat-num">{len(specific_applied)}</div><div class="stat-label">具体岗位投递</div></div>
<div class="stat"><div class="stat-num">{len(community_applied)}</div><div class="stat-label">人才社区投递</div></div>
<div class="stat stat-ok"><div class="stat-num">{len(cross_refs)}</div><div class="stat-label">匹配搜索结果</div></div>
<div class="stat stat-alert"><div class="stat-num">{len(recruiter_notifs)}</div><div class="stat-label">招聘相关通知</div></div>
</div>

{f'''<div class="section"><div class="section-title">搜索结果中已投递/保存的岗位 ({len(cross_refs)})</div>{cross_cards}</div>''' if cross_cards else ''}

{f'''<div class="section"><div class="section-title">已投递 - 具体岗位 ({len(specific_applied)})</div>{applied_cards if specific_applied else '<div class="card"><div class="card-meta">无具体岗位投递记录</div></div>'}</div>''' if applied else ''}

{f'''<div class="section"><div class="section-title">已投递 - 人才社区 ({len(community_applied)})</div>{''.join(card_html(a, '#30363d') for a in community_applied[:30])}</div>''' if community_applied else ''}

{f'''<div class="section"><div class="section-title">已保存 ({len(saved)})</div>{saved_cards}</div>''' if saved else ''}

{f'''<div class="section"><div class="section-title">招聘相关通知</div>{notif_cards if notif_cards else '<div class="card"><div class="card-meta">未检测到招聘相关通知</div></div>'}</div>'''}

<div class="footer">
    点击职位标题在新标签页查看详情 · 确保 Chrome 已登录 LinkedIn
</div>
</body>
</html>"""

    with open(RESPONSES_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML 已保存: {RESPONSES_HTML}")


# ---- cross-reference with search results ----

def cross_reference(searched_jobs, applied_jobs, saved_jobs):
    """Match applied/saved jobs against search results by company name."""
    def norm(name):
        if not name:
            return ""
        n = name.strip().lower()
        for suffix in [' inc', ' inc.', ' llc', ' llc.', ' ltd', ' ltd.',
                       ' corp', ' corp.', ' limited', ' co.', ' co',
                       ' plc', ' gmbh', ' s.l.', ' s.a.', ' pte', ', inc.']:
            if n.endswith(suffix):
                n = n[:-len(suffix)]
        return n.strip()

    refs = []
    applied_norm = {norm(a["company"]): a for a in applied_jobs if a["company"]}
    saved_norm = {norm(s["company"]): s for s in saved_jobs if s["company"]}

    for job in searched_jobs:
        cn = norm(job.get("company", ""))
        if not cn:
            continue
        if cn in applied_norm:
            refs.append({
                "search_title": job.get("title", ""),
                "search_url": job.get("url", ""),
                "company": job.get("company", ""),
                "score": job.get("score", 0),
                "match_type": "applied",
                "applied_url": applied_norm[cn].get("url", ""),
            })
        elif cn in saved_norm:
            refs.append({
                "search_title": job.get("title", ""),
                "search_url": job.get("url", ""),
                "company": job.get("company", ""),
                "score": job.get("score", 0),
                "match_type": "saved",
                "saved_url": saved_norm[cn].get("url", ""),
            })

    refs.sort(key=lambda r: r["score"], reverse=True)
    return refs


# ---- main ----

def main(skip_html=False):
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    print("=" * 60)
    print("  LinkedIn 申请追踪")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    cookies = parse_cookies(str(COOKIE_FILE))
    print(f"\n[0] 加载 {len(cookies)} 个 cookies")

    applied_jobs = []
    saved_jobs = []
    notifications = []

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        # Add cookies one by one to identify any bad ones
        good = 0
        for c in cookies:
            try:
                context.add_cookies([c])
                good += 1
            except Exception:
                print(f"    跳过无效 cookie: {c.get('name', '?')} (domain={c.get('domain', '?')})")
        print(f"    成功添加 {good}/{len(cookies)} 个 cookies")

        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        # Try multiple approaches to establish session.
        # LinkedIn's feed page sometimes blocks automation even with valid cookies.
        print("    建立 session...")

        # Approach: go to the applied jobs page directly. If it works, we're logged in.
        # The page itself is the best login check — private pages show "登录以查看" when logged out.
        page.goto("https://www.linkedin.com/jobs/my-jobs/applied-jobs/", wait_until="domcontentloaded", timeout=25000)
        time.sleep(4)

        current_url = page.url.lower()
        page_text = page.inner_text("body")[:1000].lower()
        print(f"    URL: {current_url[:80]}")

        # Detect login wall on the applied jobs page itself
        if "login" in current_url or "sign-in" in current_url:
            print(f"    ❌ Cookie 已失效 (redirect to login)")
            print(f"    步骤: Chrome → F12 → Application → Cookies → 全选 → 复制 → 粘贴到 cookies.txt")
            browser.close()
            pw.stop()
            return
        if any(phrase in page_text for phrase in [
            "登录以查看", "sign in to see",
            "您已退出登录", "you've been logged out", "logged out",
            "登录领英，体验完整功能",
        ]):
            print(f"    ❌ Cookie 已失效 (页面显示已退出登录)")
            print(f"    步骤: Chrome 打开 linkedin.com → 登录 → F12 → Application → Cookies → 全选 → 复制")
            browser.close()
            pw.stop()
            return

        print(f"    Session OK — applied jobs page accessible")

        # 1. Applied jobs — we're already on this page after session check
        applied_jobs = scrape_current_page(page, "已投递", "applied", max_cards=200)

        # 2. Saved jobs
        saved_jobs = scrape_job_list(
            page,
            "https://www.linkedin.com/jobs/my-jobs/saved-jobs/",
            "已保存", "saved", max_cards=200
        )

        # 3. Notifications via Voyager API
        notifications = check_notifications(page)

        browser.close()
    finally:
        pw.stop()

    # Save JSON
    output = {
        "applied": applied_jobs,
        "saved": saved_jobs,
        "notifications": notifications,
        "checked_at": datetime.now().isoformat(),
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 已保存: {OUTPUT_FILE}")

    # Cross-reference with search results
    searched_jobs = []
    if MATCHED_JSON.exists():
        with open(MATCHED_JSON, 'r', encoding='utf-8') as f:
            searched_jobs = json.load(f)
    cross_refs = cross_reference(searched_jobs, applied_jobs, saved_jobs)

    # Generate HTML (unless --json-only)
    if not skip_html:
        generate_html(applied_jobs, saved_jobs, notifications, cross_refs)
    else:
        print("    (--json-only: 跳过 HTML 生成)")

    # Summary
    specific_applied = [a for a in applied_jobs if a["category"] == "specific"]
    community_applied = [a for a in applied_jobs if a["category"] == "talent_community"]
    specific_saved = [s for s in saved_jobs if s["category"] == "specific"]
    community_saved = [s for s in saved_jobs if s["category"] == "talent_community"]

    print(f"\n{'=' * 60}")
    print(f"  汇总:")
    print(f"    已投递-具体岗位: {len(specific_applied)}")
    print(f"    已投递-人才社区: {len(community_applied)}")
    print(f"    已保存-具体岗位: {len(specific_saved)}")
    print(f"    已保存-人才社区: {len(community_saved)}")
    print(f"    匹配搜索结果的: {len(cross_refs)}")
    recruiter_count = sum(1 for n in notifications if n.get("is_recruiter"))
    print(f"    招聘相关通知: {recruiter_count}")
    print(f"{'=' * 60}")

    if specific_applied:
        print("\n具体岗位投递:")
        for a in specific_applied[:15]:
            print(f"    {a['title']} @ {a['company']}")

    if cross_refs:
        print(f"\n搜索结果中已投递/保存 ({len(cross_refs)}):")
        for r in cross_refs[:10]:
            print(f"    [{r['match_type']}] {r['search_title']} @ {r['company']} (评分{r['score']})")

    if recruiter_count:
        print(f"\n招聘相关通知 ({recruiter_count}):")
        for n in notifications:
            if n.get("is_recruiter"):
                print(f"    {n['sender']}: {n['preview'][:80]}")

    print(f"\n打开 HTML: {RESPONSES_HTML}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn application tracker")
    parser.add_argument("--json-only", action="store_true", help="Skip HTML generation")
    args = parser.parse_args()
    main(skip_html=args.json_only)
