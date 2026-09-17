#!/usr/bin/env python3
"""
将浏览器导出的Cookie转换为Playwright格式
用法: python convert_cookies.py --input cookies.txt --output cookies.json
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def parse_cookie_file(file_path: str) -> list:
    """
    解析浏览器导出的Cookie文件

    支持格式：
    1. Netscape/Mozilla格式（tab分隔）
    2. curl命令中的Cookie字符串

    Returns:
        list: Cookie列表
    """
    cookies = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否是JSON格式（已有cookies.json）
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) > 0 and "name" in parsed[0]:
            print(f"[INFO] 检测到JSON格式，共 {len(parsed)} 个Cookie")
            return parsed
    except (json.JSONDecodeError, KeyError):
        pass

    # 检查是否包含curl命令
    curl_match = re.search(r"-b\s+'([^']+)'", content)
    if curl_match:
        cookie_string = curl_match.group(1)
        # 解析cookie字符串
        for pair in cookie_string.split("; "):
            pair = pair.strip()
            if "=" in pair:
                name, value = pair.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".jd.com",
                    "path": "/",
                })
        return cookies

    # 解析Netscape格式
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) >= 7:
            domain = parts[0]
            path = parts[2]
            secure = parts[3].lower() == "true"
            expires = parts[4]
            name = parts[5]
            value = parts[6]

            # 转换过期时间
            expires_ts = None
            if expires and expires != "会话":
                try:
                    # 尝试解析ISO格式
                    dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    expires_ts = int(dt.timestamp())
                except:
                    try:
                        expires_ts = int(expires)
                    except:
                        pass

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": secure,
            }

            if expires_ts:
                cookie["expires"] = expires_ts

            cookies.append(cookie)

    return cookies


def convert_to_playwright(cookies: list) -> list:
    """
    转换为Playwright格式
    """
    playwright_cookies = []

    for cookie in cookies:
        pw_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie.get("domain", ".jd.com"),
            "path": cookie.get("path", "/"),
        }

        if cookie.get("secure"):
            pw_cookie["secure"] = True

        if cookie.get("expires"):
            pw_cookie["expires"] = cookie["expires"]

        playwright_cookies.append(pw_cookie)

    return playwright_cookies


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cookie格式转换工具")
    parser.add_argument("--input", "-i", required=True, help="输入Cookie文件")
    parser.add_argument("--output", "-o", help="输出JSON文件")

    args = parser.parse_args()

    if args.output is None:
        args.output = str(Path(args.input).with_suffix(".json"))

    # 解析Cookie
    print(f"[INFO] 正在解析: {args.input}")
    cookies = parse_cookie_file(args.input)
    print(f"[INFO] 解析到 {len(cookies)} 个Cookie")

    # 转换格式
    pw_cookies = convert_to_playwright(cookies)

    # 保存
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(pw_cookies, f, ensure_ascii=False, indent=2)

    print(f"[OK] 已保存: {args.output}")

    # 显示关键Cookie
    key_cookies = ["pin", "unick", "thor", "light_key", "flash"]
    print("\n[INFO] 关键Cookie:")
    for cookie in pw_cookies:
        if cookie["name"] in key_cookies:
            print(f"  {cookie['name']}: {cookie['value'][:30]}...")


if __name__ == "__main__":
    main()
