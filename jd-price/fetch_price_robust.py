#!/usr/bin/env python3
"""
京东价格获取 — 三重保障完整版
================================
优先级1: 复用持久化Chrome Profile (已登录态)
优先级2: 真实浏览器模式 (可见窗口，手动验证)
优先级3: 直接读取页面最终渲染价格 (DOM/XHR/渲染结果)

自动验证: ??? / 1??9 / null → 自动切换下级策略
三重验证: DOM解析 → XHR抓取 → 页面渲染结果

用法:
  python fetch_price_robust.py --sku 100012043978
  python fetch_price_robust.py --sku 100012043978 --headless  # 强制无头
"""

import json, sys, re, argparse
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
PROFILE_DIR = SKILL_DIR / ".chrome-profile"  # 持久化Chrome Profile
PROFILE_DIR.mkdir(exist_ok=True)

FONT_MAP = {
    0xEE18: '0', 0xE08B: '1', 0xF053: '2', 0xEB3A: '3',
    0xEC5D: '4', 0xE0A6: '5', 0xF0D6: '6', 0xF8E7: '7',
    0xEC81: '8', 0xF288: '9',
}

def search_product(keyword: str, page) -> list:
    """搜索京东商品，返回SKU列表（从DOM属性提取）"""
    from urllib.parse import quote
    page.goto(f"https://so.m.jd.com/ware/search.action?keyword={quote(keyword)}",
              wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(5000)
    for _ in range(4):
        page.evaluate('window.scrollBy(0, 500)')
        page.wait_for_timeout(800)
    # 从 search_prolist_item 的 skuid 属性提取
    skus = page.evaluate('''() => {
        const items = document.querySelectorAll('[skuid]');
        return Array.from(items).map(el => ({
            sku: el.getAttribute('skuid'),
            text: el.textContent?.trim()?.substring(0, 80) || ''
        })).filter(x => x.sku && x.sku.length > 8);
    }''')
    return skus


# 无效价格模式 — 触发自动降级
INVALID_PRICE_PATTERNS = [
    r'^\?+$',           # 纯问号
    r'^\d\?+\d?$',      # 1??9
    r'^null$',          # null
    r'^$',              # 空
    r'^\?[\d\?]*$',     # 混合问号
]

def is_valid_price(price_str: str, raw_text: str = "") -> bool:
    """检查价格是否有效 — 自动拒绝字体加密的伪价格"""
    if not price_str:
        return False
    price_str = str(price_str).strip()

    # 拒绝已知无效模式
    for pattern in INVALID_PRICE_PATTERNS:
        if re.match(pattern, price_str):
            return False

    # 必须包含数字
    if not re.search(r'\d', price_str):
        return False

    # 关键: 如果原始文本含'?'表示字体加密未解码，拒绝
    if raw_text and '?' in raw_text:
        return False

    # 价格应该在合理范围 (京东商品 0.01 ~ 999999)
    try:
        val = float(price_str.replace(',', ''))
        if val < 0.01 or val > 999999:
            return False
    except ValueError:
        return False

    return True


def decode_font(text: str) -> str:
    """解码蜘蛛字体"""
    return ''.join(FONT_MAP.get(ord(c), c) for c in text)


# ═══════════════════════════════════════════════
#  价格提取层 — 多层兜底
# ═══════════════════════════════════════════════

def extract_price_layer1(page) -> dict:
    """层1: window.itemPrice.jdPrice — 登录后返回明文价格!!! (最重要)"""
    try:
        data = page.evaluate("""() => {
            const r = {};
            if (window.itemPrice) {
                r.jdPrice = window.itemPrice.jdPrice;  // 登录后是明文如 "1539.00"
                // 传回原始字符码点，防止JSON序列化丢失
                if (r.jdPrice) {
                    r.codes = [];
                    for (let i = 0; i < r.jdPrice.length; i++)
                        r.codes.push(r.jdPrice.charCodeAt(i));
                }
            }
            return r;
        }""")
        if data.get("codes"):
            raw = ''.join(chr(c) for c in data['codes'])
            # 如果全是ASCII数字，说明已登录，直接返回明文
            if all(48 <= c <= 57 or c == 46 for c in data['codes']):
                return {"price": raw, "source": "layer1:jdPrice(明文/已登录)", "raw": raw}
            # 如果含PUA字符，字体解码
            decoded = decode_font(raw)
            if is_valid_price(decoded, raw_text=raw):
                return {"price": decoded, "source": "layer1:itemPrice+font", "raw": raw}
        # 直接返回（可能已含PUA字符但被JSON序列化替换）
        if data.get("jdPrice") and '?' not in data["jdPrice"] and is_valid_price(data["jdPrice"]):
            return {"price": data["jdPrice"], "source": "layer1:itemPrice", "raw": data["jdPrice"]}
    except:
        pass
    return {}


def extract_price_layer2(page) -> dict:
    """层2: DOM选择器直接读取渲染后的价格文本"""
    try:
        info = page.evaluate("""() => {
            const r = {};
            // 主价格元素
            const mainPrice = document.getElementById('main_price');
            if (mainPrice) {
                r.mainPriceText = mainPrice.textContent.trim();
                r.mainPriceHTML = mainPrice.innerHTML;
                // 获取计算后样式确认字体
                const cs = window.getComputedStyle(mainPrice);
                r.fontFamily = cs.fontFamily;
            }
            // 所有包含价格文本的元素
            const priceEls = document.querySelectorAll('.price, [class*="price"], .p-price, .summary-price, .goods-price');
            const texts = [];
            priceEls.forEach(el => {
                const t = el.textContent.trim();
                if (t && /[¥￥\\d]/.test(t) && !texts.includes(t))
                    texts.push(t);
            });
            r.allPriceTexts = texts.slice(0, 5);
            return r;
        }""")

        # 解析每个价格文本 — 必须不含'?'才接受
        for txt in info.get("allPriceTexts", []):
            if '?' in txt:
                continue  # 字体加密，跳过
            cleaned = re.sub(r'[^\d.]', '', txt)
            if is_valid_price(cleaned) and len(cleaned) >= 2:
                return {"price": cleaned, "source": f"layer2:DOM({txt[:20]})"}

        if info.get("mainPriceText") and '?' not in info["mainPriceText"]:
            cleaned = re.sub(r'[^\d.]', '', info["mainPriceText"])
            if is_valid_price(cleaned) and len(cleaned) >= 2:
                return {"price": cleaned, "source": "layer2:mainPrice"}
    except:
        pass
    return {}


def extract_price_layer3(page) -> dict:
    """层3: 拦截XHR/API响应获取价格"""
    try:
        # 尝试从window._itemOnly获取
        data = page.evaluate("""() => {
            const r = {};
            if (window._itemOnly && window._itemOnly.item) {
                const item = window._itemOnly.item;
                r.skuName = item.skuName;
                // 搜索所有价格相关字段
                for (const k of Object.keys(item)) {
                    const v = item[k];
                    if (typeof v === 'string' && /^\\d{3,8}\\.?\\d*$/.test(v))
                        r[k] = v;
                    if (typeof v === 'number' && v > 0 && v < 10000000)
                        r[k] = String(v);
                }
            }
            // 也检查 priceArr
            if (window.itemPrice && window.itemPrice.priceArr) {
                r.priceArr = window.itemPrice.priceArr;
            }
            return r;
        }""")

        # 从item字段找价格 - 排除非价格ID字段
        NON_PRICE_FIELDS = {'brandId', 'skuId', 'venderId', 'shopId', 'categoryId',
                           'cid1', 'cid2', 'cid3', 'weight', 'image', 'state',
                           'length', 'width', 'height', 'id', 'spId', 'popId'}
        for k, v in data.items():
            if k in NON_PRICE_FIELDS:
                continue
            if not any(kw in k.lower() for kw in ['price', 'amount', 'cost', 'sale', 'discount']):
                continue  # 只从明确的price字段提取
            if isinstance(v, str) and re.match(r'^\d{3,8}\.?\d*$', v):
                if is_valid_price(v):
                    return {"price": v, "source": f"layer3:_itemOnly.{k}"}
    except:
        pass
    return {}


def extract_price_layer4(page) -> dict:
    """层4: SKU变体文本 / 已选配置"""
    try:
        texts = page.evaluate("""() => {
            const texts = [];
            // SKU选择器
            const sel = document.querySelector('#skuChoose1, [class*="sku-choose"] span, .choose-support span');
            if (sel) texts.push(sel.textContent.trim());
            // 已选配置
            const chosen = document.querySelector('.selected, [class*="selected"], [class*="active"]');
            if (chosen) texts.push(chosen.textContent.trim());
            // body中的已选文本
            const body = document.body.innerText;
            const m = body.match(/已选[：:]\\s*([^\\n]{5,50})/);
            if (m) texts.push(m[1]);
            return texts;
        }""")
        for text in texts:
            m = re.search(r'(\d{3,8}\.?\d{0,2})', text)
            if m and is_valid_price(m.group(1)):
                return {"price": m.group(1), "source": f"layer4:variant({text[:30]})"}
    except:
        pass
    return {}


def extract_price_layer5(page) -> dict:
    """层5: 页面全部文本正则提取"""
    try:
        body = page.evaluate("() => document.body.innerText")
        patterns = [
            (r'[¥￥]\s*(\d{3,8}\.?\d{0,2})', 'body:¥'),
            (r'京东价[：:]\s*[¥￥]?\s*(\d{3,8}\.?\d{0,2})', 'body:京东价'),
            (r'到手价[：:]\s*[¥￥]?\s*(\d{3,8}\.?\d{0,2})', 'body:到手价'),
            (r'PLUS价[：:]\s*[¥￥]?\s*(\d{3,8}\.?\d{0,2})', 'body:PLUS价'),
            (r'价格[：:]\s*[¥￥]?\s*(\d{3,8}\.?\d{0,2})', 'body:价格'),
        ]
        for pat, label in patterns:
            m = re.search(pat, body)
            if m and is_valid_price(m.group(1)):
                return {"price": m.group(1).replace(',', ''), "source": f"layer5:{label}"}
    except:
        pass
    return {}


def extract_product_name(page) -> str:
    """提取商品名称"""
    try:
        return page.evaluate("""() => {
            // window对象
            if (window._itemOnly && window._itemOnly.item && window._itemOnly.item.skuName)
                return window._itemOnly.item.skuName;
            if (window.shareConfig && window.shareConfig.title)
                return window.shareConfig.title;
            // DOM选择器
            const sels = ['h1', '.sku-name', '.title', '.item-name', '[class*="name"]', '.product-title'];
            for (const sel of sels) {
                const el = document.querySelector(sel);
                if (el && el.textContent.trim().length > 3)
                    return el.textContent.trim().replace(/\\s+/g, ' ');
            }
            return document.title.split('【')[0].trim();
        }""")
    except:
        return ""


def extract_shop(page) -> str:
    """提取店铺名称"""
    try:
        return page.evaluate("""() => {
            if (window._itemInfo && window._itemInfo.shopFloor && window._itemInfo.shopFloor.shopInfo)
                return window._itemInfo.shopFloor.shopInfo.shopName;
            const sels = ['.shop-name a', '[class*="shop-name"]', '.shopName a', '.vender-name a'];
            for (const sel of sels) {
                const el = document.querySelector(sel);
                if (el) return el.textContent.trim();
            }
            return '';
        }""")
    except:
        return ""


# ═══════════════════════════════════════════════
#  价格提取主函数 — 多层依次尝试
# ═══════════════════════════════════════════════

def extract_price_all_layers(page) -> dict:
    """依次尝试所有层，返回第一个有效结果"""
    layers = [
        extract_price_layer1,
        extract_price_layer2,
        extract_price_layer3,
        extract_price_layer4,
        extract_price_layer5,
    ]

    for layer_fn in layers:
        result = layer_fn(page)
        price_val = result.get("price", "")
        raw_hint = result.get("raw", price_val)
        if result and is_valid_price(price_val, raw_text=raw_hint):
            return result

    return {"price": "", "source": "none"}


# ═══════════════════════════════════════════════
#  浏览器启动策略 — 三级优先级
# ═══════════════════════════════════════════════

def try_persistent_profile(sku: str) -> dict:
    """优先级1: 使用持久化Chrome Profile (保留已登录态)"""
    print("[P1] 尝试持久化Chrome Profile...")

    profile_path = str(PROFILE_DIR.resolve())

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,
                channel="chrome",
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins",
                ],
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
                locale="zh-CN",
            )
        except Exception as e:
            print(f"  [WARN] 持久化Profile失败: {e}")
            return {}

        # 同时加载cookies.json作为补充
        if COOKIE_FILE.exists():
            try:
                with open(COOKIE_FILE) as f:
                    extra_cookies = json.load(f)
                for c in extra_cookies:
                    c.setdefault("sameSite", "Lax")
                    c.setdefault("httpOnly", False)
                context.add_cookies(extra_cookies)
            except:
                pass

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        page = context.new_page()
        result = _do_fetch(page, sku, "P1:persistent")
        context.close()
        return result


def try_visible_browser(sku: str) -> dict:
    """优先级2: 真实可见浏览器"""
    print("[P2] 尝试可见浏览器模式...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
        except:
            browser = p.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        # 加载已有cookie
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE) as f:
                cookies = json.load(f)
            for c in cookies:
                c.setdefault("sameSite", "Lax")
                c.setdefault("httpOnly", False)
            context.add_cookies(cookies)

        page = context.new_page()
        result = _do_fetch(page, sku, "P2:visible")
        browser.close()
        return result


def try_headless(sku: str) -> dict:
    """优先级3: 无头模式"""
    print("[P3] 尝试无头模式...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36",
            locale="zh-CN",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """)

        if COOKIE_FILE.exists():
            with open(COOKIE_FILE) as f:
                cookies = json.load(f)
            for c in cookies:
                c.setdefault("sameSite", "Lax")
                c.setdefault("httpOnly", False)
            context.add_cookies(cookies)

        page = context.new_page()
        result = _do_fetch(page, sku, "P3:headless")
        browser.close()
        return result


def _do_fetch(page, sku: str, strategy: str) -> dict:
    """执行实际的价格抓取"""
    url = f"https://item.m.jd.com/product/{sku}.html"

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        title = page.title()
        if "频控" in title:
            return {"sku": sku, "status": "blocked", "strategy": strategy,
                    "error": "频控拦截", "fetch_time": datetime.now().isoformat()}

        # 多层提取价格
        price_result = extract_price_all_layers(page)
        name = extract_product_name(page)
        shop = extract_shop(page)

        # 自动保存cookie
        try:
            cookies = page.context.cookies()
            with open(COOKIE_FILE, "w") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
        except:
            pass

        price_val = price_result.get("price", "")

        return {
            "sku": sku,
            "name": name,
            "price": price_val,
            "shop": shop,
            "price_source": price_result.get("source", "none"),
            "strategy": strategy,
            "status": "success" if is_valid_price(price_val) else "price_invalid",
            "fetch_time": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"sku": sku, "strategy": strategy, "status": "error",
                "error": str(e)[:200], "fetch_time": datetime.now().isoformat()}


# ═══════════════════════════════════════════════
#  主函数 — 三级优先级 + 多层验证
# ═══════════════════════════════════════════════

def save_result(result: dict):
    monitor_dir = SKILL_DIR / "monitors"
    monitor_dir.mkdir(exist_ok=True)
    monitor_file = monitor_dir / f"{result['sku']}.json"

    history = []
    if monitor_file.exists():
        with open(monitor_file) as f:
            history = json.load(f).get("history", [])

    history.append({
        "price": result.get("price", ""),
        "name": result.get("name", ""),
        "source": result.get("price_source", ""),
        "strategy": result.get("strategy", ""),
        "time": result.get("fetch_time", "")
    })
    history = [h for h in history if h.get("price")]  # 只保留有效价格
    history = history[-30:]

    save_data = {
        "sku": result["sku"],
        "name": result.get("name", ""),
        "current_price": result.get("price", ""),
        "shop": result.get("shop", ""),
        "price_source": result.get("price_source", ""),
        "last_strategy": result.get("strategy", ""),
        "history": history,
        "last_update": result.get("fetch_time", "")
    }
    with open(monitor_file, "w") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    return str(monitor_file)


def main():
    parser = argparse.ArgumentParser(description="京东价格获取 — 三重保障完整版")
    parser.add_argument("--sku", required=True, help="京东商品SKU")
    parser.add_argument("--headless", action="store_true", help="强制无头模式")
    args = parser.parse_args()

    sku = args.sku
    result = None

    # ===== 三级优先级策略 =====
    strategies = [
        (try_persistent_profile, "P1: 持久化Chrome Profile"),
        (try_visible_browser, "P2: 真实可见浏览器"),
    ]

    if args.headless:
        strategies = [(try_headless, "P3: 无头模式")]

    for strategy_fn, label in strategies:
        print(f"\n{'='*50}")
        print(f"  {label}")
        print(f"{'='*50}")

        result = strategy_fn(sku)

        if result.get("status") == "blocked":
            print(f"  ⚠️ 被拦截，尝试下一级...")
            continue

        if result.get("status") == "error":
            print(f"  ⚠️ 错误: {result.get('error')}，尝试下一级...")
            continue

        price = result.get("price", "")
        if not is_valid_price(price):
            print(f"  ⚠️ 价格无效 ('{price}')，尝试下一级...")
            continue

        # ✅ 成功获取有效价格！
        break

    # 如果所有策略都失败，最后尝试无头模式
    if not result or not is_valid_price(result.get("price", "")):
        if not args.headless:
            print(f"\n  ⚠️ P1/P2均失败，最后尝试P3无头模式...")
            result = try_headless(sku)

    # 保存
    output_file = save_result(result) if result else "N/A"

    # 输出
    price_str = result.get("price", "") if result else ""
    price_fmt = f"¥{float(price_str):.2f}" if price_str and price_str.replace('.','').isdigit() else (price_str or "N/A")

    print(f"\n{'='*55}")
    print(f"  📦 京东商品信息")
    print(f"{'='*55}")
    print(f"  SKU:    {sku}")
    print(f"  名称:   {result.get('name', 'N/A') if result else 'N/A'}")
    print(f"  价格:   {price_fmt}")
    print(f"  店铺:   {result.get('shop', 'N/A') if result else 'N/A'}")
    print(f"  来源:   {result.get('price_source', 'N/A') if result else 'N/A'}")
    print(f"  策略:   {result.get('strategy', 'N/A') if result else 'N/A'}")
    print(f"  状态:   {result.get('status', 'N/A') if result else 'N/A'}")

    if result and not is_valid_price(result.get("price", "")):
        print(f"\n  ⚠️ 所有策略均未能获取有效价格")
        print(f"  建议: 运行 python login.py 手动登录京东")
    elif result and result.get("status") == "blocked":
        print(f"\n  ⚠️ 被反爬拦截，建议使用 --headless 以外的模式")

    print(f"\n  💾 {output_file}")


if __name__ == "__main__":
    main()
