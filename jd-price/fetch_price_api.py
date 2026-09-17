#!/usr/bin/env python3
"""
使用京东移动端API获取商品价格
用法: python fetch_price_api.py --sku 100012043978
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    print("[ERROR] 请先安装requests: pip install requests")
    sys.exit(1)


def load_cookies(cookie_file: str) -> dict:
    """加载Cookie文件"""
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # 转换为requests格式
    cookie_dict = {}
    for cookie in cookies:
        cookie_dict[cookie["name"]] = cookie["value"]

    return cookie_dict


def fetch_price_api(sku: str, cookies: dict = None) -> dict:
    """
    使用京东移动端API获取商品价格

    Args:
        sku: 商品SKU
        cookies: Cookie字典

    Returns:
        dict: 商品信息
    """
    url = "https://api.m.jd.com/api"

    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://m.jd.com",
        "referer": "https://m.jd.com/",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    }

    # 获取商品详情的API
    body = json.dumps({
        "skuId": sku,
        "from": "pc",
    })

    data = f"appid=pcDetailPage&functionId=pcDetailPage_getWareInfo&body={quote(body)}"

    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "sku": sku,
                "status": "success",
                "data": result,
                "fetch_time": datetime.now().isoformat()
            }
        else:
            return {
                "sku": sku,
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "fetch_time": datetime.now().isoformat()
            }

    except Exception as e:
        return {
            "sku": sku,
            "status": "error",
            "error": str(e),
            "fetch_time": datetime.now().isoformat()
        }


def extract_price_from_html(sku: str, cookies: dict = None) -> dict:
    """
    从移动端HTML页面提取价格

    Args:
        sku: 商品SKU
        cookies: Cookie字典

    Returns:
        dict: 商品信息
    """
    url = f"https://item.m.jd.com/product/{sku}.html"

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "accept-language": "zh-CN,zh;q=0.9",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            timeout=10
        )

        if response.status_code == 200:
            response.encoding = "utf-8"
            html = response.text

            # 提取价格
            price_match = re.search(r'"p":"([\d.]+)"', html)
            if not price_match:
                price_match = re.search(r'price["\s:]+([\d.]+)', html)

            # 提取商品名称
            name_match = re.search(r'"skuName":"([^"]+)"', html)
            if not name_match:
                name_match = re.search(r'<title>([^<]+)</title>', html)

            # 提取店铺
            shop_match = re.search(r'"shopName":"([^"]+)"', html)

            return {
                "sku": sku,
                "status": "success",
                "name": name_match.group(1) if name_match else "",
                "price": f"¥{price_match.group(1)}" if price_match else "",
                "shop": shop_match.group(1) if shop_match else "",
                "fetch_time": datetime.now().isoformat()
            }
        else:
            return {
                "sku": sku,
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "fetch_time": datetime.now().isoformat()
            }

    except Exception as e:
        return {
            "sku": sku,
            "status": "error",
            "error": str(e),
            "fetch_time": datetime.now().isoformat()
        }


def save_result(result: dict, output_dir: str = None):
    """保存查询结果"""
    if output_dir is None:
        output_dir = str(Path(__file__).parent / "monitors")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_file = Path(output_dir) / f"{result['sku']}.json"

    # 如果文件存在，加载历史数据
    history = []
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            history = data.get("history", [])

    # 添加新记录
    history.append({
        "price": result.get("price", ""),
        "time": result.get("fetch_time", "")
    })

    # 保存
    save_data = {
        "sku": result["sku"],
        "name": result.get("name", ""),
        "current_price": result.get("price", ""),
        "shop": result.get("shop", ""),
        "history": history,
        "last_update": result.get("fetch_time", "")
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return str(output_file)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="京东商品价格获取工具（API方式）")
    parser.add_argument("--sku", required=True, help="京东商品SKU编号")
    parser.add_argument("--cookie", help="Cookie文件路径")
    parser.add_argument("--output", help="输出目录")

    args = parser.parse_args()

    # 加载Cookie
    cookies = None
    if args.cookie:
        cookies = load_cookies(args.cookie)
        print(f"[INFO] 已加载 {len(cookies)} 个Cookie")

    # 尝试API方式
    print(f"[INFO] 正在获取商品 {args.sku} 的价格...")
    result = extract_price_from_html(args.sku, cookies)

    # 保存结果
    output_file = save_result(result, args.output)

    # 输出结果
    print("\n" + "=" * 50)
    print("[OK] 商品信息获取完成")
    print("=" * 50)
    print(f"SKU: {result['sku']}")
    print(f"名称: {result.get('name', 'N/A')}")
    print(f"价格: {result.get('price', 'N/A')}")
    print(f"店铺: {result.get('shop', 'N/A')}")
    print(f"状态: {result.get('status', 'N/A')}")
    print(f"\n数据已保存: {output_file}")

    if result.get("error"):
        print(f"\n[ERROR] 错误信息: {result['error']}")


if __name__ == "__main__":
    main()
