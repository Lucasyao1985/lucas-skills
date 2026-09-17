#!/usr/bin/env python3
"""
京东商品价格获取 — 完成版
借鉴 zhipin skill 反爬: 系统Chrome + 非headless + ignoreDefaultArgs + 移动端页面

反爬突破思路 (来源 zhipin skill):
  1. channel='chrome' — 使用系统Chrome而非Playwright Chromium
  2. headless=False — 可见浏览器绕过无头检测
  3. ignore_default_args=['--enable-automation'] — 移除自动化标志
  4. wait_until='domcontentloaded' — 而非 networkidle
  5. 移动端URL (item.m.jd.com) — 比桌面端反爬弱

价格获取策略 (按优先级):
  1. 页面JS对象 window.itemPrice / window._itemOnly
  2. SKU变体文本 (如 "1539(需预约)")
  3. 页面嵌入JSON数据
  4. 蜘蛛字体解码 (PUA字符映射)
  5. 正则提取页面价格线索

用法:
  python fetch_price.py --sku 100012043978          # 默认有头模式
  python fetch_price.py --sku 100012043978 --headless  # 无头模式(可能被检测)
  python fetch_price.py --sku 100012043978 --manual    # 手动完成验证码
"""

import json
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[ERROR] pip install playwright && playwright install chromium")
    sys.exit(1)

SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.json"

# 京东蜘蛛字体映射: PUA字符 → 数字
FONT_MAP = {
    0xEE18: '0', 0xE08B: '1', 0xF053: '2', 0xEB3A: '3',
    0xEC5D: '4', 0xE0A6: '5', 0xF0D6: '6', 0xF8E7: '7',
    0xEC81: '8', 0xF288: '9',
}


def decode_font_price(text: str) -> str:
    """解码蜘蛛字体加密的价格字符串"""
    result = []
    for ch in text:
        cp = ord(ch)
        if cp in FONT_MAP:
            result.append(FONT_MAP[cp])
        else:
            result.append(ch)
    return ''.join(result)


def extract_price_multi_strategy(page) -> dict:
    """多策略提取商品价格"""
    info = {}

    # 策略1: 从JavaScript全局对象提取
    try:
        js_data = page.evaluate("""() => {
            const data = {};

            // window.itemPrice (主要价格数据)
            if (window.itemPrice) {
                data.jdPrice = window.itemPrice.jdPrice;
                data.priceArr = window.itemPrice.priceArr;
                if (window.itemPrice.jdPrice) {
                    data.jdPriceCodes = [];
                    for (let i = 0; i < window.itemPrice.jdPrice.length; i++) {
                        data.jdPriceCodes.push(window.itemPrice.jdPrice.charCodeAt(i));
                    }
                }
            }

            // window._itemOnly (商品详情)
            if (window._itemOnly && window._itemOnly.item) {
                const item = window._itemOnly.item;
                data.skuName = item.skuName || item.name || '';
                data.skuId = item.skuId;
                data.brandId = item.brandId;
                // 搜索价格相关字段
                const priceFields = {};
                for (const k of Object.keys(item)) {
                    if (k.toLowerCase().includes('price')) {
                        priceFields[k] = item[k];
                    }
                }
                data.priceFields = priceFields;
            }

            // window._itemInfo (库存/店铺信息)
            if (window._itemInfo) {
                if (window._itemInfo.stock) {
                    data.stockState = window._itemInfo.stock.StockState;
                    data.sidDely = window._itemInfo.stock.sidDely;
                }
                if (window._itemInfo.shopFloor && window._itemInfo.shopFloor.shopInfo) {
                    data.shopName = window._itemInfo.shopFloor.shopInfo.shopName;
                    data.venderId = window._itemInfo.shopFloor.shopInfo.venderId;
                }
            }

            // window.shareConfig (分享配置)
            if (window.shareConfig) {
                data.shareTitle = window.shareConfig.title;
                data.shareDesc = window.shareConfig.desc;
            }

            return data;
        }""")

        if js_data.get("jdPrice"):
            raw_price = js_data["jdPrice"]
            decoded = decode_font_price(raw_price)
            # 检查是否完全解码(不含?的字符即解码成功)
            if '?' not in decoded:
                info["price"] = decoded
                info["price_source"] = "window.itemPrice (font decoded)"

        if js_data.get("skuName"):
            info["name"] = js_data["skuName"]
        if js_data.get("shopName"):
            info["shop"] = js_data["shopName"]
        if js_data.get("shareTitle"):
            info["display_name"] = js_data["shareTitle"]
    except Exception:
        pass

    # 策略2: 从SKU变体文本提取价格 (最可靠的后备方案)
    if not info.get("price"):
        try:
            var_texts = page.evaluate("""() => {
                const texts = [];
                // SKU选择器中的变体文本
                const skuSpans = document.querySelectorAll('#skuChoose1, [id*="skuChoose"], [class*="sku-choose"] span, .choose-support span');
                skuSpans.forEach(el => {
                    const t = el.textContent.trim();
                    if (t && /\\d/.test(t)) texts.push(t);
                });

                // 已选中的SKU
                const selected = document.querySelector('.selected, [class*="selected"], [class*="active"]');
                if (selected) {
                    const t = selected.textContent.trim();
                    if (t && /\\d/.test(t)) texts.push(t);
                }

                // 从页面文本提取 SKU 配置
                const bodyText = document.body.innerText;
                const skuMatch = bodyText.match(/已选[：:]\\s*([^，,\\n]{5,50})/);
                if (skuMatch) texts.push(skuMatch[1]);

                return texts;
            }""")
            for text in var_texts:
                # 提取价格数字: "1539(需预约)" → 1539
                m = re.search(r'(\d{3,6}\.?\d{0,2})', text)
                if m:
                    info["price"] = m.group(1)
                    info["price_source"] = f"SKU variant ({text[:30]})"
                    break
        except Exception:
            pass

    # 策略3: CSS选择器获取商品名称
    if not info.get("name"):
        try:
            name = page.evaluate("""() => {
                const sels = ['h1', '.sku-name', '.title', '.item-name',
                    '[class*="name"]', '.product-title', '.goods-name'];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const t = el.textContent.trim();
                        if (t.length > 3) return t.replace(/\\s+/g, ' ');
                    }
                }
                return document.title.split('【')[0].trim();
            }""")
            if name:
                info["name"] = name
        except Exception:
            pass

    # 策略4: CSS选择器获取店铺
    if not info.get("shop"):
        try:
            shop = page.evaluate("""() => {
                const sels = ['.shop-name a', '[class*="shop-name"]',
                    '.jdm-shop-name', '.shopName', '.vender-name a'];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el) return el.textContent.trim();
                }
                return '';
            }""")
            if shop:
                info["shop"] = shop
        except Exception:
            pass

    # 策略5: 从页面文本正则提取 (最后的备选)
    if not info.get("price"):
        try:
            body = page.evaluate("() => document.body.innerText")
            patterns = [
                r'[¥￥]\s*(\d{2,6}\.?\d{0,2})',
                r'京东价[：:]\s*[¥￥]?\s*(\d{2,6}\.?\d{0,2})',
                r'到手价[：:]\s*[¥￥]?\s*(\d{2,6}\.?\d{0,2})',
                r'PLUS价[：:]\s*[¥￥]?\s*(\d{2,6}\.?\d{0,2})',
            ]
            for p in patterns:
                m = re.search(p, body)
                if m:
                    info["price"] = m.group(1).replace(",", "")
                    info["price_source"] = f"body regex ({p[:40]})"
                    break
        except Exception:
            pass

    return info


def fetch_jd_price(sku: str, headless: bool = False, manual_mode: bool = False,
                   debug: bool = True) -> dict:
    """使用Playwright获取京东商品价格"""

    url = f"https://item.m.jd.com/product/{sku}.html"  # 移动端URL
    cookies = load_cookies()

    with sync_playwright() as p:
        # 核心1: 系统Chrome + 移除自动化标志
        try:
            browser = p.chromium.launch(
                headless=headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-infobars", "--no-sandbox",
                    "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                ],
                ignore_default_args=["--enable-automation"],
            )
        except Exception as e:
            print(f"[WARN] Chrome不可用，回退Chromium: {e}", file=sys.stderr)
            browser = p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                ignore_default_args=["--enable-automation"],
            )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 核心2: 隐身脚本
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        # 加载Cookie
        if cookies:
            for c in cookies:
                c.setdefault("sameSite", "Lax")
                c.setdefault("httpOnly", False)
            context.add_cookies(cookies)
            print(f"[INFO] 已加载 {len(cookies)} 个Cookie")

        page = context.new_page()

        try:
            print(f"[INFO] 正在访问: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)

            # 处理验证码/频控
            title = page.title()
            current_url = page.url

            if "频控" in title or "验证" in title:
                if manual_mode:
                    print("[INFO] 检测到验证页，请在浏览器完成验证...")
                    try:
                        page.wait_for_url("**/item.m.jd.com/**", timeout=120000)
                        page.wait_for_timeout(3000)
                    except Exception:
                        return {
                            "sku": sku, "url": url, "status": "blocked_by_jd",
                            "error": "验证超时", "fetch_time": datetime.now().isoformat()
                        }
                else:
                    return {
                        "sku": sku, "url": url, "status": "blocked_by_jd",
                        "error": "频控拦截，请使用 --manual 模式手动验证",
                        "fetch_time": datetime.now().isoformat()
                    }

            # 保存调试信息
            if debug:
                debug_dir = SKILL_DIR / "debug"
                debug_dir.mkdir(exist_ok=True)
                page.screenshot(path=str(debug_dir / f"{sku}.png"), full_page=False)

            # 提取价格
            product_info = extract_price_multi_strategy(page)

            # 刷新Cookie
            try:
                save_cookies(context.cookies())
            except Exception:
                pass

            # 检查登录状态
            if "?" in str(product_info.get("price", "")):
                login_needed = "登录查看" in page.evaluate("() => document.body.innerText.substring(0, 500)")
            else:
                login_needed = False

            result = {
                "sku": sku,
                "url": url,
                "name": product_info.get("name") or product_info.get("display_name", ""),
                "price": product_info.get("price", ""),
                "shop": product_info.get("shop", ""),
                "price_source": product_info.get("price_source", "none"),
                "fetch_time": datetime.now().isoformat(),
                "status": "success" if product_info.get("price") else "price_not_found",
                "login_needed": login_needed,
            }

            return result

        except Exception as e:
            return {
                "sku": sku, "url": url,
                "error": str(e),
                "fetch_time": datetime.now().isoformat(),
                "status": "error"
            }
        finally:
            browser.close()


def load_cookies() -> list:
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_cookies(cookies: list):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)


def save_result(result: dict) -> str:
    monitor_dir = SKILL_DIR / "monitors"
    monitor_dir.mkdir(exist_ok=True)
    monitor_file = monitor_dir / f"{result['sku']}.json"

    history = []
    if monitor_file.exists():
        with open(monitor_file, "r", encoding="utf-8") as f:
            history = json.load(f).get("history", [])

    history.append({
        "price": result.get("price", ""),
        "name": result.get("name", ""),
        "time": result.get("fetch_time", "")
    })
    if len(history) > 30:
        history = history[-30:]

    save_data = {
        "sku": result["sku"],
        "url": result["url"],
        "name": result.get("name", ""),
        "current_price": result.get("price", ""),
        "shop": result.get("shop", ""),
        "price_source": result.get("price_source", ""),
        "history": history,
        "last_update": result.get("fetch_time", "")
    }

    with open(monitor_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return str(monitor_file)


def format_price(price_str) -> str:
    if not price_str:
        return ""
    clean = re.sub(r'[^\d.]', '', str(price_str))
    if clean:
        try:
            return f"¥{float(clean):.2f}"
        except ValueError:
            return f"¥{clean}"
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="京东商品价格获取（反反爬增强版）",
        epilog="示例: python fetch_price.py --sku 100012043978"
    )
    parser.add_argument("--sku", required=True, help="京东商品SKU编号")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--manual", action="store_true", help="手动验证模式")
    parser.add_argument("--no-debug", action="store_true", help="不保存截图")
    args = parser.parse_args()

    result = fetch_jd_price(
        args.sku,
        headless=args.headless,
        manual_mode=args.manual,
        debug=not args.no_debug
    )

    output_file = save_result(result)
    price_fmt = format_price(result.get("price", ""))

    print("\n" + "=" * 55)
    print("  \U0001f4e6 京东商品信息")
    print("=" * 55)
    print(f"  SKU:    {result['sku']}")
    print(f"  名称:   {result.get('name') or 'N/A'}")
    print(f"  价格:   {price_fmt or 'N/A'}")
    print(f"  店铺:   {result.get('shop') or 'N/A'}")
    print(f"  来源:   {result.get('price_source', 'N/A')}")
    print(f"  状态:   {result.get('status', 'N/A')}")
    if result.get("login_needed"):
        print(f"  ⚠️  需要登录京东账号查看完整价格")
    if result.get("error"):
        print(f"  ⚠️  {result['error']}")
    print(f"\n  \U0001f4be 数据已保存: {output_file}")


if __name__ == "__main__":
    main()
