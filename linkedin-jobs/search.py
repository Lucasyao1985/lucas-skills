#!/usr/bin/env python3
"""
LinkedIn Job Search — Domestic + Global for 徐伟
Targets AI Builder / AI Native roles: "用 AI 构建产品的人，不是传统程序员"
Searches both 上海 and Remote/Worldwide positions.
Uses Google Chrome with stealth + comprehensive selectors.
"""

import json
import re
import sys
import time
import os
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Also log to file for WSL-side monitoring
_LOG_FILE = Path("C:/Users/Lucas/Desktop/GPT-image2/linkedin-search.log")

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

_log_fh = open(_LOG_FILE, "w", encoding="utf-8")
sys.stdout = Tee(sys.stdout, _log_fh)
sys.stderr = Tee(sys.stderr, _log_fh)

# ── Config ──────────────────────────────────────────────
SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.txt"
OUTPUT_FILE = SKILL_DIR / "matched_jobs.json"

# Time filter: only search jobs from last N seconds
# r86400=24h, r604800=7d, r2592000=30d
TIME_FILTER = "r604800"  # last 7 days

# ── 两线搜索：国内(上海) + 海外(Remote/Worldwide) ──
# 每项: (query, location_name, geo_id)
# geo_id: 上海=102890883, Worldwide=92000000
SEARCH_QUERIES = [
    # ═══ 上海本地 ═══
    ("AI Agent 开发 上海", "上海", "102890883"),
    ("大模型 AI 开发 上海", "上海", "102890883"),
    ("AI 应用开发工程师 上海", "上海", "102890883"),
    ("自动化开发 上海", "上海", "102890883"),
    ("前端开发 React 上海", "上海", "102890883"),

    # ═══ Remote / Worldwide — AI Builder 类型 ═══
    ("AI Agent Engineer Remote", "Worldwide", "92000000"),
    ("AI Builder Product Engineer", "Worldwide", "92000000"),
    ("AI Native Full Stack Engineer", "Worldwide", "92000000"),
    ("AI Automation Engineer Remote", "Worldwide", "92000000"),
    ("Vibe Coding AI Developer", "Worldwide", "92000000"),
    ("Generative AI Engineer Remote", "Worldwide", "92000000"),
    ("AI Workflow Automation Remote", "Worldwide", "92000000"),
    ("Prompt Engineer AI Agent Remote", "Worldwide", "92000000"),
    ("No Code AI Developer Remote", "Worldwide", "92000000"),
    ("AI Product Engineer Builder", "Worldwide", "92000000"),
    ("Claude AI Developer Remote", "Worldwide", "92000000"),
    ("Cursor AI Engineer Remote", "Worldwide", "92000000"),
    ("AIGC Developer ComfyUI Remote", "Worldwide", "92000000"),
    ("AI Applications Engineer Remote", "Worldwide", "92000000"),

    # ═══ AI Coding Agent — 用 AI 写代码的新范式 ═══
    ("AI Coding Agent Remote", "Worldwide", "92000000"),
    ("AI-Assisted Developer Remote", "Worldwide", "92000000"),
    ("Agentic Development Engineer", "Worldwide", "92000000"),
    ("AI-Powered Software Engineer Remote", "Worldwide", "92000000"),
    ("Claude Code Developer", "Worldwide", "92000000"),

    # ═══ 硅谷 / 旧金山湾区 ═══
    ("AI Agent Engineer", "San Francisco Bay Area", "90000084"),
    ("AI Builder Product Engineer", "San Francisco Bay Area", "90000084"),
    ("AI Native Full Stack Developer", "San Francisco Bay Area", "90000084"),
    ("AI Automation Engineer", "San Francisco Bay Area", "90000084"),
    ("Generative AI Engineer", "San Francisco Bay Area", "90000084"),
    ("AI Workflow Automation", "San Francisco Bay Area", "90000084"),
    ("Prompt Engineer AI Agent", "San Francisco Bay Area", "90000084"),
    ("Claude AI Developer", "San Francisco Bay Area", "90000084"),
    ("Cursor AI Engineer", "San Francisco Bay Area", "90000084"),
    ("Vibe Coding Developer", "San Francisco Bay Area", "90000084"),

    # ═══ 硅谷 — AI Coding Agent 新范式 ═══
    ("AI Coding Agent", "San Francisco Bay Area", "90000084"),
    ("AI-Assisted Developer", "San Francisco Bay Area", "90000084"),
    ("Agentic Development Engineer", "San Francisco Bay Area", "90000084"),
    ("AI-Powered Software Engineer", "San Francisco Bay Area", "90000084"),
    ("Claude Code Developer", "San Francisco Bay Area", "90000084"),
]

# ── 排除传统企业/不匹配岗位 ──
# 公司名包含这些关键词 → 直接跳过
EXCLUDE_COMPANIES = [
    "PwC", "pwc", "普华永道",
    "Deloitte", "德勤",
    "EY", "安永",
    "KPMG", "毕马威",
    "Accenture", "埃森哲",
    "Capgemini", "凯捷",
    "Cognizant", "高知特",
    "Infosys", "印孚瑟斯",
    "TCS", "Tata Consultancy",
    "Wipro",
    "IBM",
    "Oracle",
    "SAP",
    "富士通", "Fujitsu",
    "NEC", "日立", "Hitachi",
    "NTT", "NTT DATA",
]

# 标题包含这些 → 直接跳过
EXCLUDE_TITLES = [
    "senior manager", "senior director", "VP ", "Vice President",
    "项目经理", "project manager", "program manager",
    "salesforce", "Salesforce",
    "SAP ", "sap consultant",
    "日语", "Japanese", "JLPT", "N1", "N2",
    "java开发", "java engineer", "java software",
    "devops", "DevOps",
    "QA ", "QA engineer", "测试工程师", "test engineer",
    "support engineer", "技术支持",
    "cybersecurity", "security engineer", "安全工程师",
    "network engineer", "网络工程师",
    "system admin", "系统管理员",
    "database administrator", "DBA",
    "erp ", "ERP",
    "banking", "insurance", "financial services",
    "scrum master", "agile coach",
]

# 标题包含这些 → 扣分（偏传统/硬性门槛高）
PENALTY_TITLES = [
    "senior", "sr.", "staff engineer", "staff software",
    "lead engineer", "tech lead",
    "5+ years", "5年以上", "8+ years", "10+ years",
    "bachelor", "master", "phd", "本科", "硕士", "博士",
    "team lead", "engineering manager",
]

# 标题包含这些 → 大幅加分（AI Builder 类型信号）
AI_BUILDER_BONUS = [
    "ai native", "ai builder", "ai-first", "ai first",
    "product engineer", "builder engineer",
    "vibe coding", "vibe coder",
    "prompt engineer", "prompt engineering",
    "ai agent", "agent developer", "agent engineer",
    "generative ai", "gen ai",
    "no degree", "no cs degree",
    "remote-first", "distributed team",
    "startup", "early stage", "seed stage",
    "y combinator", "yc ", "techstars",
    "founding engineer", "founding team",
    "0 to 1", "zero to one",
    "side project", "hacker", "builder",
    "prototype", "rapid prototyping",
    "ai automation", "ai workflow",
    "claude", "cursor", "copilot",
    # AI Coding Agent 新范式 — 用 AI 写代码，不是传统手写
    "ai coding agent", "ai coding", "ai-assisted",
    "agentic", "agentic development", "agentic engineer",
    "ai-powered", "ai powered", "ai first development",
    "claude code", "ai pair programming",
    "ai-driven development", "ai augmented",
    "windsurf", "devin", "lovable", "bolt", "replit",
    "ai software engineer", "ai native engineer",
    "no traditional", "portfolio over", "builder mindset",
    "ship fast", "ship daily", "build in public",
]

# Core skills for scoring
CORE_SKILLS = [
    "ai agent", "agent开发", "ai开发", "ai应用", "ai application",
    "n8n", "automation", "自动化", "comfyui", "aigc",
    "frontend", "前端", "react", "vue", "typescript", "javascript",
    "python", "claude", "cursor", "llm", "大模型",
    "vibe coding", "full stack", "全栈", "workflow", "openclaw",
    "node.js", "nodejs", "next.js", "nextjs",
    "ai builder", "ai native", "product engineer", "builder",
    "remote", "remote-first", "async", "distributed",
    # AI Coding Agent 新范式
    "ai coding", "ai-assisted", "agentic", "ai-powered",
    "claude code", "ai pair programming", "ai augmented",
    "windsurf", "devin", "lovable", "bolt", "replit",
    "ai driven", "ai software engineer",
]

TITLE_BONUS = [
    "ai agent", "agent开发", "前端", "自动化", "aigc", "ai应用",
    "ai开发", "大模型", "全栈", "full stack",
    "ai native", "ai builder", "product engineer", "vibe coding",
    "generative ai", "remote",
]


def parse_cookies(filepath: str) -> list[dict]:
    """Parse exported cookie file into Playwright format."""
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
            domain = parts[2].strip() if len(parts) > 2 else ".linkedin.com"
            path = parts[3].strip() if len(parts) > 3 else "/"
            expires_str = parts[4].strip() if len(parts) > 4 else ""
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


def extract_jobs_from_page(page) -> list[dict]:
    """Extract job cards using multiple selector strategies."""
    jobs = []

    # Strategy 1: Broadest container selectors
    card_selectors = [
        ".jobs-search-results__list-item",
        ".job-card-container",
        ".base-search-card",
        ".scaffold-layout__list-item",
        "li.jobs-search-results__list-item",
        "li[data-entity-urn]",
        "[data-job-id]",
        ".job-search-card",
        "article.job-card",
    ]

    cards = []
    for sel in card_selectors:
        cards = page.query_selector_all(sel)
        if cards:
            break

    if not cards:
        # Fallback: find all links that look like job links
        cards = page.query_selector_all("a[href*='/jobs/view/']")
        if cards:
            # These are links, not cards — handle differently
            seen = set()
            for link in cards:
                href = link.get_attribute("href") or ""
                job_id_match = re.search(r'/jobs/view/(\d+)', href)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    if job_id not in seen:
                        seen.add(job_id)
                        # Try to get parent card context
                        parent = link
                        for _ in range(5):
                            parent = parent.query_selector("xpath=..")
                            if not parent:
                                break
                        jobs.append({
                            "title": link.inner_text().strip(),
                            "company": "",
                            "location": "",
                            "url": "https://www.linkedin.com" + href.split("?")[0],
                        })
            return jobs

    # Extract from cards
    for card in cards[:40]:
        try:
            # Title
            title_el = (
                card.query_selector(".job-card-list__title") or
                card.query_selector(".base-search-card__title") or
                card.query_selector(".job-card-container__link") or
                card.query_selector("h3") or
                card.query_selector("a") or
                card.query_selector("strong")
            )
            title = title_el.inner_text().strip() if title_el else ""

            # Company
            company_el = (
                card.query_selector(".job-card-container__company-name") or
                card.query_selector(".base-search-card__subtitle") or
                card.query_selector(".artdeco-entity-lockup__subtitle") or
                card.query_selector("h4")
            )
            company = company_el.inner_text().strip() if company_el else ""

            # Location
            loc_el = (
                card.query_selector(".job-card-container__metadata-item") or
                card.query_selector(".job-search-card__location") or
                card.query_selector(".artdeco-entity-lockup__caption")
            )
            location = loc_el.inner_text().strip() if loc_el else ""

            # Link
            link_el = card.query_selector("a")
            link = ""
            if link_el:
                link = link_el.get_attribute("href") or ""
                if link and not link.startswith("http"):
                    link = "https://www.linkedin.com" + link
                link = link.split("?")[0]

            # Also try data attribute
            if not link:
                entity_urn = card.get_attribute("data-entity-urn") or ""
                job_id_match = re.search(r':(\d+)$', entity_urn)
                if job_id_match:
                    link = f"https://www.linkedin.com/jobs/view/{job_id_match.group(1)}/"

            if title:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": link,
                })
        except Exception:
            continue

    return jobs


def score_job(job: dict) -> tuple[int, list[str]]:
    """Score a job against core skills. Returns negative score if job should be excluded."""
    company = job.get("company", "").lower()
    title = job.get("title", "").lower()
    text = f"{title} {company}"

    # ── 硬排除 ──
    for kw in EXCLUDE_COMPANIES:
        if kw.lower() in company:
            return -999, [f"🚫 排除公司: {kw}"]

    for kw in EXCLUDE_TITLES:
        if kw.lower() in title:
            return -999, [f"🚫 排除岗位: {kw}"]

    # ── 评分 ──
    score = 0
    matched = []

    # AI Builder 信号加分
    for kw in AI_BUILDER_BONUS:
        if kw.lower() in title:
            score += 25
            matched.append(f"🔑 {kw}")

    # 核心技能加分
    for skill in CORE_SKILLS:
        if skill.lower() in text:
            score += 10
            matched.append(skill)

    # 标题直接命中高价值词
    for kw in TITLE_BONUS:
        if kw.lower() in title:
            score += 20
            matched.append(f"★{kw}")

    # 传统/硬门槛关键词扣分
    for kw in PENALTY_TITLES:
        if kw.lower() in title:
            score -= 15
            matched.append(f"⚠️ {kw}")

    return score, matched


def run_search():
    """Main search logic using Playwright + Chrome."""
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    print("[1] 启动 Google Chrome...")
    cookies = parse_cookies(COOKIE_FILE)
    print(f"    加载 {len(cookies)} 个 cookies")

    # Start fresh each run — no historical accumulation
    # Old jobs expire within 1-2 days; accumulating stale data makes the output unusable
    all_jobs = {}

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
        context.add_cookies(cookies)

        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        for qi, (query, loc_name, geo_id) in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[{qi}/{len(SEARCH_QUERIES)}] 搜索: '{query}' ({loc_name})")

            encoded = query.replace(" ", "%20")
            loc_encoded = loc_name.replace(" ", "%20")
            is_global = geo_id == "92000000"
            remote_param = "&f_WT=2" if is_global else ""
            url = (
                f"https://www.linkedin.com/jobs/search/?"
                f"keywords={encoded}"
                f"&location={loc_encoded}"
                f"&geoId={geo_id}"
                f"&f_AL=true"
                f"&f_TPR={TIME_FILTER}"
                f"{remote_param}"
                f"&sortBy=R"
            )

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(3)

                # Check login
                if "login" in page.url.lower() or "sign-in" in page.url.lower():
                    print("    ❌ Cookie 过期，需要重新登录")
                    break

                # Scroll to load
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)

                # Extract
                new_jobs = extract_jobs_from_page(page)
                print(f"    抓取到 {len(new_jobs)} 个职位")

                for job in new_jobs:
                    key = re.sub(r"[^a-zA-Z0-9一-鿿]", "", job.get("title", "") + job.get("company", ""))[:50]
                    if key and key not in all_jobs:
                        job["source_query"] = query
                        all_jobs[key] = job

                print(f"    总计去重: {len(all_jobs)}")

            except Exception as e:
                msg = str(e)
                print(f"    出错: {msg[:100]}")
                if "closed" in msg.lower() or "target" in msg.lower():
                    print("    浏览器已关闭，终止搜索")
                    break
                continue

            time.sleep(1.5)

        browser.close()

    finally:
        pw.stop()

    # Score all jobs, filter out excluded
    job_list = []
    excluded_count = 0
    for job in all_jobs.values():
        job["score"], job["matched_skills"] = score_job(job)
        if job["score"] < 0:
            excluded_count += 1
        else:
            job_list.append(job)

    if excluded_count:
        print(f"\n  🚫 自动排除 {excluded_count} 个不匹配岗位（传统企业/硬性门槛）")

    job_list.sort(key=lambda j: j["score"], reverse=True)

    return job_list


def main():
    print("=" * 60)
    print("  领英职位搜索 — 国内 + 海外双线")
    print("  匹配: AI Builder / AI Agent / 自动化 / 前端")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    cn = sum(1 for _,l,_ in SEARCH_QUERIES if l=="上海")
    gl = sum(1 for _,l,_ in SEARCH_QUERIES if l=="Worldwide")
    sv = sum(1 for _,l,_ in SEARCH_QUERIES if "San Francisco" in l)
    print(f"  搜索词: {len(SEARCH_QUERIES)} 个 (上海{cn} + 全球{gl} + 硅谷{sv})")
    print("=" * 60)

    jobs = run_search()

    if not jobs:
        print("\n❌ 未找到结果")
        return

    # AI Builder 信号强的岗位（标题命中 AI Builder/Bonus 关键词 ≥3 个）
    builder_jobs = [j for j in jobs if sum(1 for m in j.get("matched_skills", []) if m.startswith("🔑")) >= 3]
    high = [j for j in jobs if j["score"] >= 20 and j not in builder_jobs]
    mid = [j for j in jobs if 10 <= j["score"] < 20]
    low = [j for j in jobs if j["score"] < 10]

    def show(j, idx):
        s = j["score"]
        loc = j.get('location', '?')
        is_cn = any(w in loc for w in ["上海", "北京", "深圳", "广州", "杭州", "中国", "朝阳", "浦东", "徐汇"])
        is_sv = any(w in loc for w in ["San Francisco", "Bay Area", "Mountain View", "Palo Alto", "San Jose", "Sunnyvale", "Santa Clara", "Cupertino"])
        if is_cn: tag = "🇨🇳"
        elif is_sv: tag = "🌉"
        else: tag = "🌍"
        # Show AI Builder signals
        builder_signals = [m.replace("🔑 ", "") for m in j.get("matched_skills", []) if m.startswith("🔑")]
        print(f"\n  [{idx}] ⭐{s} {tag} | {j['title']}")
        print(f"       🏢 {j.get('company', '?')} | 📍 {loc}")
        if j.get("url"):
            print(f"       🔗 {j['url']}")
        if builder_signals:
            print(f"       🔑 AI Builder 信号: {', '.join(builder_signals[:6])}")
        if j.get("matched_skills"):
            other = [m for m in j["matched_skills"] if not m.startswith("🔑") and not m.startswith("🚫") and not m.startswith("⚠️")]
            if other:
                print(f"       🏷️ {', '.join(other[:6])}")

    if builder_jobs:
        print(f"\n── 🔑 AI Builder 类型 ({len(builder_jobs)}) ──")
        print("   「用 AI 构建产品的人，不是传统程序员」")
        for i, j in enumerate(builder_jobs[:20], 1):
            show(j, i)

    if high:
        print(f"\n── 🔥 高匹配 ({len(high)}) ──")
        for i, j in enumerate(high[:40], 1):
            show(j, i)

    if mid:
        print(f"\n── 👍 中等匹配 ({len(mid)}) ──")
        for i, j in enumerate(mid[:20], 1):
            show(j, i)

    if low:
        print(f"\n── 👀 其他 ({len(low)}) ──")
        for i, j in enumerate(low[:15], 1):
            show(j, i)

    print(f"\n{'=' * 60}")
    print(f"  总计: {len(jobs)} | 🔑AI Builder: {len(builder_jobs)} | 🔥高: {len(high)} | 👍中: {len(mid)} | 👀低: {len(low)}")
    print(f"{'=' * 60}")

    # Remove internal scoring data for clean output
    clean = []
    for j in jobs:
        clean.append({
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "score": j.get("score", 0),
            "matched_skills": j.get("matched_skills", []),
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {OUTPUT_FILE}")

    # Show top 10 summary for easy review
    print(f"\n🏆 TOP 10 推荐投递:")
    for i, j in enumerate(jobs[:10], 1):
        stars = "⭐" * min(5, 1 + j["score"] // 10)
        print(f"  {i:2}. {stars} {j.get('title','')} @ {j.get('company','')}")
        print(f"      {j.get('url','')}")


if __name__ == "__main__":
    main()
