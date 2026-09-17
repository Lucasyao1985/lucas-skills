#!/usr/bin/env python3
"""
从浏览器导出京东Cookie
用法: python export_cookies.py
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[ERROR] 请先安装playwright: pip install playwright")
    sys.exit(1)


def export_cookies(output_file: str = None):
    """
    打开浏览器让用户登录京东，然后导出Cookie

    Args:
        output_file: 输出文件路径
    """
    if output_file is None:
        output_file = str(Path(__file__).parent / "cookies.json")

    print("=" * 50)
    print("京东Cookie导出工具")
    print("=" * 50)
    print()
    print("[INFO] 即将打开浏览器，请按以下步骤操作：")
    print("1. 在浏览器中登录京东账号")
    print("2. 登录成功后，回到此窗口按回车键")
    print("3. Cookie将自动导出")
    print()

    input("按回车键开始...")

    with sync_playwright() as p:
        # 启动浏览器（非无头模式）
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )

        # 注入脚本隐藏webdriver标识
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        page = context.new_page()

        # 访问京东登录页面
        print("[INFO] 正在打开京东登录页面...")
        page.goto("https://passport.jd.com/new/login.aspx", wait_until="networkidle")

        print()
        print("[INFO] 请在浏览器中登录京东账号")
        print("[INFO] 登录成功后，回到此窗口按回车键")
        print()

        input("登录完成后，按回车键导出Cookie...")

        # 获取Cookie
        cookies = context.cookies()

        # 保存Cookie
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Cookie已导出: {output_file}")
        print(f"[INFO] 共 {len(cookies)} 个Cookie")

        browser.close()

    return output_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="京东Cookie导出工具")
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()

    export_cookies(args.output)


if __name__ == "__main__":
    main()
