#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双色球分析工具 v6.3
用法:
  python ssq.py fetch      # 联网抓取最新数据 + 自动复盘
  python ssq.py analyze    # 分析最近30期，输出JSON
  python ssq.py recommend  # 生成4注推荐+结构分
  python ssq.py all        # 一键全流程
  python ssq.py review <期号> <红1> <红2> <红3> <红4> <红5> <红6> <蓝>

依赖: pip install requests beautifulsoup4
数据存储: C:\\Users\\用户名\\.ssq_data\\

v6.3 改动（2026-05）：
  - 数据源从 cwl.gov.cn（被 WAF 拦截 403）迁移至 500.com HTML 表格
  - 500.com 返回 HTML 表格，解析 <tr>/<td> 提取数据
  - 分位分析（嘲风方法）：6 个位置独立统计，每位推荐 TOP2-3 + 组合推荐
  - cwl.gov.cn 返回完整开奖信息（奖池、销售额、各等奖注数）
  - 多窗口分析：10/20/30/50 期并行统计
  - 特征画像推荐：基于多窗口共识构建目标画像，定向生成候选
  - 蓝球独立预测：独立评分模块，蓝球 TOP3
"""

import sys, os, json, math, random, statistics, argparse
from datetime import datetime
from collections import Counter
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"缺少依赖: {e}\n请运行: pip install requests beautifulsoup4")
    sys.exit(1)

TOTAL_COMBOS   = 17_720_024
ANALYZE_WINDOW = 30
RECOMMEND_N    = 4
BASE_URL = "https://datachart.500.com/ssq/history/newinc/history.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json",
}
NO_PROXY = {"http": "", "https": ""}

DATA_DIR     = Path.home() / ".ssq_data"
HIST_FILE    = DATA_DIR / "history.json"
ARCHIVE_FILE = DATA_DIR / "predictions.json"


# ── 1. 抓取 ───────────────────────────────────────────

def fetch_from_500com(issue_count=120, timeout=15):
    """500.com HTML 表格（cwl.gov.cn 被 WAF 拦截后的替代源）"""
    import re as _re
    url = f"https://datachart.500.com/ssq/history/newinc/history.php?limit={issue_count}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                            timeout=timeout, proxies=NO_PROXY)
        resp.raise_for_status()
        html = resp.text
        trs = _re.findall(r'<tr[^>]*>(.*?)</tr>', html, _re.DOTALL)
        records = []
        from datetime import datetime
        weekdays = ['一','二','三','四','五','六','日']
        for tr in trs:
            tds = _re.findall(r'<td[^>]*>(.*?)</td>', tr, _re.DOTALL)
            cleaned = [_re.sub(r'<[^>]+>', '', td).strip() for td in tds]
            if cleaned and len(cleaned) >= 10 and cleaned[1].isdigit() and len(cleaned[1]) == 5:
                period = cleaned[1]
                reds = sorted([int(cleaned[i]) for i in range(2, 8)])
                blue = int(cleaned[8])
                date_str = cleaned[-1] if cleaned[-1].startswith('20') else ''
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    wd = weekdays[dt.weekday()]
                except:
                    wd = ''
                sales = cleaned[12].replace(',', '') if len(cleaned) > 12 else ''
                pool = cleaned[10].replace(',', '') if len(cleaned) > 10 else ''
                records.append({
                    "period": period, "red_balls": reds, "blue_ball": blue,
                    "weekday": wd, "date": f"{date_str}({wd})",
                    "sales": sales, "pool_money": pool, "prize_grades": [],
                })
        return records
    except Exception as e:
        print(f"  500.com 抓取失败: {e}")
        return []


def cmd_fetch(_):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 58)
    print("  [Step 1] 联网抓取")
    print("=" * 58)

    # ── 主数据源：500.com HTML 表格（cwl.gov.cn 被 WAF 拦截）──
    records = fetch_from_500com(120)
    if not records:
        print("FETCH_FAILED:网络请求失败或数据解析异常")
        return
    print(f"  500.com: 获取 {len(records)} 期")

    existing  = _load_history()
    exist_set = {r["period"] for r in existing}
    new_n     = 0
    for r in records:
        if r["period"] not in exist_set:
            existing.append(r); new_n += 1
    existing.sort(key=lambda x: x["period"], reverse=True)
    _save_history(existing)

    lat = existing[0]
    rs  = " ".join(f"{n:02d}" for n in lat["red_balls"])
    print(f"新增 {new_n} 期，本地共 {len(existing)} 期")
    print(f"最新: {lat['period']}  红 {rs}  蓝 {lat['blue_ball']:02d}")

    # ── 验证闭环 ──
    api_latest = records[0]["period"] if records else None
    local_latest = lat["period"]
    if api_latest and api_latest == local_latest:
        print(f"FETCH_OK:{local_latest}")
    elif api_latest and api_latest > local_latest:
        print(f"UPDATE_FAILED:本地 {local_latest} 仍落后于 API {api_latest}")
    else:
        print(f"FETCH_OK:{local_latest}")


    # ── 自动复盘 ──
    if new_n > 0 and len(existing) > 1:
        _auto_review(lat)


def _auto_review(latest_draw):
    """抓取到新数据后，自动用最新开奖号复盘上期预测"""
    arch = _load_archive()
    if not arch:
        return

    period   = latest_draw["period"]
    act_reds = latest_draw["red_balls"]
    act_blue = latest_draw["blue_ball"]

    # 找到最近一条未复盘的预测
    target = None
    for entry in reversed(arch):
        if entry.get("review") is None and entry.get("actual") is None:
            target = entry; break

    if not target:
        return

    print(f"\n── 自动复盘 {period} 期 ──────────────────────────────")
    rs = " ".join(f"{n:02d}" for n in act_reds)
    print(f"开奖: 红 {rs}  蓝 {act_blue:02d}")

    results = []
    for p in target["predictions"]:
        hr = len(set(p["reds"]) & set(act_reds))
        hb = (p["blue"] == act_blue)
        pz = _prize(hr, hb)
        rs2 = " ".join(f"{n:02d}" for n in p["reds"])
        print(f"  #{p['idx']} 红{rs2} 蓝{p['blue']:02d} → 红{hr}/6 蓝{'中' if hb else '×'} {pz}")
        results.append({"idx": p["idx"], "hit_reds": hr, "hit_blue": hb, "prize": pz})

    target["actual"] = {"period": period, "reds": act_reds, "blue": act_blue}
    target["review"] = results
    _save_archive(arch)

    all_hits = [r["hit_reds"] for e in arch if e.get("review") for r in e["review"]]
    if all_hits:
        print(f"累计: {len(all_hits)} 次  红球最高 {max(all_hits)}/6  均值 {statistics.mean(all_hits):.2f}/6")


# ── 2. 统计分析 ──────────────────────────────────────

def _compute_stats(data, full_history=None):
    """单窗口统计分析（保留兼容，多窗口场景调用 _compute_multi_stats）"""
    n = len(data)
    red_freq  = Counter(); blue_freq = Counter()
    for r in data:
        red_freq.update(r["red_balls"]); blue_freq[r["blue_ball"]] += 1

    red_exp  = n * 6 / 33;  red_std  = math.sqrt(red_exp  * (1 - 6/33)) or 1
    blue_exp = n * 1 / 16;  blue_std = math.sqrt(blue_exp * (1 - 1/16)) or 1
    def z(actual, exp, std): return round((actual - exp) / std, 2)

    red_z  = {i: z(red_freq.get(i, 0),  red_exp,  red_std)  for i in range(1, 34)}
    blue_z = {i: z(blue_freq.get(i, 0), blue_exp, blue_std) for i in range(1, 17)}

    red_anom  = sorted([i for i, s in red_z.items()  if s < -2.0], key=lambda x: red_z[x])
    blue_anom = sorted([i for i, s in blue_z.items() if s < -2.0], key=lambda x: blue_z[x])

    red_miss  = {i: 0 for i in range(1, 34)}
    blue_miss = {i: 0 for i in range(1, 17)}
    for r in data:
        for i in range(1, 34):
            if i not in r["red_balls"]: red_miss[i] += 1
        for i in range(1, 17):
            if r["blue_ball"] != i:     blue_miss[i] += 1

    hw = min(20, n)
    rc = Counter(); bc = Counter()
    for r in data[:hw]:
        rc.update(r["red_balls"]); bc[r["blue_ball"]] += 1
    avg_r = hw * 6 / 33; avg_b = hw / 16
    red_hot   = sorted([i for i in range(1,34) if rc.get(i,0) > avg_r],       key=lambda x: -rc.get(x,0))
    red_cold  = sorted([i for i in range(1,34) if rc.get(i,0) < avg_r * 0.5], key=lambda x:  rc.get(x,0))
    blue_hot  = sorted([i for i in range(1,17) if bc.get(i,0) > avg_b],       key=lambda x: -bc.get(x,0))
    blue_cold = sorted([i for i in range(1,17) if bc.get(i,0) < avg_b * 0.5], key=lambda x:  bc.get(x,0))

    odd_c = Counter(); siz_c = Counter(); sums = []; spans = []
    for r in data:
        rb = r["red_balls"]
        odd = sum(x % 2 for x in rb); big = sum(1 for x in rb if x >= 17)
        odd_c[f"{odd}奇{6-odd}偶"] += 1; siz_c[f"{big}大{6-big}小"] += 1
        sums.append(sum(rb)); spans.append(max(rb) - min(rb))

    ssorted = sorted(sums)
    p20 = ssorted[max(0, int(n * 0.20))]; p80 = ssorted[min(n-1, int(n * 0.80))]

    src = full_history if full_history else data
    red_max_miss  = {i: 0 for i in range(1, 34)}
    blue_max_miss = {i: 0 for i in range(1, 17)}
    red_last = {i: None for i in range(1, 34)}; blue_last = {i: None for i in range(1, 17)}
    for idx, r in enumerate(reversed(src)):
        for i in range(1, 34):
            if i in r["red_balls"]:
                if red_last[i] is not None:
                    gap = idx - red_last[i] - 1; red_max_miss[i] = max(red_max_miss[i], gap)
                red_last[i] = idx
        if r["blue_ball"] in range(1, 17):
            bi = r["blue_ball"]
            if blue_last[bi] is not None:
                gap = idx - blue_last[bi] - 1; blue_max_miss[bi] = max(blue_max_miss[bi], gap)
            blue_last[bi] = idx
    total = len(src)
    for i in range(1, 34):
        if red_last[i] is None: red_max_miss[i] = total
    for i in range(1, 17):
        if blue_last[i] is None: blue_max_miss[i] = total

    return {
        "window": n, "latest_period": data[0]["period"],
        "latest_reds": data[0]["red_balls"], "latest_blue": data[0]["blue_ball"],
        "red_anom": red_anom, "blue_anom": blue_anom,
        "red_z": red_z, "blue_z": blue_z,
        "red_miss_top5": sorted(red_miss.items(),  key=lambda x: -x[1])[:5],
        "blue_miss_top3": sorted(blue_miss.items(), key=lambda x: -x[1])[:3],
        "red_hot": red_hot[:8], "red_cold": red_cold[:8],
        "blue_hot": blue_hot[:5], "blue_cold": blue_cold[:5],
        "top_odd": odd_c.most_common(3), "top_size": siz_c.most_common(3),
        "sum_mean": round(statistics.mean(sums), 1),
        "sum_std":  round(statistics.stdev(sums) if n > 1 else 0, 1),
        "sum_p20_p80": [p20, p80], "span_mean": round(statistics.mean(spans), 1),
        "last_reds": set(data[0]["red_balls"]),
        "_red_miss": red_miss, "_blue_miss": blue_miss,
        "_red_max_miss": red_max_miss, "_blue_max_miss": blue_max_miss,
    }


def _compute_multi_stats(full_history, windows=(10, 20, 30, 50)):
    """
    多窗口并行统计：在 10/20/30/50 期窗口上分别计算，
    输出各窗口一致判定（consensus）和分歧（divergence）。
    """
    if not full_history:
        return None
    results = {}
    for w in windows:
        w = min(w, len(full_history))
        if w < 3:
            continue
        data = full_history[:w]
        results[w] = _compute_stats(data, full_history=full_history)

    if not results:
        return None

    # ── 共识分析 ──
    # 所有窗口都判定为冷（z < -1.5）的号码 → 稳定冷号
    # 所有窗口都判定为热（z > 1.0）的号码 → 稳定热号
    # 短窗口冷+长窗口热 → 近期回冷（可能回补）
    # 短窗口热+长窗口冷 → 近期升温（趋势反转）

    red_consensus_cold = []  # 所有窗口都冷
    red_consensus_hot  = []  # 所有窗口都热
    red_diverge        = []  # 短冷长热 or 短热长冷（分歧）
    blue_consensus_cold = []
    blue_consensus_hot  = []
    blue_diverge        = []

    sorted_ws = sorted(results.keys())
    short_w = sorted_ws[0]
    long_w  = sorted_ws[-1]

    for num in range(1, 34):
        all_cold = all(results[w]["red_z"].get(num, 0) < -1.5 for w in sorted_ws)
        all_hot  = all(results[w]["red_z"].get(num, 0) > 1.0  for w in sorted_ws)
        if all_cold:
            red_consensus_cold.append(num)
        elif all_hot:
            red_consensus_hot.append(num)
        else:
            sz = results[short_w]["red_z"].get(num, 0)
            lz = results[long_w]["red_z"].get(num, 0)
            if sz < -1.0 and lz > 0.5:
                red_diverge.append((num, "短冷长热→可能回补"))
            elif sz > 1.0 and lz < -0.5:
                red_diverge.append((num, "短热长冷→趋势退潮"))

    for num in range(1, 17):
        all_cold = all(results[w]["blue_z"].get(num, 0) < -1.5 for w in sorted_ws)
        all_hot  = all(results[w]["blue_z"].get(num, 0) > 1.0  for w in sorted_ws)
        if all_cold:
            blue_consensus_cold.append(num)
        elif all_hot:
            blue_consensus_hot.append(num)
        else:
            sz = results[short_w]["blue_z"].get(num, 0)
            lz = results[long_w]["blue_z"].get(num, 0)
            if sz < -1.0 and lz > 0.5:
                blue_diverge.append((num, "短冷长热→可能回补"))
            elif sz > 1.0 and lz < -0.5:
                blue_diverge.append((num, "短热长冷→趋势退潮"))

    return {
        "windows": results,
        "consensus": {
            "red_cold": red_consensus_cold,
            "red_hot": red_consensus_hot,
            "red_diverge": red_diverge,
            "blue_cold": blue_consensus_cold,
            "blue_hot": blue_consensus_hot,
            "blue_diverge": blue_diverge,
        },
        "primary": results.get(30) or results[sorted_ws[-1]],  # 默认用 30 期作为主分析
    }


def cmd_analyze(_):
    hist = _load_history()
    if not hist:
        print("无本地数据，请先运行: python ssq.py fetch"); sys.exit(1)

    data = hist[:ANALYZE_WINDOW]; stats = _compute_stats(data, full_history=hist)
    multi = _compute_multi_stats(hist)

    print("=" * 58)
    print(f"  [Step 2] 统计分析（最近 {stats['window']} 期）")
    print("=" * 58)
    rs = " ".join(f"{n:02d}" for n in stats["latest_reds"])
    print(f"最新: {stats['latest_period']}  红 {rs}  蓝 {stats['latest_blue']:02d}\n")

    # ── 多窗口概览 ──
    if multi:
        print("── 多窗口分析（10/20/30/50期）────────────────────────")
        for w in sorted(multi["windows"]):
            ws = multi["windows"][w]
            ra = ws["red_anom"][:5]
            ba = ws["blue_anom"][:3]
            ra_str = " ".join(f"{n:02d}" for n in ra) or "无"
            ba_str = " ".join(f"{n:02d}" for n in ba) or "无"
            print(f"  {w:2d}期 | 异常冷红: {ra_str}  异常冷蓝: {ba_str}  和值均值: {ws['sum_mean']}")

        c = multi["consensus"]
        if c["red_cold"]:
            print(f"\n  共识稳定冷红: {' '.join(f'{n:02d}' for n in c['red_cold'])}")
        if c["red_hot"]:
            print(f"  共识稳定热红: {' '.join(f'{n:02d}' for n in c['red_hot'])}")
        if c["red_diverge"]:
            div_str = "  ".join(f"{n:02d}({note})" for n, note in c["red_diverge"])
            print(f"  红球分歧: {div_str}")
        if c["blue_cold"]:
            print(f"  共识稳定冷蓝: {' '.join(f'{n:02d}' for n in c['blue_cold'])}")
        if c["blue_hot"]:
            print(f"  共识稳定热蓝: {' '.join(f'{n:02d}' for n in c['blue_hot'])}")
        print()

    print("── 统计异常沉寂（z-score < -2σ）───────────────────────")
    ra = "  ".join(f"{i:02d}(z={stats['red_z'][i]})" for i in stats["red_anom"]) or "暂无"
    ba = "  ".join(f"{i:02d}(z={stats['blue_z'][i]})" for i in stats["blue_anom"]) or "暂无"
    print(f"  红球: {ra}"); print(f"  蓝球: {ba}")

    print("\n── 遗漏 TOP ─────────────────────────────────────────")
    print(f"  红球: {'  '.join(f'{n:02d}:{m}期' for n,m in stats['red_miss_top5'])}")
    print(f"  蓝球: {'  '.join(f'{n:02d}:{m}期' for n,m in stats['blue_miss_top3'])}")

    print("\n── 冷热（近20期）───────────────────────────────────────")
    print(f"  热红: {' '.join(f'{n:02d}' for n in stats['red_hot'])}")
    print(f"  冷红: {' '.join(f'{n:02d}' for n in stats['red_cold'])}")
    print(f"  热蓝: {' '.join(f'{n:02d}' for n in stats['blue_hot'])}")
    print(f"  冷蓝: {' '.join(f'{n:02d}' for n in stats['blue_cold'])}")

    print("\n── 结构 & 和值 ──────────────────────────────────────")
    print(f"  奇偶TOP3: {'  '.join(f'{r}({c}次)' for r,c in stats['top_odd'])}")
    print(f"  大小TOP3: {'  '.join(f'{r}({c}次)' for r,c in stats['top_size'])}")
    print(f"  和值: 均值={stats['sum_mean']}  σ={stats['sum_std']}  60%区间[{stats['sum_p20_p80'][0]}, {stats['sum_p20_p80'][1]}]")
    print(f"  跨度: 均值={stats['span_mean']}")

    # ── 分位分析 ──
    pos = _position_analysis(hist, window=20)
    if pos:
        print("\n── 分位分析（近20期，每位独立统计）─────────────────────")
        pos_names = ["第1位(龙头)", "第2位", "第3位", "第4位", "第5位", "第6位(凤尾)"]
        for i in range(6):
            p = pos["positions"][i]
            top_str = " ".join(f"{n:02d}({c})" for n, c in p["top_numbers"][:3])
            rec_str = " ".join(f"{n:02d}" for n in p["recommend"])
            print(f"  {pos_names[i]}: 热{top_str} → 推荐 {rec_str}")
        c1 = " ".join(f"{n:02d}" for n in pos["combos"][0])
        c2 = " ".join(f"{n:02d}" for n in pos["combos"][1])
        print(f"  分位组合1: {c1}")
        print(f"  分位组合2: {c2}")

    clean = {k: (sorted(v) if isinstance(v, set) else v) for k, v in stats.items() if not k.startswith("_")}
    out = DATA_DIR / "latest_stats.json"
    out.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[LLM_STATS_JSON_START]")
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    print("[LLM_STATS_JSON_END]")


# ── 3. 推荐引擎 ──────────────────────────────────────

def _structural_score(reds, blue, stats):
    """
    0-10 纯结构分。评估组合是否符合历史分布规律。
    不暗示任何预测准确性。
    """
    sc = 0; det = {}

    # 和值区间 (+3)
    s = sum(reds); lo, hi = stats["sum_p20_p80"]
    if lo <= s <= hi:
        sc += 3; det["和值"] = f"{s} 在60%区间[{lo},{hi}] ✓"
    elif abs(s - stats["sum_mean"]) < stats["sum_std"] * 1.5:
        sc += 1; det["和值"] = f"{s} 接近区间"
    else:
        det["和值"] = f"{s} 偏离区间"

    # 奇偶比 (+2)
    odd = sum(1 for r in reds if r % 2 == 1)
    os_ = f"{odd}奇{6-odd}偶"
    topr = [r for r,_ in stats["top_odd"][:2]]
    if os_ in topr:
        sc += 2; det["奇偶"] = f"{os_} 常见组合 ✓"
    else:
        det["奇偶"] = f"{os_}"

    # 大小比 (+2)
    big = sum(1 for r in reds if r >= 17)
    ss_ = f"{big}大{6-big}小"
    tops = [r for r,_ in stats["top_size"][:2]]
    if ss_ in tops:
        sc += 2; det["大小"] = f"{ss_} 常见组合 ✓"
    else:
        det["大小"] = f"{ss_}"

    # 三区分布 (+2)
    z1 = sum(1 for r in reds if 1  <= r <= 11)
    z2 = sum(1 for r in reds if 12 <= r <= 22)
    z3 = sum(1 for r in reds if 23 <= r <= 33)
    if z1 >= 1 and z2 >= 1 and z3 >= 1:
        sc += 2; det["分区"] = f"{z1}-{z2}-{z3} 各区有覆盖 ✓"
    else:
        det["分区"] = f"{z1}-{z2}-{z3} 有缺区"

    # 跨度 (+1)
    sp = max(reds) - min(reds)
    if abs(sp - stats["span_mean"]) < 8:
        sc += 1; det["跨度"] = f"{sp} 接近均值{stats['span_mean']}"
    else:
        det["跨度"] = f"{sp}"

    return sc, det


def _position_analysis(full_history, window=20):
    """
    分位分析（嘲风方法）：每个位置独立统计。
    近 N 期，每个位置的号码分布、012路、奇偶、合数。
    每个位置推荐 TOP2。
    """
    if not full_history or len(full_history) < window:
        return None

    data = full_history[:window]
    positions = {}  # pos[0..5] -> { numbers: Counter, mod3: Counter, odd/even: Counter, prime: Counter }

    for pos in range(6):
        nums = Counter()
        mod3 = Counter()
        parity = Counter()
        composite = Counter()

        for r in data:
            num = r["red_balls"][pos]
            nums[num] += 1
            mod3[num % 3] += 1
            parity["偶" if num % 2 == 0 else "奇"] += 1
            # 合数判断（2,3,5,7 为质数，其余≥4的非质数为合数）
            is_prime = num in (2, 3, 5, 7) or (num > 7 and all(num % d != 0 for d in range(2, int(num**0.5)+1)))
            composite["合" if is_prime else "质"] += 1

        # 推荐号：出现频率最高的前 2 个 + 最近遗漏最大的前 1 个
        top2 = [n for n, _ in nums.most_common(2)]

        # 每位选 top2
        recommend = list(top2)

        # 第3个推荐：从剩余高频号中取，避开已选
        for n, c in nums.most_common(10):
            if n not in recommend:
                recommend.append(n)
                break

        positions[pos] = {
            "top_numbers": [(n, c) for n, c in nums.most_common(5)],
            "mod3_dist": dict(mod3),
            "parity_dist": dict(parity),
            "composite_dist": dict(composite),
            "recommend": recommend[:3],
            "hot": top2,
        }

    # 组合推荐：每位选 1 个组成 1 注（取每位 hot[0]），再组合生成 2 注
    combo1 = sorted([positions[i]["hot"][0] for i in range(6)])
    # 第 2 注：每位选 hot[1]（如果有的话），否则 fallback 到 hot[0]
    combo2 = sorted([positions[i]["hot"][1] if len(positions[i]["hot"]) > 1 else positions[i]["recommend"][0] for i in range(6)])

    return {
        "window": window,
        "positions": positions,
        "combos": [combo1, combo2],
    }


def _build_feature_profile(stats, multi=None):
    """
    基于多窗口统计构建目标特征画像。
    不是预测，是「什么样的组合结构更符合近期规律」。
    """
    # 从多窗口共识获取偏好
    prefer_cold = set()
    prefer_hot  = set()
    if multi and "consensus" in multi:
        prefer_cold = set(multi["consensus"]["red_cold"][:6])
        prefer_hot  = set(multi["consensus"]["red_hot"][:6])

    # 异常沉寂号（z < -2）
    anom = set(stats["red_anom"])

    # 高遗漏号（按遗漏排序取前10）
    miss_sorted = sorted(stats["_red_miss"].items(), key=lambda x: -x[1])
    high_miss = {n for n, _ in miss_sorted[:10]}

    # 最近一期出现的号（倾向避开）
    last_reds = stats.get("last_reds", set())

    # 目标和值区间
    sum_lo, sum_hi = stats["sum_p20_p80"]
    sum_mean = stats["sum_mean"]

    # 目标奇偶比（取最常见的前2）
    target_odd_ratios = []
    for ratio_str, _ in stats["top_odd"][:2]:
        # "3奇3偶" → 3
        target_odd_ratios.append(int(ratio_str[0]))

    # 目标大小比
    target_big_ratios = []
    for ratio_str, _ in stats["top_size"][:2]:
        target_big_ratios.append(int(ratio_str[0]))

    # 跨度目标
    span_mean = stats["span_mean"]

    return {
        "prefer_cold": prefer_cold,
        "prefer_hot": prefer_hot,
        "anom": anom,
        "high_miss": high_miss,
        "avoid_last": last_reds,
        "sum_range": [sum_lo, sum_hi],
        "sum_mean": sum_mean,
        "target_odd": target_odd_ratios,
        "target_big": target_big_ratios,
        "span_mean": span_mean,
    }


def _score_candidate_by_profile(reds, profile):
    """
    基于特征画像给候选组合打分（0-10）。
    不改变概率，只评估「与画像的匹配度」。
    """
    sc = 0
    s = sum(reds)
    lo, hi = profile["sum_range"]

    # 和值匹配 (+3)
    if lo <= s <= hi:
        sc += 3
    elif abs(s - profile["sum_mean"]) < 20:
        sc += 1

    # 奇偶匹配 (+2)
    odd = sum(1 for r in reds if r % 2 == 1)
    if odd in profile["target_odd"]:
        sc += 2

    # 大小匹配 (+2)
    big = sum(1 for r in reds if r >= 17)
    if big in profile["target_big"]:
        sc += 2

    # 三区覆盖 (+1.5)
    z1 = sum(1 for r in reds if 1  <= r <= 11)
    z2 = sum(1 for r in reds if 12 <= r <= 22)
    z3 = sum(1 for r in reds if 23 <= r <= 33)
    if z1 >= 1 and z2 >= 1 and z3 >= 1:
        sc += 1.5

    # 偏好号命中 (+0.5 each, max +2)
    rset = set(reds)
    prefer = profile["prefer_cold"] | profile["prefer_hot"] | profile["anom"] | profile["high_miss"]
    prefer_hits = len(rset & prefer)
    sc += min(2, prefer_hits * 0.5)

    # 避开最近一期（轻微惩罚，-0.5）
    if rset & profile["avoid_last"]:
        sc -= 0.5

    return round(min(10, max(0, sc)), 1)


def _gen_max_coverage(stats, multi=None, n=5000):
    """
    特征画像定向生成：先构建目标画像，再从各区间抽候选，
    确保每个组合都匹配画像特征，最后贪心选最大覆盖 4 注。
    注间重叠 ≤3。
    """
    profile = _build_feature_profile(stats, multi)

    # 构建加权池
    rm = stats["_red_miss"]; maxr = max(rm.values()) or 1
    anom  = profile["anom"]
    hot_r = set(stats["red_hot"])
    last_r = profile["avoid_last"]

    def red_w(i):
        return max(0.1,
                   1
                   + (rm.get(i, 0) / maxr) * 1.5
                   + (2 if i in anom else 0)
                   + (1 if i in hot_r else 0)
                   + (-0.5 if i in last_r else 0))

    bm = stats["_blue_miss"]; maxb = max(bm.values()) or 1
    banom = set(stats["blue_anom"]); hot_b = set(stats["blue_hot"])
    def blue_w(i):
        return max(0.1,
                   1 + (bm.get(i, 0) / maxb) * 1.5
                   + (2 if i in banom else 0)
                   + (1 if i in hot_b else 0))

    pool_r = list(range(1, 34)); pool_b = list(range(1, 17))
    rw = [red_w(i) for i in pool_r]
    bw = [blue_w(i) for i in pool_b]

    # 生成候选（画像匹配 + 加权采样双过滤）
    candidates = []; seen = set(); att = 0
    while len(candidates) < n and att < n * 5:
        att += 1
        reds = tuple(sorted(random.choices(pool_r, weights=rw, k=6)))
        if len(set(reds)) != 6 or reds in seen:
            continue
        seen.add(reds)
        blue = random.choices(pool_b, weights=bw, k=1)[0]
        sc = _score_candidate_by_profile(list(reds), profile)
        if sc >= 5.0:  # 只保留画像匹配度 ≥5 的
            candidates.append((sc, list(reds), blue))

    # 候选不够时放宽阈值
    if len(candidates) < 20:
        candidates = []
        seen2 = set()
        for _ in range(n * 2):
            reds = tuple(sorted(random.choices(pool_r, weights=rw, k=6)))
            if len(set(reds)) != 6 or reds in seen2:
                continue
            seen2.add(reds)
            blue = random.choices(pool_b, weights=bw, k=1)[0]
            sc = _score_candidate_by_profile(list(reds), profile)
            candidates.append((sc, list(reds), blue))

    # 贪心最大覆盖：注间红球重叠 ≤3
    candidates.sort(key=lambda x: -x[0])
    picks = []
    for item in candidates:
        sc, reds, blue = item
        rset = set(reds)
        overlap_ok = True
        for p in picks:
            if len(rset & set(p[1])) > 3:
                overlap_ok = False; break
        if not overlap_ok:
            continue
        picks.append(item)
        if len(picks) == RECOMMEND_N:
            break

    # 放宽：仍不够则取消重叠限制
    if len(picks) < RECOMMEND_N:
        for item in candidates:
            if item in picks: continue
            picks.append(item)
            if len(picks) == RECOMMEND_N:
                break

    return picks, profile


STRATS = ["覆盖优化A", "覆盖优化B", "覆盖优化C", "覆盖优化D"]


# ── 7. 蓝球独立预测 ──────────────────────────────────

def _predict_blue(stats, multi=None):
    """
    蓝球独立评分：基于遗漏、z-score、多窗口共识，
    输出 Top3 推荐 + 各候选评分。
    """
    bm = stats["_blue_miss"]
    bz = stats["blue_z"]
    banom = set(stats["blue_anom"])
    hot_b = set(stats["blue_hot"])
    cold_b = set(stats["blue_cold"])
    maxb = max(bm.values()) or 1

    # 多窗口共识
    cons_cold = set(); cons_hot = set()
    if multi and "consensus" in multi:
        cons_cold = set(multi["consensus"]["blue_cold"])
        cons_hot  = set(multi["consensus"]["blue_hot"])

    candidates = []
    for num in range(1, 17):
        sc = 0
        # 遗漏占比 (+3)
        miss_ratio = bm.get(num, 0) / maxb
        sc += miss_ratio * 3

        # z-score 沉寂 (+2)
        z_val = bz.get(num, 0)
        if z_val < -2:
            sc += 2
        elif z_val < -1:
            sc += 1

        # 异常沉寂 (+1.5)
        if num in banom:
            sc += 1.5

        # 多窗口共识冷号 (+1.5)
        if num in cons_cold:
            sc += 1.5

        # 近期热号（轻微，+0.5）
        if num in hot_b:
            sc += 0.5

        # 近期冷号（轻微惩罚，-0.3）— 避免一直追冷
        if num in cold_b:
            sc -= 0.3

        # 多窗口共识热号（趋势可能退潮，-0.5）
        if num in cons_hot:
            sc -= 0.5

        candidates.append((round(sc, 2), num))

    candidates.sort(key=lambda x: -x[0])
    return candidates[:3], candidates


def cmd_recommend(_):
    hist = _load_history()
    if not hist:
        print("无本地数据，请先运行: python ssq.py fetch"); sys.exit(1)

    data = hist[:ANALYZE_WINDOW]; stats = _compute_stats(data, full_history=hist)
    multi = _compute_multi_stats(hist)
    picks, profile = _gen_max_coverage(stats, multi=multi)
    if not picks:
        print("候选生成失败，请重试"); sys.exit(1)

    # 蓝球独立预测
    blue_top3, blue_all = _predict_blue(stats, multi=multi)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print("  [Step 3] 本期推荐（特征画像 + 最大覆盖策略）")
    print("=" * 60)
    print(f"  基于最近 {ANALYZE_WINDOW} 期 | {now}")
    print(f"  [!] 头奖概率固定: 1/{TOTAL_COMBOS:,}，评分仅为结构合理性\n")

    # ── 特征画像概览 ──
    print("  ── 特征画像 ─────────────────────────────────────────")
    print(f"  目标和值区间: [{profile['sum_range'][0]}, {profile['sum_range'][1]}] (均值{profile['sum_mean']})")
    print(f"  目标奇偶比: {profile['target_odd']}  目标大小比: {profile['target_big']}")
    print(f"  偏好号(冷/异常): {' '.join(f'{n:02d}' for n in sorted(profile['prefer_cold'] | profile['anom']))}")
    print(f"  偏好号(热): {' '.join(f'{n:02d}' for n in sorted(profile['prefer_hot']))}")
    print(f"  避开近期: {' '.join(f'{n:02d}' for n in sorted(profile['avoid_last']))}")
    print()

    to_save = []
    all_reds_covered = set()
    for idx, (sc, reds, blue) in enumerate(picks[:RECOMMEND_N]):
        strat = STRATS[idx] if idx < len(STRATS) else f"采样{idx+1}"
        rs    = " ".join(f"{r:02d}" for r in sorted(reds))
        s     = sum(reds); sp = max(reds) - min(reds)
        odd   = sum(1 for r in reds if r % 2 == 1)
        big   = sum(1 for r in reds if r >= 17)
        all_reds_covered |= set(reds)

        print(f"【第{idx+1}注】{strat}")
        print(f"  红球: {rs}   蓝球: {blue:02d}")
        print(f"  画像匹配分: {sc}/10")
        print(f"  特征: 和值={s}  跨度={sp}  奇偶={odd}:{6-odd}  大小={big}:{6-big}\n")
        to_save.append({"idx": idx+1, "strategy": strat, "reds": sorted(reds), "blue": blue, "score": sc})

    print(f"  覆盖统计: 4注共覆盖 {len(all_reds_covered)} 个不同红球 ({len(all_reds_covered)}/33)")
    print(f"  覆盖率: {len(all_reds_covered)/33*100:.0f}%\n")

    # ── 蓝球独立推荐 ──
    print("  ── 蓝球推荐 ─────────────────────────────────────────")
    for rank, (sc, num) in enumerate(blue_top3, 1):
        print(f"  TOP{rank}: {num:02d}  评分 {sc}")
    print()

    # ── 分位推荐（嘲风方法）──
    pos = _position_analysis(hist, window=20)
    if pos:
        print("  ── 分位推荐（近20期每位独立统计）──────────────────")
        pos_names = ["第1位(龙头)", "第2位", "第3位", "第4位", "第5位", "第6位(凤尾)"]
        for i in range(6):
            p = pos["positions"][i]
            rec_str = " ".join(f"{n:02d}" for n in p["recommend"])
            hot_str = " ".join(f"{n:02d}" for n in p["hot"])
            print(f"  {pos_names[i]}: 热号{hot_str} → 推荐 {rec_str}")
        for ci, combo in enumerate(pos["combos"], 1):
            cs = " ".join(f"{n:02d}" for n in combo)
            print(f"  分位组合{ci}: {cs}")
        print()

    arch = _load_archive()
    arch.append({"timestamp": now, "based_on": stats["latest_period"],
                 "window": ANALYZE_WINDOW, "predictions": to_save,
                 "blue_predictions": [{"rank": i+1, "num": n, "score": s} for i, (s, n) in enumerate(blue_top3)],
                 "actual": None, "review": None})
    _save_archive(arch)
    print(f"  预测存档: {ARCHIVE_FILE}")

    # 历史命中统计
    all_hits = [r["hit_reds"] for e in arch if e.get("review") for r in e["review"]]
    if all_hits:
        total = len(all_hits); mx = max(all_hits); avg = statistics.mean(all_hits)
        print(f"  历史: {total} 次预测  红球最高 {mx}/6  均值 {avg:.2f}/6")

    out = {
        "based_on": stats["latest_period"], "window": ANALYZE_WINDOW, "timestamp": now,
        "picks": [{
            "rank": i+1, "strategy": STRATS[i] if i < len(STRATS) else f"采样{i+1}",
            "red_balls": sorted(p[1]), "blue_ball": p[2], "score": p[0],
            "features": {
                "sum": sum(p[1]), "span": max(p[1]) - min(p[1]),
                "odd_even": f"{sum(x%2 for x in p[1])}:{6-sum(x%2 for x in p[1])}",
                "big_small": f"{sum(1 for x in p[1] if x>=17)}:{sum(1 for x in p[1] if x<17)}"
            }
        } for i, p in enumerate(picks[:RECOMMEND_N])],
        "blue_top3": [{"rank": i+1, "num": n, "score": s} for i, (s, n) in enumerate(blue_top3)],
        "coverage": {"unique_reds": len(all_reds_covered), "pct": round(len(all_reds_covered) / 33 * 100, 1)},
        "profile": profile,
    }
    print("\n[LLM_RECOMMEND_JSON_START]")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=list))
    print("[LLM_RECOMMEND_JSON_END]")


# ── 4. 复盘 ───────────────────────────────────────────

def _prize(hr, hb):
    if hr == 6 and hb: return "一等奖"
    if hr == 6:        return "二等奖"
    if hr == 5 and hb: return "三等奖"
    if hr == 5 or (hr == 4 and hb): return "四等奖"
    if hr == 4 or (hr == 3 and hb): return "五等奖"
    if hb:             return "六等奖"
    return "未中奖"


def cmd_review(args):
    if len(args.nums) < 8:
        print("用法: python ssq.py review <期号> <红1> <红2> <红3> <红4> <红5> <红6> <蓝>")
        sys.exit(1)
    period   = args.nums[0]
    act_reds = sorted(int(x) for x in args.nums[1:7])
    act_blue = int(args.nums[7])
    arch     = _load_archive()
    if not arch:
        print("无预测记录，先运行 recommend"); sys.exit(1)
    last = arch[-1]

    print("=" * 60)
    print(f"  [Step 4] 复盘 — {period} 期")
    print("=" * 60)
    rs = " ".join(f"{n:02d}" for n in act_reds)
    print(f"开奖: 红 {rs}  蓝 {act_blue:02d}\n")

    results = []
    for p in last["predictions"]:
        hr = len(set(p["reds"]) & set(act_reds))
        hb = (p["blue"] == act_blue)
        pz = _prize(hr, hb)
        rs2 = " ".join(f"{n:02d}" for n in p["reds"])
        print(f"  #{p['idx']} ({p['strategy']}) 画像分{p['score']}")
        print(f"    红 {rs2}  蓝 {p['blue']:02d} → 红{hr}/6 蓝{'中' if hb else '×'} {pz}\n")
        results.append({"idx": p["idx"], "hit_reds": hr, "hit_blue": hb, "prize": pz})

    # 蓝球复盘
    if last.get("blue_predictions"):
        print("  ── 蓝球复盘 ──")
        for bp in last["blue_predictions"]:
            hit = "✓" if bp["num"] == act_blue else "×"
            print(f"    TOP{bp['rank']} {bp['num']:02d} → {hit}")
        print()

    last["actual"] = {"period": period, "reds": act_reds, "blue": act_blue}
    last["review"] = results
    _save_archive(arch)

    # ── 累计统计 ──
    all_hits = [r["hit_reds"] for e in arch if e.get("review") for r in e["review"]]
    if all_hits:
        total = len(all_hits); mx = max(all_hits); avg = statistics.mean(all_hits)
        print(f"累计: {total} 次预测  红球最高 {mx}/6  均值 {avg:.2f}/6")
        prizes = Counter(r["prize"] for e in arch if e.get("review") for r in e["review"])
        print(f"中奖记录: {dict(prizes)}")

    # ── 随机基准对比 ──
    # 随机 4 注的期望红球命中数 ≈ 4 × 6×6/33 ≈ 4.36/6（每注期望 1.09 个红球）
    # 实际均值 vs 随机期望
    random_expect_per_bet = 6 * 6 / 33  # ≈ 1.09
    random_expect_total = 4 * random_expect_per_bet
    if all_hits:
        actual_avg = statistics.mean(all_hits)
        diff = actual_avg - random_expect_per_bet
        print(f"\n── 随机基准对比 ──")
        print(f"  随机期望: 每注 {random_expect_per_bet:.2f}/6 红球  |  4注合计 {random_expect_total:.2f}/6")
        print(f"  实际均值: 每注 {actual_avg:.2f}/6 红球")
        if diff > 0.05:
            print(f"  偏差: +{diff:.2f}（略高于随机，结构筛选有微弱正向信号）")
        elif diff < -0.05:
            print(f"  偏差: {diff:.2f}（略低于随机，说明结构筛选未命中）")
        else:
            print(f"  偏差: {diff:.2f}（与随机基本持平）")
        print(f"  [!] 样本量小，偏差不具统计显著性")


# ── 5. 本地 I/O ──────────────────────────────────────

def _load_history():
    if HIST_FILE.exists():
        try: return json.loads(HIST_FILE.read_text(encoding="utf-8"))
        except: pass
    return []

def _save_history(r):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HIST_FILE.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

def _load_archive():
    if ARCHIVE_FILE.exists():
        try: return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        except: pass
    return []

def _save_archive(d):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 6. 入口 ──────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="双色球分析工具 v6.1")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("fetch"); sub.add_parser("analyze")
    sub.add_parser("recommend"); sub.add_parser("all")
    rv = sub.add_parser("review"); rv.add_argument("nums", nargs="+")
    args = p.parse_args()

    if   args.cmd == "fetch":     cmd_fetch(args)
    elif args.cmd == "analyze":   cmd_analyze(args)
    elif args.cmd == "recommend": cmd_recommend(args)
    elif args.cmd == "all":
        cmd_fetch(args); print(); cmd_analyze(args); print(); cmd_recommend(args)
    elif args.cmd == "review":    cmd_review(args)
    else: p.print_help()

if __name__ == "__main__":
    main()
