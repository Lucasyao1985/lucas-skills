#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_test.py — crypto-signal-agent 冒烟测试
════════════════════════════════════════════════════════
Part A 离线单元测试: 指标数学、阈值分层、输出契约（无需网络）
Part B 在线实战测试: 端点可达性/新鲜度 + 端到端信号生成（需网络）

用法:
    python tests/smoke_test.py                # 全部测试
    python tests/smoke_test.py --offline      # 仅离线部分
    python tests/smoke_test.py --symbol SOLUSDT  # 指定端到端币种

退出码: 0=全部通过, 1=存在失败。CI/定时任务可直接使用。
"""

import argparse
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import signal_agent as sa  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def approx(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


# ════════════════════════════════════════════════════════════════
# Part A — 离线单元测试
# ════════════════════════════════════════════════════════════════
def test_indicators():
    print("\n[A1] clip 边界")
    check("下界", sa.clip(-150) == -100)
    check("上界", sa.clip(150) == 100)
    check("区间内", sa.clip(42) == 42)

    print("\n[A2] EMA 已知值")
    closes = [float(i) for i in range(1, 31)]          # 1..30 线性序列
    e = sa.ema(closes, 10)
    check("EMA(线性序列) 单调且收敛于尾部均值附近", e > 20 and e < 30, f"got {e}")
    check("EMA 常数序列=常数", approx(sa.ema([5.0] * 25, 9), 5.0))

    print("\n[A3] Wilder ATR")
    kl = [[0, 12, 10, 11, 11, 0]] * 2 + [
        [0, 11 + i * 0.5, 10 + i * 0.5, 10.5 + i * 0.5, 11 + i * 0.5, 0]
        for i in range(20)]
    a1 = sa.wilder_atr(kl, 14)
    check("ATR 为正", a1 > 0, f"got {a1}")
    check("ATR(Wilder) ≤ 平均TR(SMA)当波动收窄",
          approx(sa.wilder_atr([[0, 2, 1, 1.5, 2, 0]] * 15, 14),
                 sum([1.0] * 14) / 14, 1e-9))

    print("\n[A4] RSI 序列")
    up = [float(i) for i in range(1, 40)]              # 全涨 → RSI=100
    down = [-float(i) for i in range(1, 40)]           # 全跌 → RSI=0
    s_up, s_down = sa.rsi_series(up), sa.rsi_series(down)
    check("全涨 RSI=100", approx(s_up[-1], 100.0))
    check("全跌 RSI=0", approx(s_down[-1], 0.0))
    mixed = [10, 11, 10.5, 11.5, 11, 12, 11.4, 12.4] * 6
    m = sa.rsi_series(mixed)[-1]
    check("混合序列 RSI ∈ (0,100)", 0 < m < 100, f"got {m}")
    check("短序列填充50", sa.rsi_series([1, 2, 3])[-1] == 50)

    print("\n[A5] 资金费率分层（原始小数）")
    cases = [(0.0006, -80), (0.0003, -40), (0.00021, -40), (0.0001, -10),
             (0.0, 0), (-0.0002, 40), (-0.0004, 80), (0.001, -80)]
    for rate, want in cases:
        got = sa.funding_tier(rate)
        check(f"rate={rate:+.4f} → {want}", got == want, f"got {got}")

    print("\n[A6] FNG 逆向分层")
    fcases = [(10, 80), (30, 40), (50, 0), (70, -40), (90, -80)]
    for v, want in fcases:
        got = sa.fng_tier(v)
        check(f"fng={v} → {want}", got == want, f"got {got}")

    print("\n[A7] 合成权重与方向死区")
    check("权重和=1", approx(sum(sa.COMPOSITE_WEIGHTS.values()), 1.0))
    check("+35 → 做多", sa.decide_direction(35) == "做多")
    check("+34.9 → 观望", sa.decide_direction(34.9) == "观望")
    check("-35 → 做空", sa.decide_direction(-35) == "做空")
    check("-34.9 → 观望", sa.decide_direction(-34.9) == "观望")
    check("0 → 观望", sa.decide_direction(0) == "观望")


def test_output_contract():
    print("\n[A8] §7 输出契约（做多样例）")
    sample = {
        "symbol": "BTCUSDT", "direction": "做多", "composite": 52.3,
        "entry": [93000.0, 93200.0], "stop": 91500.0,
        "targets": [94500.0, 96000.0], "rr": 2.1,
        "win_rate": 68.2, "signal_strength": 52, "confidence": 95,
        "risk_flags": [], "notes": [],
        "data_time_utc": "2026-08-22 08:00:00", "_debug": {},
    }
    out = sa.format_cn(sample)
    lines = out.splitlines()
    check("首行=方向：做多", lines[0] == "方向：做多")
    check("包含入场区间", any(l.startswith("入场区间：$") for l in lines))
    check("包含止损位", any(l.startswith("止损位：$") for l in lines))
    check("目标位含主/延伸", any("（主）/" in l and "（延伸）" in l for l in lines))
    check("评分格式", any(re.fullmatch(r"方向评分：\+\d+\.\d / 100", l) for l in lines))

    print("\n[A9] §7 输出契约（观望样例）")
    wait = dict(sample, direction="观望", entry=[None, None], stop=None,
                targets=[None, None], rr=None, win_rate=None,
                risk_flags=["EXTREME_VOLATILITY"])
    out_w = sa.format_cn(wait)
    lw = out_w.splitlines()
    check("首行=方向：观望", lw[0] == "方向：观望")
    check("观望时三行均为—", all(any(l == f"{k}：" + "—" for l in lw)
                              for k in ("入场区间", "止损位", "目标位")))
    check("风控标记输出", any("EXTREME_VOLATILITY" in l for l in lw))


def test_macro_layer():
    print("\n[A10] 宏观事件窗口（FOMC/CPI 类门控）")
    now = 1_800_000_000
    ev = lambda title, impact, dt: {"title": title, "impact": impact, "ts": now + dt * 3600}
    f, n = sa.macro_flag([ev("CPI y/y", "High", -1)], now_ts=now)          # 1h 前发布
    check("High事件后1h内 → 触发静默窗", f is not None and f["title"] == "CPI y/y")
    f, _ = sa.macro_flag([ev("FOMC Statement", "High", -3)], now_ts=now)   # 3h 前
    check("High事件3h前 → 已出窗", f is None)
    f, _ = sa.macro_flag([ev("NFP", "High", +1.5)], now_ts=now)            # 1.5h 后
    check("High事件1.5h后将至 → 预警静默", f is not None)
    f, n = sa.macro_flag([ev("Unemployment Claims", "Medium", -2)], now_ts=now)
    check("Medium事件仅提示不封锁", f is None and len(n) == 1)
    f, n = sa.macro_flag([], now_ts=now)
    check("空日历不触发", f is None and n == [])

    print("\n[A11] BTC 联动门控")
    check("做多+BTC暴跌6% → flag", sa.btc_conflict("做多", -6.0, True) == "flag")
    check("做空+BTC暴涨6% → flag", sa.btc_conflict("做空", 6.0, False) == "flag")
    check("做多+BTC跌3%且1h空头 → penalty",
          sa.btc_conflict("做多", -3.0, False) == "penalty")
    check("做多+BTC横盘多头排列 → None", sa.btc_conflict("做多", 0.5, True) is None)
    check("观望方向永不触发", sa.btc_conflict("观望", -9.0, False) is None)

    print("\n[A12] 下一个高影响事件")
    nxt = sa.next_macro_event([ev("PCE", "High", 5), ev("Old", "High", -10),
                               ev("Far", "High", 48)], now_ts=now, within_hours=24)
    check("取24h内最近的High事件", nxt is not None and nxt["title"] == "PCE")
    check("24h外无事件", sa.next_macro_event([ev("Far", "High", 48)], now_ts=now) is None)

    print("\n[A13] ETF 资金流分层（顺势因子，±400 $M/3日 → 满分）")
    ecases = [(None, 0), (0.0, 0), (100.0, 20), (400.0, 80), (730.8, 80),
              (-236.5, -47.3), (-400.0, -80), (-1000.0, -80)]
    for v, want in ecases:
        got = sa.etf_tier(v)
        check(f"sum3={v} → {want}", approx(got, want, 1e-9), f"got {got}")
    check("情绪组权重和=1（带/不带 ETF）",
          all(approx(sum(w.values()), 1.0) for w in sa.SENTIMENT_W.values()))

    print("\n[A14] 主流币画像")
    check("BTC ATR 阈值 0.80", sa.resolve_profile("BTCUSDT")["atr_pct_max"] == 0.80)
    check("DOGE ATR 阈值 1.50", sa.resolve_profile("DOGEUSDT")["atr_pct_max"] == 1.50)
    check("DOGE 深度下限 $1.0M", sa.resolve_profile("DOGEUSDT")["depth_floor"] == 1_000_000)
    check("未收录币走默认画像",
          sa.resolve_profile("PEPEUSDT") == sa.DEFAULT_PROFILE)
    check("主流币清单含 BTC/ETH/DOGE 等 9 币",
          len(sa.MAJOR_COINS) == 9 and {"BTCUSDT", "ETHUSDT", "DOGEUSDT"}
          <= set(sa.MAJOR_COINS))
    check("全部主流币均可解析画像",
          all(sa.resolve_profile(s)["atr_pct_max"] > 0 and
              sa.resolve_profile(s)["depth_floor"] > 0 for s in sa.MAJOR_COINS))


# ════════════════════════════════════════════════════════════════
# Part B — 在线实战测试
# ════════════════════════════════════════════════════════════════
def test_endpoints(sym="BTCUSDT"):
    print(f"\n[B1] 端点可达性与 schema（{sym}）")
    t0 = time.time()
    d = sa.fetch_all(sym)
    fetch_s = time.time() - t0
    check(f"并行抓取完成 < 20s（实际 {fetch_s:.1f}s）", fetch_s < 20)

    def ok(k, cond_fn):
        v = d.get(k, {})
        has_err = isinstance(v, dict) and "error" in v
        detail = str(v.get("error", ""))[:80] if isinstance(v, dict) else ""
        check(k, (not has_err) and cond_fn(v), detail)

    ok("ticker", lambda v: float(v["lastPrice"]) > 0)
    ok("k1h", lambda v: isinstance(v, list) and len(v) >= 24)
    ok("k15m", lambda v: isinstance(v, list) and len(v) >= 32)
    ok("depth", lambda v: len(v.get("bids", [])) > 0 and len(v.get("asks", [])) > 0)
    ok("aggtrades", lambda v: isinstance(v, list))
    ok("oi_hist", lambda v: isinstance(v, list) and len(v) >= 2
       and "sumOpenInterest" in v[0])
    ok("funding", lambda v: "lastFundingRate" in v)
    ok("lsr", lambda v: isinstance(v, list) and "longShortRatio" in v[0])
    ok("fng", lambda v: int(v["data"][0]["value"]) >= 0)
    # 宏观日历（软检查：不可用仅提示）
    evs, err = sa.fetch_macro_events()
    print(f"  ℹ️ 宏观日历: {'可用' if not err else '不可用(允许降级)'}，本周USD高/中影响事件 {len(evs)} 个")
    # 备源可选，失败只提示
    for k in ("okx_spot", "coingecko"):
        v = d.get(k, {})
        print(f"  ℹ️ 备源 {k}: {'可用' if 'error' not in v else '不可用(允许降级)'}")

    print("\n[B2] 数据新鲜度")
    now_ms = time.time() * 1000
    age = (now_ms - int(d["ticker"]["closeTime"])) / 1000
    check(f"ticker.closeTime 距今 {age:.1f}s < 120s", age < 120)
    last_close_1h = int(d["k1h"][-1][6])
    age_k = (now_ms - last_close_1h) / 1000
    check(f"1h K线 closeTime 距今 {age_k/60:.0f}min < 130min", age_k < 130 * 60)

    return d


def test_e2e(symbol):
    print(f"\n[B3] 端到端信号生成（{symbol}，§7 契约校验）")
    script = HERE.parent / "scripts" / "signal_agent.py"
    t0 = time.time()
    p = subprocess.run([sys.executable, str(script), symbol],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=60)
    dt = time.time() - t0
    out = (p.stdout or "").strip()
    first = out.splitlines()[0].strip() if out else ""
    check(f"退出码 0（实际 {p.returncode}）", p.returncode == 0,
          (p.stderr or "")[-200:])
    check(f"总耗时 < 45s（实际 {dt:.1f}s）", dt < 45)
    check(f"首行符合 ^方向：(做多|做空|观望)$ → 「{first}」",
          re.fullmatch(r"方向：(做多|做空|观望)", first) is not None)
    check("包含数据时间行", "数据时间：" in out and "UTC" in out)

    print(f"\n[B4] 多币种 + JSON 模式（{symbol} ETHUSDT DOGEUSDT）")
    p2 = subprocess.run(
        [sys.executable, str(script), symbol, "ETHUSDT", "DOGEUSDT", "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        arr = json.loads(p2.stdout)
        check("JSON 可解析且长度=3", isinstance(arr, list) and len(arr) == 3)
        keys_ok = all(r.get("direction") in ("做多", "做空", "观望") for r in arr)
        check("每个结果的 direction 合法", keys_ok)
        syms = {r.get("symbol") for r in arr}
        check("DOGEUSDT 端到端被覆盖", "DOGEUSDT" in syms, str(syms))
    except Exception as e:
        check("JSON 可解析", False, str(e))

    if symbol.upper() == "BTCUSDT":
        print("\n[B5] ETF 覆盖层端到端（--etf-flow-btc 传入后 notes 应记录）")
        p3 = subprocess.run(
            [sys.executable, str(script), "BTCUSDT",
             "--etf-flow-btc", "101.1,-236.5,730.8", "--json"],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        try:
            r3 = json.loads(p3.stdout)[0]
            comp = (r3.get("_debug") or {}).get("components", {})
            check("ETF 合计进入调试明细", comp.get("etf_sum3_musd") == 595.4,
                  f"got {comp.get('etf_sum3_musd')}")
            check("notes 记录 ETF 净流入",
                  any("ETF" in n for n in r3.get("notes", [])),
                  str(r3.get("notes")))
        except Exception as e:
            check("ETF 端到端 JSON 可解析", False, str(e))


# ════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="仅跑离线单测")
    ap.add_argument("--symbol", default="BTCUSDT")
    args = ap.parse_args()

    t0 = time.time()
    test_indicators()
    test_output_contract()
    test_macro_layer()

    if not args.offline:
        try:
            test_endpoints(args.symbol.upper())
            test_e2e(args.symbol.upper())
        except Exception as e:
            check("在线测试套件未抛异常", False, repr(e))
    else:
        print("\n(--offline) 跳过在线实战测试")

    total = PASS + FAIL
    print(f"\n{'='*52}")
    print(f"冒烟测试结果: {PASS}/{total} 通过, {FAIL} 失败, 用时 {time.time()-t0:.1f}s")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
