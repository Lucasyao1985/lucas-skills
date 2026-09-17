#!/usr/bin/env python3
"""
京东登录脚本 — 移动端H5登录，兼容 item.m.jd.com 价格抓取

参考: /mnt/d/.openrouter/xiaomi/新建 文本文档.txt
- 用户通过移动端 m.jd.com 登录
- x-rp-client: h5_1.0.0 (京东移动Web客户端)
- Cookie 包含 pin, thor, sdtoken 等移动端会话令牌

用法:
  python login.py              # 打开Chrome手动登录
  python login.py --check      # 仅检查当前登录状态
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[ERROR] pip install playwright && playwright install chromium")
    sys.exit(1)

SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.json"
PROFILE_DIR = SKILL_DIR / ".chrome-profile"

# 移动端UA — 与参考文件中的 curl 命令一致
MOBILE_UA = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"


def check_login_status():
    """检查当前Cookie是否有效"""
    if not COOKIE_FILE.exists():
        print("❌ 没有 cookies.json，需要先登录")
        return False

    with open(COOKIE_FILE) as f:
        cookies = json.load(f)

    # 检查关键cookie
    key_cookies = ['pt_pin', 'pt_key', 'pt_token', 'pin', 'thor']
    found = [c['name'] for c in cookies if c['name'] in key_cookies]
    print(f"📦 cookies.json: {len(cookies)} 个Cookie")
    print(f"   关键Cookie: {found}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            channel="chrome",
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=MOBILE_UA,
            locale="zh-CN",
        )
        for c in cookies:
            c.setdefault("sameSite", "Lax")
            c.setdefault("httpOnly", False)
        context.add_cookies(cookies)
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        page = context.new_page()

        # 测试移动端个人中心
        page.goto("https://home.m.jd.com/myJd/newHome.action", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        url = page.url
        title = page.title()

        if "passport" in url.lower() or "login" in url.lower():
            print("❌ Cookie 已失效，需要重新登录")
            browser.close()
            return False
        else:
            # 检查是否能看到用户名
            try:
                nick = page.evaluate("""() => {
                    const el = document.querySelector('.nickname, .user_name, [class*="nick"], [class*="user"]');
                    return el ? el.textContent.trim() : '';
                }""")
                print(f"✅ Cookie 有效 — 已登录用户: {nick or '(移动端)'}")
                print(f"   当前URL: {url[:80]}")
            except:
                print(f"✅ Cookie 有效 — 页面标题: {title[:60]}")

            browser.close()
            return True


def do_login():
    """打开可见浏览器让用户手动登录"""
    print("=" * 55)
    print("  京东移动端H5登录")
    print("  参考: m.jd.com 登录 → Cookie用于 item.m.jd.com")
    print("=" * 55)
    print()
    print("  流程:")
    print("  1. 打开Chrome浏览器 → 京东移动端首页")
    print("  2. 在浏览器中完成登录（扫码或账号密码）")
    print("  3. 登录后脚本自动保存Cookie")
    print("  4. 关闭浏览器即可")
    print()

    input("按 Enter 开始...")

    # 使用持久化Profile保留登录态
    profile_path = str(PROFILE_DIR.resolve())
    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=False,
            channel="chrome",
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1920, "height": 1080},
            user_agent=MOBILE_UA,  # 移动端UA → 匹配参考文件
            locale="zh-CN",
        )

        # 加载已有Cookie（加速登录）
        if COOKIE_FILE.exists():
            try:
                with open(COOKIE_FILE) as f:
                    old_cookies = json.load(f)
                for c in old_cookies:
                    c.setdefault("sameSite", "Lax")
                    c.setdefault("httpOnly", False)
                context.add_cookies(old_cookies)
                print(f"[INFO] 已加载 {len(old_cookies)} 个旧Cookie")
            except:
                pass

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        """)

        page = context.new_page()

        # ===== 步骤1: 打开移动端首页 =====
        print("\n[INFO] 打开京东移动端首页 m.jd.com ...")
        page.goto("https://m.jd.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        url = page.url
        title = page.title()
        print(f"  当前URL: {url[:100]}")
        print(f"  页面标题: {title[:60]}")

        # ===== 步骤2: 检测登录状态（严格检查Cookie，不只是URL） =====
        cookies = context.cookies()
        has_pin = any(c['name'] == 'pin' for c in cookies)
        has_thor = any(c['name'] == 'thor' for c in cookies)
        is_login_page = "passport" in url.lower() or "login" in url.lower()

        if not has_pin or not has_thor or is_login_page:
            # 真正需要登录
            print("\n⚠️  未登录 — 请在浏览器中完成京东登录")
            print("  支持: 扫码登录 / 账号密码 / 短信验证")
            print("  登录成功标志: 页面顶部出现用户昵称")
            print("  等待登录... (最多5分钟)\n")

            try:
                # 等待直到Cookie中出现pin
                start = __import__('time').time()
                while __import__('time').time() - start < 300:
                    __import__('time').sleep(2)
                    cookies = context.cookies()
                    has_pin = any(c['name'] == 'pin' for c in cookies)
                    has_thor = any(c['name'] == 'thor' for c in cookies)
                    if has_pin and has_thor:
                        print("\n✅ 检测到有效登录 (pin + thor Cookie)")
                        break
                    # 每15秒提示一次
                    elapsed = int(__import__('time').time() - start)
                    if elapsed % 30 == 0 and elapsed > 0:
                        print(f"  ...等待中 ({elapsed}s)")
                else:
                    print("\n[WARN] 5分钟超时，如果已登录请忽略")
            except KeyboardInterrupt:
                pass
        else:
            nick = next((c['value'][:20] for c in cookies if c['name'] == 'pin'), '?')
            print(f"\n✅ 已登录 — pin={nick}...")

        # ===== 步骤3: 访问移动端商品页完善Cookie =====
        print("\n[INFO] 访问商品页完善Cookie...")
        page.goto("https://item.m.jd.com/product/100012043978.html", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        # 检查商品页标题
        item_title = page.title()
        if "频控" not in item_title:
            print(f"  商品页: {item_title[:80]}")

        # 也访问一下个人中心获取完整cookie
        page.goto("https://home.m.jd.com/myJd/newHome.action", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # ===== 步骤4: 保存Cookie =====
        cookies = context.cookies()

        # 保存到 cookies.json
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        # 打印关键Cookie
        key_names = ['pt_pin', 'pt_key', 'pt_token', 'pwdt_id', 'sdtoken',
                     '__jda', 'thor', 'light_key']
        print(f"\n{'='*55}")
        print(f"  ✅ 登录完成!")
        print(f"{'='*55}")
        print(f"  保存了 {len(cookies)} 个Cookie")
        print(f"  关键Cookie:")
        for c in cookies:
            if c['name'] in key_names:
                print(f"    {c['name']}: {c['value'][:40]}...")
        print(f"\n  📁 cookies.json")
        print(f"  📁 .chrome-profile/ (持久化Profile)")
        print(f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*55}")
        print()
        print("  测试: python fetch_price_robust.py --sku <SKU>")

        context.close()


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_login_status()
    else:
        do_login()
