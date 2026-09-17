#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal_agent.py — crypto-signal-agent 权威实现（唯一版本）
══════════════════════════════════════════════════════════════════
纯标准库实现（零第三方依赖，任何 Python 3.8+ 可运行）。
多因子加权评分 → 方向信号（1小时展望），输出严格遵循 SKILL.md 契约。
v2.3: 宏观层 — ForexFactory 事件窗口门控 + BTC 联动门控。
v2.4: 主流币画像（按币校准 ATR/深度风控阈值）+ BTC/ETH 现货 ETF
      资金流因子（模型层经 WebFetch 抓 Farside 后经 CLI 传入，见
      references/etf-flows.md）。

用法:
    python scripts/signal_agent.py                      # 默认 BTCUSDT
    python scripts/signal_agent.py ETHUSDT DOGEUSDT     # 任意币安 USDT 交易对
    python scripts/signal_agent.py --major              # 扫描全部主流币预设
    python scripts/signal_agent.py BTCUSDT --json       # 机器可读 JSON 输出
    python scripts/signal_agent.py BTCUSDT --debug      # stderr 输出子因子明细
    python scripts/signal_agent.py BTCUSDT \
        --etf-flow-btc 101.1,-236.5,730.8               # 附带 ETF 净流入(3日,$M)

设计要点（与 SKILL.md / references/ 对应）:
  * 真实历史 OI: openInterestHist 公开端点（forceOrders 已改为需 API key，爆仓因子已移除，
    其权重按 SKILL.md §9 降级规则归并至订单流墙失衡/大单集中度）。
  * 资金费率使用原始小数（0.0001 = 0.01%），阈值与 references/scoring-model.md 一致。
  * 量比仅用已收盘 K 线，避免未收盘蜡烛造成的虚假低量。
  * 双源交叉验证: Binance 主源 vs OKX/CoinGecko 备源（§2.4 协议）。
"""

import argparse
import datetime
import io
import json
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Windows 控制台 UTF-8 兜底 ─────────────────────────────────────
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

UA = {"User-Agent": "crypto-signal-agent/2.4"}
TIMEOUT = 8
MAX_BYTES = 5 * 1024 * 1024  # 响应大小上限，防内存耗尽

# 主源 + 公共镜像。受限网络下 api.binance.com / fapi.binance.com 常被阻断，
# 启动时按 /ping 探测自动挑选第一个可达主机（可用环境变量覆盖主源）。
SPOT_HOSTS = [
    os.environ.get("BINANCE_SPOT_HOST", "https://api.binance.com"),
    "https://data-api.binance.vision",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
]
FAPI_HOSTS = [
    os.environ.get("BINANCE_FAPI_HOST", "https://fapi.binance.com"),
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fdata.binance.vision",
]
SPOT = SPOT_HOSTS[0]
FAPI = FAPI_HOSTS[0]


def _probe(base, path, timeout=5):
    """主机可达性探测（GET ping，仅看 200）。"""
    import urllib.request
    try:
        req = urllib.request.Request(base + path, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def resolve_hosts():
    """解析本次运行实际使用的 spot / futures 主机，写回全局 SPOT / FAPI。"""
    global SPOT, FAPI
    for h in SPOT_HOSTS:
        if _probe(h, "/api/v3/ping"):
            SPOT = h
            break
    for h in FAPI_HOSTS:
        if _probe(h, "/fapi/v1/ping"):
            FAPI = h
            break
    return SPOT, FAPI


# ════════════════════════════════════════════════════════════════
# 网络层
# ════════════════════════════════════════════════════════════════
def fetch_json(url, retries=1):
    """带超时/重试/大小上限的 GET。失败返回 {'error': ...}。"""
    import urllib.request
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read(MAX_BYTES)
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            if attempt >= retries:
                return {"error": str(e)}
            time.sleep(0.4)
    return {"error": "unreachable"}


# ════════════════════════════════════════════════════════════════
# 指标层（纯函数，供冒烟测试导入）
# ════════════════════════════════════════════════════════════════
def clip(v, lo=-100.0, hi=100.0):
    return max(lo, min(hi, v))


def ema(closes, period):
    """标准 EMA：SMA 种子 + 指数平滑。"""
    if not closes:
        return 0.0
    if len(closes) < period:
        period = len(closes)
    k = 2.0 / (period + 1)
    val = sum(closes[:period]) / period
    for c in closes[period:]:
        val = c * k + val * (1 - k)
    return val


def wilder_atr(klines, period=14):
    """Wilder RMA 平滑的 ATR（非 SMA），klines = [[o,h,l,c,...],...]"""
    trs = []
    for i in range(1, len(klines)):
        h, l = float(klines[i][2]), float(klines[i][3])
        pc = float(klines[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return 0.0
    if len(trs) < period:
        return sum(trs) / len(trs)
    rma = sum(trs[:period]) / period
    for t in trs[period:]:
        rma = (rma * (period - 1) + t) / period
    return rma


def rsi_series(closes, period=14):
    """Wilder RSI 序列，与 closes 对齐；前 period 位填充 50。"""
    n = len(closes)
    out = [50.0] * n
    if n < period + 1:
        return out
    gains, losses = [], []
    for i in range(1, n):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def funding_tier(rate_raw):
    """资金费率分层（原始小数）。0.0005 = 0.05%/期。返回 [-80, +80] 分值。"""
    if rate_raw > 0.0005:
        return -80          # 多头拥挤 → 逆向看空
    if rate_raw > 0.0002:
        return -40
    if rate_raw < -0.0003:
        return +80          # 空头拥挤 → 逆向看多
    if rate_raw < -0.0001:
        return +40
    return clip(rate_raw * -100000)


def fng_tier(value):
    """恐惧贪婪指数逆向分层，返回 [-80, +80]。"""
    if value < 20:
        return 80
    if value < 35:
        return 40
    if value > 80:
        return -80
    if value > 65:
        return -40
    return (value - 50) * -2


COMPOSITE_WEIGHTS = {"trend": 0.30, "volume": 0.20,
                     "derivatives": 0.25, "orderflow": 0.15, "sentiment": 0.10}
assert abs(sum(COMPOSITE_WEIGHTS.values()) - 1.0) < 1e-9

SENTIMENT_W = {
    "with_etf":  {"fng": 0.35, "funding": 0.35, "etf": 0.30},   # BTC/ETH（有 ETF 数据时）
    "no_etf":    {"fng": 0.50, "funding": 0.50, "etf": 0.0},    # 山寨币或 ETF 数据缺失
}
for _w in SENTIMENT_W.values():
    assert abs(sum(_w.values()) - 1.0) < 1e-9


# ════════════════════════════════════════════════════════════════
# 主流币画像（v2.4）：风控阈值按币校准，防山寨币被 BTC 口径误杀
# 深度实测(2026-08-22, 全100档): BTC≈$1.5M / ETH≈$1.75M / SOL≈$4.4M / DOGE≈$1.7M
# depth_floor 取典型深度的 ~1/3 作下限（宁松勿误杀；触发即强制观望）
# ════════════════════════════════════════════════════════════════
MAJOR_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
               "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT"]

COIN_PROFILES = {
    #        atr_pct_max: EXTREME_VOLATILITY 阈值(1h ATR%)   depth_floor: 全100档深度下限(USD)
    "BTC":  {"atr_pct_max": 0.80, "depth_floor": 1_000_000},
    "ETH":  {"atr_pct_max": 0.90, "depth_floor": 1_000_000},
    "SOL":  {"atr_pct_max": 1.20, "depth_floor": 1_500_000},
    "BNB":  {"atr_pct_max": 1.00, "depth_floor": 800_000},
    "XRP":  {"atr_pct_max": 1.20, "depth_floor": 800_000},
    "DOGE": {"atr_pct_max": 1.50, "depth_floor": 1_000_000},
    "ADA":  {"atr_pct_max": 1.20, "depth_floor": 500_000},
    "AVAX": {"atr_pct_max": 1.50, "depth_floor": 400_000},
    "LINK": {"atr_pct_max": 1.50, "depth_floor": 400_000},
}
DEFAULT_PROFILE = {"atr_pct_max": 1.50, "depth_floor": 300_000}


def resolve_profile(symbol):
    """按交易对解析币种画像；未收录币种走保守默认（山寨波动/深度容忍更高）。"""
    base = symbol[:-4] if symbol.endswith("USDT") else symbol.upper()
    return COIN_PROFILES.get(base, DEFAULT_PROFILE)


def etf_tier(sum3_musd):
    """现货 ETF 近3交易日净流入合计（百万美元）→ [-80, +80]。
    注意：与 F&G/资金费率的逆向语义相反，ETF 资金流是**顺势**因子
    （机构增量买盘推价格、增量卖盘压价格）。±400 $M/3日 → 满分 ±80。"""
    if sum3_musd is None:
        return 0
    return clip(sum3_musd / 5.0, -80, 80)


# ════════════════════════════════════════════════════════════════
# 宏观层（v2.3）：事件窗口门控 + BTC 联动门控
# 哲学：宏观不确定性 → 抑制信号（观望），而非修改评分权重
# ════════════════════════════════════════════════════════════════
FF_CAL_URL = ("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
MACRO_PRE_MIN = 120     # 高影响事件前 2 小时进入静默窗
MACRO_POST_MIN = 60     # 事件后 1 小时内仍视为静默
MACRO_NOTE_HOURS = 3    # Medium 事件 ±3h 仅记提示
# 日历磁盘缓存：事件为提前排期，TTL 内复用无害；专用于抵御 429 限频。
# 注意：这是对"禁止缓存"纪律的唯一豁免对象——价格/OI/K线绝不缓存。
CAL_CACHE_PATH = __import__("os").path.join(
    __import__("tempfile").gettempdir(), "csa_ff_calendar_cache.json")
CAL_CACHE_TTL_SEC = 6 * 3600


def fetch_macro_events():
    """拉取本周 USD 高/中影响宏观事件。
    带磁盘缓存(6h TTL)抗限频；失败回退过期缓存；彻底无数据返回空列表。"""
    now_ts = time.time()
    cached = None
    try:
        with open(CAL_CACHE_PATH, encoding="utf-8") as f:
            blob = json.load(f)
        if isinstance(blob, dict) and "events" in blob:
            if now_ts - blob.get("ts", 0) <= CAL_CACHE_TTL_SEC:
                return [e for e in blob["events"]], None          # 新鲜缓存直返
            cached = blob["events"]                               # 过期缓存留作回退
    except Exception:
        pass
    raw = fetch_json(FF_CAL_URL, retries=0)
    if isinstance(raw, list):
        out = []
        for e in raw:
            if e.get("country") != "USD":
                continue
            if e.get("impact") not in ("High", "Medium"):
                continue
            try:
                ts = datetime.datetime.fromisoformat(e["date"]).timestamp()
            except Exception:
                continue
            out.append({"title": e.get("title", "?"), "impact": e["impact"], "ts": ts})
        try:                                                      # 写入缓存
            with open(CAL_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({"ts": now_ts, "events": out}, f)
        except Exception:
            pass
        return out, None
    if cached is not None:                                        # 429 等 → 回退旧缓存
        return [e for e in cached], "calendar_rate_limited_using_stale"
    return [], "calendar_unreachable"


def macro_flag(events, now_ts=None,
               pre_min=MACRO_PRE_MIN, post_min=MACRO_POST_MIN,
               note_hours=MACRO_NOTE_HOURS):
    """纯函数（可测）。返回 (flag_event|None, note_events:list)。
    High 事件落在 [t−pre, t+post] → 强制观望；
    Medium 事件 ±note_hours → 仅提示。"""
    now_ts = now_ts if now_ts is not None else time.time()
    for e in events:
        if e["impact"] == "High" and e["ts"] - pre_min * 60 <= now_ts <= e["ts"] + post_min * 60:
            return e, []
    notes = [e for e in events
             if e["impact"] == "Medium" and abs(e["ts"] - now_ts) <= note_hours * 3600]
    return None, notes


def next_macro_event(events, now_ts=None, within_hours=24):
    """24h 内下一个 USD High 事件（用于输出提示）。"""
    now_ts = now_ts if now_ts is not None else time.time()
    fut = [e for e in events if e["impact"] == "High" and now_ts < e["ts"] <= now_ts + within_hours * 3600]
    return min(fut, key=lambda e: e["ts"]) if fut else None


def btc_conflict(direction, btc_chg_24h, btc_bull_1h):
    """BTC 联动门控（仅用于非 BTC 币种）。纯函数（可测）。
    返回 'flag' | 'penalty' | None。
    BTC 是宏观流动性传导到山寨币的第一通道：
    BTC 24h 暴跌 ≥5% 时做多山寨 = 逆贝塔，强制观望；
    温和逆行(2~5%) → 置信度罚分。"""
    if direction == "做多":
        if btc_chg_24h is not None and btc_chg_24h <= -5:
            return "flag"
        if (btc_chg_24h is not None and btc_chg_24h <= -2) or btc_bull_1h is False:
            return "penalty"
    elif direction == "做空":
        if btc_chg_24h is not None and btc_chg_24h >= 5:
            return "flag"
        if (btc_chg_24h is not None and btc_chg_24h >= 2) or btc_bull_1h is True:
            return "penalty"
    return None


def decide_direction(score):
    """方向死区 ±35（SKILL.md §4.1）。"""
    if score >= 35:
        return "做多"
    if score <= -35:
        return "做空"
    return "观望"


# ════════════════════════════════════════════════════════════════
# 数据获取
# ════════════════════════════════════════════════════════════════
def build_urls(sym):
    return {
        # 主源 — Binance 现货
        "ticker":   f"{SPOT}/api/v3/ticker/24hr?symbol={sym}",
        "k5m":      f"{SPOT}/api/v3/klines?symbol={sym}&interval=5m&limit=48",
        "k15m":     f"{SPOT}/api/v3/klines?symbol={sym}&interval=15m&limit=48",
        "k1h":      f"{SPOT}/api/v3/klines?symbol={sym}&interval=1h&limit=48",
        "k4h":      f"{SPOT}/api/v3/klines?symbol={sym}&interval=4h&limit=30",
        "depth":    f"{SPOT}/api/v3/depth?symbol={sym}&limit=100",
        "aggtrades": f"{SPOT}/api/v3/aggTrades?symbol={sym}&limit=500",
        # 衍生品 — Binance 合约（公开端点）
        "oi_hist":  f"{FAPI}/futures/data/openInterestHist?symbol={sym}&period=15m&limit=9",
        "funding":  f"{FAPI}/fapi/v1/premiumIndex?symbol={sym}",
        "lsr":      f"{FAPI}/futures/data/topLongShortAccountRatio?symbol={sym}&period=5m&limit=1",
        # 备源交叉验证
        "okx_spot": "https://www.okx.com/api/v5/market/ticker?instId="
                    + sym.replace("USDT", "-USDT"),
        "coingecko": None,  # 需要币名映射，单独处理
        "fng":      "https://api.alternative.me/fng/?limit=1",
    }


COINGECKO_IDS = {  # 常用映射；未收录则跳过该备源（不罚分）
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "DOGE": "dogecoin",
    "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
}


def fetch_all(sym, debug=False):
    urls = build_urls(sym)
    base = sym[:-4]
    if base in COINGECKO_IDS:
        urls["coingecko"] = ("https://api.coingecko.com/api/v3/simple/price?ids="
                             + COINGECKO_IDS[base]
                             + "&vs_currencies=usd&include_last_updated_at=true")
    data = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_json, u): k for k, u in urls.items() if u}
        for f in as_completed(futs):
            data[futs[f]] = f.result()
    missing = [k for k, u in urls.items() if u and k not in data]
    for k in missing:
        data[k] = {"error": "not fetched"}
    return data


# ════════════════════════════════════════════════════════════════
# 分析主流程
# ════════════════════════════════════════════════════════════════
def analyze_symbol(symbol, debug=False, etf_sum3=None):
    """etf_sum3: 该币种现货 ETF 近3交易日净流入合计（$M，仅 BTC/ETH 有意义；
    None = 无数据 → 情绪组按 50/50 旧权重，不罚分不阻断）。"""
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    if not re.fullmatch(r"[A-Z0-9]{2,10}USDT", symbol):
        return {"error": f"非法交易对: {symbol}"}

    d = fetch_all(symbol, debug)
    now_ms = int(time.time() * 1000)
    notes, flags = [], []

    def bad(key):
        return "error" in d.get(key, {})

    # ── 1.5 宏观数据（事件日历 + BTC 联动基准）──────────────────
    macro_events, macro_err = fetch_macro_events()
    if macro_err:
        notes.append("宏观日历不可用(仅提示层缺失)")
        macro_events = []
    btc_chg = btc_bull = None
    if symbol != "BTCUSDT":
        try:
            bt = fetch_json(f"{SPOT}/api/v3/ticker/24hr?symbol=BTCUSDT", retries=0)
            bk = fetch_json(f"{SPOT}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=30", retries=0)
            if isinstance(bt, dict) and "lastPrice" in bt:
                btc_chg = float(bt.get("priceChangePercent", 0) or 0)
            if isinstance(bk, list) and len(bk) >= 22:
                bc = [float(x[4]) for x in bk]
                btc_bull = ema(bc, 9) > ema(bc, 21)
        except Exception:
            pass

    # ── 1. 价格与新鲜度 ─────────────────────────────────────────
    ticker = d["ticker"]
    price = float(ticker.get("lastPrice", 0) or 0)
    if price <= 0 or bad("ticker"):
        return {"symbol": symbol, "error": "无法获取 Binance 实时行情",
                "detail": ticker.get("error", "empty lastPrice")}
    ts_close = int(ticker.get("closeTime", 0))
    if ts_close and now_ms - ts_close > 60_000:
        notes.append("ticker 时间戳偏旧")

    k15m, k1h, k4h, k5m = d["k15m"], d["k1h"], d["k4h"], d["k5m"]
    stale_klines = 0
    interval_ms = {"k5m": 300_000, "k15m": 900_000, "k1h": 3_600_000, "k4h": 14_400_000}
    for key, kl in (("k5m", k5m), ("k15m", k15m), ("k1h", k1h), ("k4h", k4h)):
        if bad(key) or not isinstance(kl, list) or len(kl) < 14:
            stale_klines += 1
            continue
        if now_ms - int(kl[-1][6]) > 2 * interval_ms[key]:
            stale_klines += 1
    if stale_klines >= 2:
        flags.append("DATA_STALE")

    # ── 2. 交叉验证（§2.4）───────────────────────────────────────
    p_okx = p_cg = dev_okx = dev_cg = None
    okx = d.get("okx_spot", {})
    if isinstance(okx.get("data"), list) and okx["data"]:
        try:
            p_okx = float(okx["data"][0]["last"])
            dev_okx = abs(price - p_okx) / price
        except Exception:
            pass
    cg = d.get("coingecko", {})
    if not bad("coingecko") and cg:
        try:
            p_cg = float(cg[list(cg)[0]]["usd"]) if "error" not in cg and cg else None
            if p_cg:
                dev_cg = abs(price - p_cg) / price
        except Exception:
            pass

    conf = 1.0
    # OKX 为硬门控：>0.5% 先按 §2.4 重取一次，仍超限才判冲突
    if dev_okx is not None and dev_okx > 0.005:
        p2 = fetch_json(build_urls(symbol)["okx_spot"], retries=0)
        try:
            dev_okx = abs(price - float(p2["data"][0]["last"])) / price
        except Exception:
            pass
    if dev_okx is not None and dev_okx > 0.005:
        flags.append("DATA_CONFLICT")          # 实时CEX价差异常 → 强制观望
    elif any(x > 0.0015 for x in (dev_okx, dev_cg) if x is not None):
        conf = 0.85
        notes.append("备源价差偏高")
    # CoinGecko 为软校验：多所聚合天然滞后，急跌/急涨中偏差大不判冲突只降置信
    if dev_cg is not None and dev_cg > 0.005:
        conf = min(conf, 0.85)
        notes.append("CoinGecko 聚合价滞后(仅降置信)")
    divs = [x for x in (dev_okx, dev_cg) if x is not None]
    if not divs:
        conf = min(conf, 0.80)                 # 无可用备源
        notes.append("无备源验证")

    # ── 3. 趋势分（权重 30%）────────────────────────────────────
    def closes(kl):
        return [float(x[4]) for x in kl] if isinstance(kl, list) and kl else []

    def ema_leg(clist, weight):
        """单条 EMA 对齐腿；数据不足返回中性（不计入分子与分母）。"""
        if len(clist) >= 22:
            return (weight if ema(clist, 9) > ema(clist, 21) else 0), weight
        return 0, 0

    c1h, c15m, c5m = closes(k1h), closes(k15m), closes(k5m)
    bull_w, max_w = 0, 0
    for clist, w in ((c1h, 3), (c15m, 2), (c5m, 1)):
        b, m = ema_leg(clist, w)
        bull_w += b
        max_w += m
    ema_score = ((bull_w / max_w) * 200 - 100) if max_w else 0
    if not max_w:
        notes.append("K线数据不足，EMA 对齐计中性")

    highs15 = [float(x[2]) for x in k15m[-10:]] if isinstance(k15m, list) else []
    lows15 = [float(x[3]) for x in k15m[-10:]] if isinstance(k15m, list) else []
    structure_score = 0
    if len(highs15) >= 4 and len(lows15) >= 4:
        hh = lows15[-1] > lows15[-3]
        hl = highs15[-1] > highs15[-3]
        ll = lows15[-1] < lows15[-3]
        lh = highs15[-1] < highs15[-3]
        if hh and hl:
            structure_score = 80
        elif ll and lh:
            structure_score = -80

    rsi15 = rsi_series(c15m)
    rsi_score = 0
    if rsi15 and c15m:
        last_rsi = rsi15[-1]
        if last_rsi > 70:
            rsi_score = -30
        elif last_rsi < 30:
            rsi_score = 30
        w = 6
        cur_low, prev_low = min(c15m[-w:]), min(c15m[-2 * w:-w])
        cur_rsi_lo = min(rsi15[len(rsi15) - w:])
        prev_rsi_lo = min(rsi15[max(len(rsi15) - 2 * w, 0):len(rsi15) - w])
        if cur_low < prev_low and cur_rsi_lo > prev_rsi_lo:
            rsi_score = 60      # 底背离
        elif cur_low > prev_low and cur_rsi_lo < prev_rsi_lo:
            rsi_score = -60     # 顶背离

    trend_score = 0.45 * ema_score + 0.40 * structure_score + 0.15 * rsi_score

    # ── 4. 量能分（权重 20%，仅用已收盘 K 线）───────────────────
    closed_1h = k1h[:-1] if isinstance(k1h, list) else []
    vols_closed = [float(x[5]) for x in closed_1h]
    vol_ratio, delta_trend = 1.0, 0
    if len(vols_closed) >= 21:
        avg20 = sum(vols_closed[-21:-1]) / 20
        vol_ratio = vols_closed[-1] / avg20 if avg20 > 0 else 1.0
        v3 = vols_closed[-3:]
        delta_trend = 1 if v3[0] < v3[1] < v3[2] else (-1 if v3[0] > v3[1] > v3[2] else 0)

    agg = d["aggtrades"]
    taker_buy = taker_sell = 0.0
    if isinstance(agg, list):
        for t in agg[:500]:
            q = float(t.get("q", 0) or 0)
            if t.get("m"):
                taker_sell += q     # maker=卖方 → taker 是买方？注意: m=true 表示卖方是 maker
            else:
                taker_buy += q
    tt = taker_buy + taker_sell
    taker_pct = taker_buy / tt if tt > 0 else 0.5

    volume_score = (0.40 * clip((vol_ratio - 1.0) * 100)
                    + 0.35 * clip((taker_pct - 0.5) * 200)
                    + 0.25 * (delta_trend * 100))

    # ── 5. 衍生品分（权重 25%，真实历史 OI）─────────────────────
    oi_now = oi_prev = None
    oih = d.get("oi_hist")
    if isinstance(oih, list) and len(oih) >= 2:
        try:
            pts = [(int(p["timestamp"]), float(p["sumOpenInterest"])) for p in oih]
            pts.sort()
            oi_now = pts[-1][1]
            target_t = now_ms - 3_600_000
            oi_prev = min(pts, key=lambda p: abs(p[0] - target_t))[1]
        except Exception:
            pass

    fr_raw = 0.0
    try:
        fr_raw = float(d["funding"].get("lastFundingRate", 0) or 0)
    except Exception:
        pass
    funding_score = funding_tier(fr_raw) if d.get("funding") and "error" not in d["funding"] else 0

    lsr_val = 1.0
    lsr = d.get("lsr")
    if isinstance(lsr, list) and lsr:
        try:
            lsr_val = float(lsr[0]["longShortRatio"])
        except Exception:
            pass
    ls_score = clip((1.0 - lsr_val) * 100)

    if oi_now and oi_prev and oi_prev > 0:
        oi_chg_pct = (oi_now - oi_prev) / oi_prev * 100
        px_dir = 1 if len(c1h) >= 2 and c1h[-1] >= c1h[-2] else -1
        oi_score = clip(oi_chg_pct * 10 * px_dir)
    else:
        oi_chg_pct = None
        oi_score = 0
        notes.append("OI 历史不可用，该子项计 0")

    derivatives_score = 0.40 * oi_score + 0.32 * funding_score + 0.28 * ls_score

    # ── 6. 订单流分（权重 15%；爆仓因子因接口关闭已移除并归一）──
    bids = d["depth"].get("bids", []) if not bad("depth") else []
    asks = d["depth"].get("asks", []) if not bad("depth") else []
    wall_score = conc_score = 0.0
    depth_usd = 0.0
    if bids and asks:
        bv = sum(float(p) * float(q) for p, q in bids)      # 全部 100 档
        av = sum(float(p) * float(q) for p, q in asks)
        depth_usd = bv + av
        if depth_usd > 0:
            wall_score = clip((bv - av) / depth_usd * 200)
        top_b = sorted(bids, key=lambda x: float(x[1]), reverse=True)[:10]
        top_a = sorted(asks, key=lambda x: float(x[1]), reverse=True)[:10]
        sb = sum(float(q) for _, q in top_b)
        sa = sum(float(q) for _, q in top_a)
        if sb > 0 and sa > 0:
            conc_score = (float(top_b[0][1]) / sb - float(top_a[0][1]) / sa) * 200
    orderflow_score = 0.59 * wall_score + 0.41 * conc_score  # 原 0.47/0.33/0.20 去除爆仓后归一

    # ── 7. 情绪分（权重 10%；v2.4 起 BTC/ETH 含 ETF 资金流）─────
    fng_val = 50
    fng = d.get("fng", {})
    if not bad("fng") and isinstance(fng.get("data"), list) and fng["data"]:
        try:
            fng_val = int(fng["data"][0]["value"])
        except Exception:
            pass
    etf_score = etf_tier(etf_sum3)
    if etf_sum3 is not None:
        w = SENTIMENT_W["with_etf"]
        notes.append(f"现货ETF净流入(3日): {etf_sum3:+.0f} $M")
    else:
        w = SENTIMENT_W["no_etf"]
    sentiment_score = (w["fng"] * fng_tier(fng_val)
                       + w["funding"] * funding_score
                       + w["etf"] * etf_score)

    # ── 8. 合成分与方向 ─────────────────────────────────────────
    composite = (COMPOSITE_WEIGHTS["trend"] * trend_score
                 + COMPOSITE_WEIGHTS["volume"] * volume_score
                 + COMPOSITE_WEIGHTS["derivatives"] * derivatives_score
                 + COMPOSITE_WEIGHTS["orderflow"] * orderflow_score
                 + COMPOSITE_WEIGHTS["sentiment"] * sentiment_score)
    direction = decide_direction(composite)

    # ── 9. 入场/止损/目标（§4.2）────────────────────────────────
    atr_1h = wilder_atr(k1h if isinstance(k1h, list) else [])
    entry_low = entry_high = stop = tgt1 = tgt2 = rr = None
    if direction != "观望" and isinstance(k1h, list) and len(k1h) >= 4:
        hs = sorted(float(x[2]) for x in k1h)
        ls_ = sorted(float(x[3]) for x in k1h)
        res = next((p for p in hs if p > price), price * 1.02)
        sup = next((p for p in reversed(ls_) if p < price), price * 0.98)
        if direction == "做多":
            entry_low, entry_high = price * 0.9985, price * 1.0010
            stop = max(sup - atr_1h * 0.3, price * 0.985)
            tgt1, tgt2 = res, res + atr_1h * 1.5
            denom = entry_high - stop
            rr = (tgt1 - entry_high) / denom if denom > 0 else 0
        else:
            entry_high, entry_low = price * 1.0015, price * 0.9990
            stop = min(res + atr_1h * 0.3, price * 1.015)
            tgt1, tgt2 = sup, sup - atr_1h * 1.5
            denom = stop - entry_low
            rr = (entry_low - tgt1) / denom if denom > 0 else 0

    # ── 10. 风控标记（§5；v2.4 起阈值按币种画像校准）────────────
    atr_pct = atr_1h / price * 100 if price > 0 else 0
    weekend_or_offhours = time.gmtime().tm_wday >= 5 or time.gmtime().tm_hour < 4
    profile = resolve_profile(symbol)
    liq_floor = profile["depth_floor"] * (0.7 if weekend_or_offhours else 1.0)
    if atr_pct > profile["atr_pct_max"]:
        flags.append("EXTREME_VOLATILITY")
    if abs(fr_raw) > 0.0010:
        flags.append("FUNDING_EXTREME")
    if bids and asks and depth_usd < liq_floor:
        flags.append("LIQUIDITY_THIN")
    if abs(composite) < 20:
        flags.append("AMBIGUOUS_SCORE")
    if conf * 100 < 70:
        flags.append("LOW_CONFIDENCE")
    if direction != "观望" and rr is not None and rr < 1.5:
        flags.append("POOR_RR")

    # ── 宏观门控（v2.3）────────────────────────────────────────
    mflag, mnotes = macro_flag(macro_events, now_ts=now_ms / 1000)
    for e in mnotes:
        notes.append(f"宏观事件临近: {e['title']}")
    if mflag:
        flags.append("MACRO_EVENT_WINDOW")
        notes.append(f"高影响事件静默窗: {mflag['title']}")
    elif direction != "观望":
        nxt = next_macro_event(macro_events, now_ts=now_ms / 1000)
        if nxt:
            hrs = (nxt["ts"] - now_ms / 1000) / 3600
            notes.append(f"未来24h高影响事件: {nxt['title']} ({hrs:.1f}h后)")

    if direction != "观望" and symbol != "BTCUSDT" and btc_chg is not None:
        verdict = btc_conflict(direction, btc_chg, btc_bull)
        if verdict == "flag":
            flags.append("BTC_REGIME_CONFLICT")
            notes.append(f"BTC 24h {btc_chg:+.1f}% 与信号方向强逆行")
        elif verdict == "penalty":
            conf = max(conf - 0.10, 0.0)
            notes.append(f"BTC 联动偏逆(24h {btc_chg:+.1f}%)，置信度 −10")
    if flags:
        direction = "观望"
        entry_low = entry_high = stop = tgt1 = tgt2 = rr = None

    agreement = sum(1 for s in (trend_score, volume_score, derivatives_score,
                                orderflow_score, sentiment_score)
                    if s * composite > 0)
    win_rate = min(40 + abs(composite) / 2 + agreement * 4, 85) if direction != "观望" else None

    return {
        "symbol": symbol, "direction": direction,
        "composite": round(composite, 1),
        "entry": [entry_low, entry_high], "stop": stop,
        "targets": [tgt1, tgt2], "rr": round(rr, 2) if rr else None,
        "win_rate": round(win_rate, 1) if win_rate else None,
        "signal_strength": min(int(abs(composite)), 100),
        "confidence": int(conf * 100),
        "risk_flags": flags, "notes": notes,
        "data_time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts_close / 1000)),
        "_debug": {
            "price": price, "atr_pct": round(atr_pct, 3),
            "sub_scores": {"trend": round(trend_score, 1), "volume": round(volume_score, 1),
                           "derivatives": round(derivatives_score, 1),
                           "orderflow": round(orderflow_score, 1),
                           "sentiment": round(sentiment_score, 1)},
            "components": {"ema": round(ema_score, 1), "structure": structure_score,
                           "rsi": rsi_score, "vol_ratio": round(vol_ratio, 2),
                           "taker_buy_pct": round(taker_pct * 100, 1),
                           "oi_change_1h_pct": round(oi_chg_pct, 2) if oi_chg_pct is not None else None,
                           "funding_raw": fr_raw, "lsr": lsr_val, "fng": fng_val,
                           "etf_sum3_musd": etf_sum3, "etf_score": etf_score,
                           "profile": profile,
                           "depth_usd_top20": round(depth_usd)},
            "cross_check": {"okx_dev_pct": round(dev_okx * 100, 4) if dev_okx else None,
                            "coingecko_dev_pct": round(dev_cg * 100, 4) if dev_cg else None},
            "macro": {"btc_24h_chg": btc_chg, "btc_1h_bull": btc_bull,
                      "usd_high_events_today": [e["title"] for e in macro_events
                                                if e["impact"] == "High"
                                                and abs(e["ts"] - now_ms / 1000) < 12 * 3600]},
        } if debug else {},
    }


# ════════════════════════════════════════════════════════════════
# 输出层 — 严格 §7 契约（stdout 首行必须是 方向：）
# ════════════════════════════════════════════════════════════════
def format_cn(r):
    if "error" in r and r.get("direction") is None:
        return f"方向：观望\n\n入场区间：—\n止损位：—\n目标位：—" \
               f"\n\n方向评分：— / 100\n执行方案：" \
               f"\n  数据可信度：0 %\n  错误：{r['error']} [SYSTEM_ERROR]"
    wait = r["direction"] == "观望"
    lines = [f"方向：{r['direction']}", ""]
    if wait:
        lines += ["入场区间：—", "止损位：—", "目标位：—"]
    else:
        lo, hi = r["entry"]
        lines += [f"入场区间：${lo:,.2f} – ${hi:,.2f}",
                  f"止损位：${r['stop']:,.2f}",
                  f"目标位：${r['targets'][0]:,.2f}（主）/ ${r['targets'][1]:,.2f}（延伸）"]
    lines += [f"", f"方向评分：{r['composite']:+.1f} / 100", "执行方案："]
    if wait:
        lines += [f"  胜率评分：— ", f"  信号强度：{r['signal_strength']} / 100"]
    else:
        lines += [f"  胜率评分：{r['win_rate']:.0f} %",
                  f"  信号强度：{r['signal_strength']} / 100"]
    lines += [f"  数据可信度：{r['confidence']} %",
              f"  数据时间：{r['data_time_utc']} UTC"]
    if r.get("risk_flags"):
        lines.append(f"  风控标记：{', '.join(r['risk_flags'])}")
    return "\n".join(lines)


def _parse_flows(raw):
    """'101.1,-236.5,730.8' → 合计 595.4；非法输入返回 None（不阻断）。"""
    if not raw:
        return None
    try:
        vals = [float(x) for x in raw.split(",") if x.strip()]
        return sum(vals) if vals else None
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="crypto-signal-agent 权威信号引擎")
    ap.add_argument("symbols", nargs="*", default=["BTCUSDT"],
                    help="任意币安 USDT 交易对，默认 BTCUSDT")
    ap.add_argument("--major", action="store_true",
                    help="扫描主流币预设: " + ",".join(c[:-4] for c in MAJOR_COINS)
                         + "（约需 1 分钟）")
    ap.add_argument("--etf-flow-btc", default=None, metavar="M1,M2,M3",
                    help="BTC 现货 ETF 近3交易日净流入（$M，旧→新），如 101.1,-236.5,730.8"
                         "；首值为负数时须用等号连接（--etf-flow-btc=-236.5,...）；"
                         "抓取方法见 references/etf-flows.md")
    ap.add_argument("--etf-flow-eth", default=None, metavar="M1,M2,M3",
                    help="ETH 现货 ETF 近3交易日净流入（$M，旧→新）")
    ap.add_argument("--json", action="store_true", help="输出 JSON（含调试明细）")
    ap.add_argument("--debug", action="store_true", help="stderr 显示子因子计算过程")
    ap.add_argument("--no-futures", action="store_true",
                    help="跳过合约端点（网络阻断 fapi 时加速并避免无效等待）")
    args = ap.parse_args()

    spot_host, fapi_host = resolve_hosts()
    if args.debug:
        print(f"[HOST] spot={spot_host} futures={fapi_host}", file=sys.stderr)
    if args.no_futures:
        globals()["FAPI"] = ""

    etf_map = {"BTCUSDT": _parse_flows(args.etf_flow_btc),
               "ETHUSDT": _parse_flows(args.etf_flow_eth)}
    if args.etf_flow_btc and etf_map["BTCUSDT"] is None:
        print("[WARN] --etf-flow-btc 格式非法，已忽略（ETF 子项计 0）", file=sys.stderr)
    if args.etf_flow_eth and etf_map["ETHUSDT"] is None:
        print("[WARN] --etf-flow-eth 格式非法，已忽略（ETF 子项计 0）", file=sys.stderr)

    symbols = MAJOR_COINS if args.major else args.symbols
    results = [analyze_symbol(s, debug=True, etf_sum3=etf_map.get(s.upper()))
               for s in symbols]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        out = []
        for r in results:
            out.append(format_cn(r))
            dbg = r.get("_debug") or {}
            if args.debug and dbg:
                print(f"[DEBUG {r.get('symbol')}] price={dbg.get('price')} "
                      f"atr%={dbg.get('atr_pct')} sub={dbg.get('sub_scores')} "
                      f"comp={dbg.get('components')}", file=sys.stderr)
        print("\n\n".join(out))

    # 全部失败时以非零码退出（便于脚本化检测）
    if all("error" in r and r.get("direction") is None for r in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
