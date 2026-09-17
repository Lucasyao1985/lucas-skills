#!/usr/bin/env python3
"""Scrape MyShell LinkedIn members by using Playwright to call LinkedIn internal API from page context."""
import json, re, sys, time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.txt"
OUTPUT_FILE = SKILL_DIR / "people_results.json"
COMPANY_ID = "18994057"


def parse_cookies(fp):
    cookies = []
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            name, value = parts[0].strip(), parts[1].strip()
            domain = parts[2].strip() if len(parts) > 2 else ".linkedin.com"
            path = parts[3].strip() if len(parts) > 3 else "/"
            expires_str = parts[4].strip() if len(parts) > 4 else ""
            secure = parts[8].strip() if len(parts) > 8 else ""
            http_only = parts[7].strip() if len(parts) > 7 else ""
            expires = -1
            if expires_str and expires_str != "会话":
                try:
                    dt = datetime.strptime(expires_str.replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S")
                    expires = int(dt.timestamp())
                except ValueError:
                    pass
            cookies.append({
                "name": name, "value": value,
                "domain": domain.lstrip("."), "path": path,
                "httpOnly": "✓" in http_only, "secure": "✓" in secure,
                "sameSite": "None",
                **({"expires": expires} if expires > 0 else {}),
            })
    return cookies


def main():
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    print("=" * 60)
    print("  MyShell LinkedIn 成员列表 (内部API方式)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    cookies = parse_cookies(COOKIE_FILE)
    print(f"加载 {len(cookies)} 个 cookies")

    pw = sync_playwright().start()
    all_people = []

    try:
        browser = pw.chromium.launch(
            channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        context.add_cookies(cookies)
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        # Step 1: Go to company page (this works)
        print(f"\n[1] 打开公司页面...")
        page.goto("https://www.linkedin.com/company/myshell/", wait_until="domcontentloaded", timeout=25000)
        time.sleep(3)
        print(f"    URL: {page.url}")

        # Step 2: Extract CSRF token from page
        csrf_token = page.evaluate("""() => {
            const m = document.documentElement.innerHTML.match(/csrfToken"\\s*:\\s*"([^"]+)"/);
            return m ? m[1] : '';
        }""")
        print(f"    CSRF: {csrf_token[:30] if csrf_token else 'NOT FOUND'}...")

        # Step 3: Use page.evaluate to make API call from within the authenticated page
        print(f"\n[2] 调用内部API获取员工列表...")

        # Try multiple API patterns
        api_calls = [
            # Search people endpoint
            f'''fetch("/search/results/people/?currentCompany=[%22{COMPANY_ID}%22]&origin=COMPANY_PAGE_CANNED_SEARCH", {{headers: {{"accept": "text/html"}}}})''',
            # Voyager search
            f'''fetch("/voyager/api/search/cluster?count=50&origin=COMPANY_PAGE_CANNED_SEARCH&q=guided&start=0&facetCurrentCompany=List({COMPANY_ID})", {{headers: {{"accept": "application/vnd.linkedin.normalized+json+2.1", "x-restli-protocol-version": "2.0.0", "csrf-token": "{csrf_token}"}}}})''',
        ]

        for i, api_call in enumerate(api_calls):
            print(f"\n  API call {i+1}...")
            try:
                result = page.evaluate(f"""async () => {{
                    try {{
                        const resp = await {api_call};
                        const text = await resp.text();
                        return {{status: resp.status, text: text.substring(0, 5000)}};
                    }} catch(e) {{
                        return {{error: e.message}};
                    }}
                }}""")
                if 'error' in result:
                    print(f'    Error: {result["error"]}')
                else:
                    status = result.get('status', 0)
                    text = result.get('text', '')
                    print(f'    Status: {status}, text length: {len(text)}')

                    # Extract profiles from text
                    profile_pattern = re.compile(r'/in/([^/?"\'\s&#]+)')
                    matches = profile_pattern.findall(text)
                    print(f'    Found {len(matches)} /in/ paths')

                    # Also look for firstName/lastName in JSON
                    name_pattern = re.compile(r'"firstName"\s*:\s*"([^"]+)"\s*,\s*"lastName"\s*:\s*"([^"]+)"')
                    name_matches = name_pattern.findall(text)
                    print(f'    Found {len(name_matches)} name pairs')

                    for fn, ln in name_matches:
                        name = f"{fn} {ln}"
                        all_people.append({"name": name, "title": "", "url": ""})

                    for path in matches:
                        if path not in [p["url"].split("/in/")[-1].rstrip("/") for p in all_people if p.get("url")]:
                            url = f"https://www.linkedin.com/in/{path}/"
                            all_people.append({"name": path.replace("-", " ").title(), "title": "", "url": url})

            except Exception as e:
                print(f'    Eval error: {e}')

        # Step 4: If still empty, try navigating to people page via click
        if not all_people:
            print(f"\n[3] 尝试点击成员标签...")
            try:
                # Find the "People" tab link on company page
                people_tab = page.query_selector("a[href*='/people/']")
                if people_tab:
                    people_tab.click()
                    time.sleep(4)
                    print(f"    URL after click: {page.url}")

                    # Try extracting from the loaded page
                    profile_links = page.query_selector_all("a[href*='/in/']")
                    print(f"    Found {len(profile_links)} /in/ links")

                    for link in profile_links:
                        href = (link.get_attribute("href") or "").split("?")[0]
                        if "/in/" not in href or "recent-activity" in href:
                            continue
                        name = link.inner_text().strip()
                        if name and len(name) > 1:
                            all_people.append({"name": name, "title": "", "url": href})
                else:
                    print("    People tab not found")
            except Exception as e:
                print(f"    Click error: {e}")

        # Save page screenshot for debug
        page.screenshot(path=str(SKILL_DIR / "final_page.png"))

        browser.close()
    finally:
        pw.stop()

    # Deduplicate
    seen_names = set()
    final = []
    for p in all_people:
        n = p["name"].lower().strip()
        skip = {"linkedin member", "member", "connections", "followers", "linkedin", ""}
        if n in skip or n in seen_names:
            continue
        seen_names.add(n)
        final.append(p)

    print(f"\n{'=' * 60}")
    print(f"  MyShell 成员: {len(final)} 人")
    print(f"{'=' * 60}\n")
    for i, p in enumerate(final, 1):
        ti = f" — {p['title']}" if p.get('title') else ''
        print(f"  {i:3}. {p['name']}{ti}")
        if p.get('url'):
            print(f"       {p['url']}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
