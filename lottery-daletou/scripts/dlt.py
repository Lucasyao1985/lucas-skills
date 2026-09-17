#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大乐透分析工具 v2.0
用法:
  python dlt.py fetch      # 联网抓取最新数据 + 自动复盘
  python dlt.py analyze    # 分析最近30期，输出JSON
  python dlt.py recommend  # 生成4注推荐+结构分
  python dlt.py all        # 一键全流程
  python dlt.py review <期号> <前1> <前2> <前3> <前4> <前5> <后1> <后2>

依赖: pip install requests beautifulsoup4
数据存储: ~/.dlt_data/

大乐透规则:
  - 前区: 01-35 选 5
  - 后区: 01-12 选 2
  - 开奖时间: 周一、三、六 21:10
  - 九个奖级: 一等奖(5+2) 到 九等奖(3+0/1+2/0+2)
  - 头奖概率: 21,425,712
"""

import sys, os, json, math, random, statistics, argparse
from datetime import datetime
from collections import Counter
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"缺少依赖: {e}\n请运行: pip install requests beautifulsoup4")
    sys.exit(1)

# ── 常量 ──────────────────────────────────────────────

FRONT_MIN, FRONT_MAX = 1, 35   # 前区号码范围
FRONT_PICK = 5                  # 前区选几个
BACK_MIN, BACK_MAX = 1, 12     # 后区号码范围
BACK_PICK = 2                   # 后区选几个

TOTAL_COMBOS = math.comb(35, 5) * math.comb(12, 2)  # 21,425,712
ANALYZE_WINDOW = 30
RECOMMEND_N = 4

DATA_DIR     = Path.home() / ".dlt_data"
HIST_FILE    = DATA_DIR / "history.json"
STATS_FILE   = DATA_DIR / "latest_stats.json"
ARCHIVE_FILE = DATA_DIR / "predictions.json"

NO_PROXY = {"http": "", "https": ""}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://static.sporttery.cn/",
}


# ── 奖级 ──────────────────────────────────────────────

def _prize(hit_front, hit_back):
    """大乐透奖级判定"""
    if hit_front == 5 and hit_back == 2: return "一等奖"
    if hit_front == 5 and hit_back == 1: return "二等奖"
    if hit_front == 5 and hit_back == 0: return "三等奖"
    if hit_front == 4 and hit_back == 2: return "四等奖"
    if hit_front == 4 and hit_back == 1: return "五等奖"
    if hit_front == 3 and hit_back == 2: return "六等奖"
    if hit_front == 4 and hit_back == 0: return "七等奖"
    if (hit_front == 3 and hit_back == 1) or (hit_front == 2 and hit_back == 2): return "八等奖"
    if (hit_front == 3 and hit_back == 0) or (hit_front == 1 and hit_back == 2) or (hit_front == 0 and hit_back == 2): return "九等奖"
    return "未中奖"


# ── 数据加载/保存 ──────────────────────────────────────

def _load_history():
    if HIST_FILE.exists():
        return json.loads(HIST_FILE.read_text(encoding="utf-8"))
    return []

def _save_history(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HIST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _load_archive():
    if ARCHIVE_FILE.exists():
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    return []

def _save_archive(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 1. 数据抓取 ──────────────────────────────────────

def fetch_from_sporttery(timeout=20):
    """从体彩官网 API 抓取（备用源）"""
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    params = {
        "gameNo": "85",       # 85 = 大乐透
        "provinceId": "0",
        "pageSize": "100",
        "isVerify": "1",
        "pageNo": "1",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS,
                           timeout=timeout, proxies=NO_PROXY)
        data = resp.json()
        if data.get("errorCode") != "0":
            raise Exception(data.get("errorMsg", "API 返回异常"))

        records = []
        for item in data.get("value", {}).get("list", []):
            period = item.get("lotteryDrawNum", "")
            result_str = item.get("lotteryDrawResult", "")
            nums = [int(x) for x in result_str.split() if x.isdigit()]
            if len(nums) == 7:
                records.append({
                    "period": period,
                    "front": sorted(nums[:5]),
                    "back": sorted(nums[5:]),
                })
        return records
    except Exception as e:
        print(f"  sporttery.cn 抓取失败: {e}")
        return []


def cmd_fetch(_):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 58)
    print("  [Step 1] 联网抓取")
    print("=" * 58)

    # ── 唯一官方源：体彩API（gameNo=85 硬编码，不可外部修改）──
    records = fetch_from_sporttery(100)
    if not records:
        print("FETCH_FAILED:网络请求失败或 API 返回异常")
        return
    print(f"  sporttery.cn: 获取 {len(records)} 期")

    existing  = _load_history()
    exist_set = {r["period"] for r in existing}
    new_n     = 0
    for r in records:
        if r["period"] not in exist_set:
            existing.append(r)
            new_n += 1
    existing.sort(key=lambda x: x["period"], reverse=True)
    _save_history(existing)

    lat = existing[0]
    fs = " ".join(f"{n:02d}" for n in lat["front"])
    bs = " ".join(f"{n:02d}" for n in lat["back"])
    print(f"新增 {new_n} 期，本地共 {len(existing)} 期")
    print(f"最新: {lat['period']}  前区 {fs}  后区 {bs}")

    # ── 验证闭环 ──
    api_latest = records[0]["period"] if records else None
    local_latest = lat["period"]
    if api_latest and api_latest == local_latest:
        print(f"FETCH_OK:{local_latest}")
    elif api_latest and api_latest > local_latest:
        print(f"UPDATE_FAILED:本地 {local_latest} 仍落后于 API {api_latest}")
    else:
        print(f"FETCH_OK:{local_latest}")


    # 自动复盘
    if new_n > 0 and len(existing) > 1:
        _auto_review(lat)


def _auto_review(latest_draw):
    """抓取到新数据后，自动用最新开奖号复盘上期预测"""
    arch = _load_archive()
    if not arch:
        return

    period = latest_draw["period"]
    act_front = latest_draw["front"]
    act_back = latest_draw["back"]

    # 找最近一条未复盘的预测
    target = None
    for entry in reversed(arch):
        if entry.get("review") is None and entry.get("actual") is None:
            target = entry
            break
    if not target:
        return

    print(f"\n── 自动复盘 {period} 期 ──────────────────────────────────")
    fs = " ".join(f"{n:02d}" for n in act_front)
    bs = " ".join(f"{n:02d}" for n in act_back)
    print(f"开奖: 前区 {fs}  后区 {bs}")

    results = []
    for p in target["predictions"]:
        hf = len(set(p["front"]) & set(act_front))
        hb = len(set(p["back"]) & set(act_back))
        pz = _prize(hf, hb)
        fs2 = " ".join(f"{n:02d}" for n in sorted(p["front"]))
        bs2 = " ".join(f"{n:02d}" for n in sorted(p["back"]))
        print(f"  #{p['idx']} 前{fs2} 后{bs2} → 前{hf}/5 后{hb}/2 {pz}")
        results.append({"idx": p["idx"], "hit_front": hf, "hit_back": hb, "prize": pz})

    target["actual"] = {"period": period, "front": act_front, "back": act_back}
    target["review"] = results
    _save_archive(arch)


# ── 2. 统计分析 ──────────────────────────────────────

def _compute_stats(data, full_history=None):
    """单窗口统计分析（前后区分离）"""
    n = len(data)

    # ── 前区统计 ──
    front_freq = Counter()
    for r in data:
        front_freq.update(r["front"])
    front_exp = n * FRONT_PICK / (FRONT_MAX - FRONT_MIN + 1)  # n * 5 / 35
    front_std = math.sqrt(front_exp * (1 - FRONT_PICK / (FRONT_MAX - FRONT_MIN + 1))) or 1

    def z(actual, exp, std):
        return round((actual - exp) / std, 2)

    front_z = {i: z(front_freq.get(i, 0), front_exp, front_std)
               for i in range(FRONT_MIN, FRONT_MAX + 1)}
    front_anom = sorted([i for i, s in front_z.items() if s < -2.0],
                        key=lambda x: front_z[x])

    # ── 后区统计 ──
    back_freq = Counter()
    for r in data:
        back_freq.update(r["back"])
    back_exp = n * BACK_PICK / (BACK_MAX - BACK_MIN + 1)  # n * 2 / 12
    back_std = math.sqrt(back_exp * (1 - BACK_PICK / (BACK_MAX - BACK_MIN + 1))) or 1

    back_z = {i: z(back_freq.get(i, 0), back_exp, back_std)
              for i in range(BACK_MIN, BACK_MAX + 1)}
    back_anom = sorted([i for i, s in back_z.items() if s < -2.0],
                       key=lambda x: back_z[x])

    # ── 遗漏值 ──
    front_miss = {i: 0 for i in range(FRONT_MIN, FRONT_MAX + 1)}
    back_miss = {i: 0 for i in range(BACK_MIN, BACK_MAX + 1)}
    for r in data:
        for i in range(FRONT_MIN, FRONT_MAX + 1):
            if i not in r["front"]:
                front_miss[i] += 1
        for i in range(BACK_MIN, BACK_MAX + 1):
            if i not in r["back"]:
                back_miss[i] += 1

    # ── 冷热号（近20期）──
    hw = min(20, n)
    front_rc = Counter()
    back_bc = Counter()
    for r in data[:hw]:
        front_rc.update(r["front"])
        back_bc.update(r["back"])

    avg_front = hw * FRONT_PICK / (FRONT_MAX - FRONT_MIN + 1)  # hw * 5 / 35
    avg_back = hw * BACK_PICK / (BACK_MAX - BACK_MIN + 1)      # hw * 2 / 12

    front_hot = sorted([i for i in range(FRONT_MIN, FRONT_MAX + 1)
                        if front_rc.get(i, 0) > avg_front],
                       key=lambda x: -front_rc.get(x, 0))
    front_cold = sorted([i for i in range(FRONT_MIN, FRONT_MAX + 1)
                         if front_rc.get(i, 0) < avg_front * 0.5],
                        key=lambda x: front_rc.get(x, 0))
    back_hot = sorted([i for i in range(BACK_MIN, BACK_MAX + 1)
                       if back_bc.get(i, 0) > avg_back],
                      key=lambda x: -back_bc.get(x, 0))
    back_cold = sorted([i for i in range(BACK_MIN, BACK_MAX + 1)
                        if back_bc.get(i, 0) < avg_back * 0.5],
                       key=lambda x: back_bc.get(x, 0))

    # ── 结构指标 ──
    odd_c = Counter()
    siz_c = Counter()
    sums = []
    spans = []
    for r in data:
        fb = r["front"]
        odd = sum(x % 2 for x in fb)
        big = sum(1 for x in fb if x >= 18)
        odd_c[f"{odd}奇{FRONT_PICK - odd}偶"] += 1
        siz_c[f"{big}大{FRONT_PICK - big}小"] += 1
        sums.append(sum(fb))
        spans.append(max(fb) - min(fb))

    ssorted = sorted(sums)
    p20 = ssorted[max(0, int(n * 0.20))]
    p80 = ssorted[min(n - 1, int(n * 0.80))]

    # ── 全历史最大遗漏 ──
    src = full_history if full_history else data
    front_max_miss = {i: 0 for i in range(FRONT_MIN, FRONT_MAX + 1)}
    back_max_miss = {i: 0 for i in range(BACK_MIN, BACK_MAX + 1)}
    front_last = {i: None for i in range(FRONT_MIN, FRONT_MAX + 1)}
    back_last = {i: None for i in range(BACK_MIN, BACK_MAX + 1)}

    for idx, r in enumerate(reversed(src)):
        for i in range(FRONT_MIN, FRONT_MAX + 1):
            if i in r["front"]:
                if front_last[i] is not None:
                    gap = idx - front_last[i] - 1
                    front_max_miss[i] = max(front_max_miss[i], gap)
                front_last[i] = idx
        for i in range(BACK_MIN, BACK_MAX + 1):
            if i in r["back"]:
                if back_last[i] is not None:
                    gap = idx - back_last[i] - 1
                    back_max_miss[i] = max(back_max_miss[i], gap)
                back_last[i] = idx

    total = len(src)
    for i in range(FRONT_MIN, FRONT_MAX + 1):
        if front_last[i] is None:
            front_max_miss[i] = total
    for i in range(BACK_MIN, BACK_MAX + 1):
        if back_last[i] is None:
            back_max_miss[i] = total

    return {
        "window": n,
        "latest_period": data[0]["period"],
        "latest_front": data[0]["front"],
        "latest_back": data[0]["back"],
        "front_anom": front_anom,
        "back_anom": back_anom,
        "front_z": front_z,
        "back_z": back_z,
        "front_miss_top5": sorted(front_miss.items(), key=lambda x: -x[1])[:5],
        "back_miss_top3": sorted(back_miss.items(), key=lambda x: -x[1])[:3],
        "front_hot": front_hot[:8],
        "front_cold": front_cold[:8],
        "back_hot": back_hot[:5],
        "back_cold": back_cold[:5],
        "top_odd": odd_c.most_common(3),
        "top_size": siz_c.most_common(3),
        "sum_mean": round(statistics.mean(sums), 1),
        "sum_std": round(statistics.stdev(sums) if n > 1 else 0, 1),
        "sum_p20_p80": [p20, p80],
        "span_mean": round(statistics.mean(spans), 1),
        "last_front": set(data[0]["front"]),
        "_front_miss": front_miss,
        "_back_miss": back_miss,
        "_front_max_miss": front_max_miss,
        "_back_max_miss": back_max_miss,
    }


def _compute_multi_stats(full_history, windows=(10, 20, 30, 50)):
    """多窗口并行统计"""
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

    # 共识分析
    sorted_ws = sorted(results.keys())
    front_consensus_cold = []
    front_consensus_hot = []
    front_diverge = []
    back_consensus_cold = []
    back_consensus_hot = []
    back_diverge = []

    short_w = sorted_ws[0]
    long_w = sorted_ws[-1]

    for num in range(FRONT_MIN, FRONT_MAX + 1):
        all_cold = all(results[w]["front_z"].get(num, 0) < -1.5 for w in sorted_ws)
        all_hot = all(results[w]["front_z"].get(num, 0) > 1.0 for w in sorted_ws)
        if all_cold:
            front_consensus_cold.append(num)
        elif all_hot:
            front_consensus_hot.append(num)
        else:
            sz = results[short_w]["front_z"].get(num, 0)
            lz = results[long_w]["front_z"].get(num, 0)
            if sz < -1.0 and lz > 0.5:
                front_diverge.append((num, "短冷长热→可能回补"))
            elif sz > 1.0 and lz < -0.5:
                front_diverge.append((num, "短热长冷→趋势退潮"))

    for num in range(BACK_MIN, BACK_MAX + 1):
        all_cold = all(results[w]["back_z"].get(num, 0) < -1.5 for w in sorted_ws)
        all_hot = all(results[w]["back_z"].get(num, 0) > 1.0 for w in sorted_ws)
        if all_cold:
            back_consensus_cold.append(num)
        elif all_hot:
            back_consensus_hot.append(num)
        else:
            sz = results[short_w]["back_z"].get(num, 0)
            lz = results[long_w]["back_z"].get(num, 0)
            if sz < -1.0 and lz > 0.5:
                back_diverge.append((num, "短冷长热→可能回补"))
            elif sz > 1.0 and lz < -0.5:
                back_diverge.append((num, "短热长冷→趋势退潮"))

    return {
        "windows": results,
        "consensus": {
            "front_cold": front_consensus_cold,
            "front_hot": front_consensus_hot,
            "front_diverge": front_diverge,
            "back_cold": back_consensus_cold,
            "back_hot": back_consensus_hot,
            "back_diverge": back_diverge,
        },
        "primary": results.get(30) or results[sorted_ws[-1]],
    }


def cmd_analyze(_):
    hist = _load_history()
    if not hist:
        print("无本地数据，请先运行: python dlt.py fetch")
        sys.exit(1)

    data = hist[:ANALYZE_WINDOW]
    stats = _compute_stats(data, full_history=hist)
    multi = _compute_multi_stats(hist)

    print("=" * 58)
    print(f"  [Step 2] 统计分析（最近 {stats['window']} 期）")
    print("=" * 58)
    fs = " ".join(f"{n:02d}" for n in stats["latest_front"])
    bs = " ".join(f"{n:02d}" for n in stats["latest_back"])
    print(f"最新: {stats['latest_period']}  前区 {fs}  后区 {bs}\n")

    # 多窗口概览
    if multi:
        print("── 多窗口分析（10/20/30/50期）────────────────────────")
        for w in sorted(multi["windows"]):
            ws = multi["windows"][w]
            fa = ws["front_anom"][:5]
            ba = ws["back_anom"][:3]
            fa_str = " ".join(f"{n:02d}" for n in fa) or "无"
            ba_str = " ".join(f"{n:02d}" for n in ba) or "无"
            print(f"  {w:2d}期 | 异常冷前: {fa_str}  异常冷后: {ba_str}  和值均值: {ws['sum_mean']}")

        c = multi["consensus"]
        if c["front_cold"]:
            print(f"\n  共识稳定冷前: {' '.join(f'{n:02d}' for n in c['front_cold'])}")
        if c["front_hot"]:
            print(f"  共识稳定热前: {' '.join(f'{n:02d}' for n in c['front_hot'])}")
        if c["front_diverge"]:
            div_str = "  ".join(f"{n:02d}({note})" for n, note in c["front_diverge"])
            print(f"  前区分歧: {div_str}")
        if c["back_cold"]:
            print(f"  共识稳定冷后: {' '.join(f'{n:02d}' for n in c['back_cold'])}")
        if c["back_hot"]:
            print(f"  共识稳定热后: {' '.join(f'{n:02d}' for n in c['back_hot'])}")
        print()

    print("── 统计异常沉寂（z-score < -2σ）───────────────────────")
    fa = "  ".join(f"{i:02d}(z={stats['front_z'][i]})" for i in stats["front_anom"]) or "暂无"
    ba = "  ".join(f"{i:02d}(z={stats['back_z'][i]})" for i in stats["back_anom"]) or "暂无"
    print(f"  前区: {fa}")
    print(f"  后区: {ba}")

    print("\n── 遗漏 TOP ─────────────────────────────────────────")
    print(f"  前区: {'  '.join(f'{n:02d}:{m}期' for n, m in stats['front_miss_top5'])}")
    print(f"  后区: {'  '.join(f'{n:02d}:{m}期' for n, m in stats['back_miss_top3'])}")

    print("\n── 冷热（近20期）───────────────────────────────────────")
    print(f"  热前: {' '.join(f'{n:02d}' for n in stats['front_hot'])}")
    print(f"  冷前: {' '.join(f'{n:02d}' for n in stats['front_cold'])}")
    print(f"  热后: {' '.join(f'{n:02d}' for n in stats['back_hot'])}")
    print(f"  冷后: {' '.join(f'{n:02d}' for n in stats['back_cold'])}")

    print("\n── 结构 & 和值 ──────────────────────────────────────")
    print(f"  奇偶TOP3: {'  '.join(f'{r}({c}次)' for r, c in stats['top_odd'])}")
    print(f"  大小TOP3: {'  '.join(f'{r}({c}次)' for r, c in stats['top_size'])}")
    print(f"  和值: 均值={stats['sum_mean']}  σ={stats['sum_std']}  60%区间[{stats['sum_p20_p80'][0]}, {stats['sum_p20_p80'][1]}]")
    print(f"  跨度: 均值={stats['span_mean']}")

    # 分位分析
    pos = _position_analysis(hist, window=20)
    if pos:
        print("\n── 分位分析（近20期，每位独立统计）─────────────────────")
        pos_names = ["第1位(龙头)", "第2位", "第3位", "第4位", "第5位(凤尾)"]
        for i in range(FRONT_PICK):
            p = pos["positions"][i]
            top_str = " ".join(f"{n:02d}({c})" for n, c in p["top_numbers"][:3])
            rec_str = " ".join(f"{n:02d}" for n in p["recommend"])
            print(f"  {pos_names[i]}: 热{top_str} → 推荐 {rec_str}")
        c1 = " ".join(f"{n:02d}" for n in pos["combos"][0])
        c2 = " ".join(f"{n:02d}" for n in pos["combos"][1])
        print(f"  分位组合1: {c1}")
        print(f"  分位组合2: {c2}")

    clean = {k: (sorted(v) if isinstance(v, set) else v)
             for k, v in stats.items() if not k.startswith("_")}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[LLM_STATS_JSON_START]")
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    print("[LLM_STATS_JSON_END]")


# ── 3. 推荐引擎 ──────────────────────────────────────

STRATS = ["覆盖优化A", "覆盖优化B", "覆盖优化C", "覆盖优化D"]


def _structural_score(reds, stats):
    """
    0-10 纯结构分。评估大乐透前区组合是否符合历史分布规律。
    不暗示任何预测准确性。
    """
    sc = 0; det = {}

    # 和值区间 (+3)
    s = sum(reds); lo, hi = stats["sum_p20_p80"]
    if lo <= s <= hi:
        sc += 3; det["和值"] = f"{s} 在60%区间[{lo},{hi}]"
    elif abs(s - stats["sum_mean"]) < stats["sum_std"] * 1.5:
        sc += 1; det["和值"] = f"{s} 接近区间"
    else:
        det["和值"] = f"{s} 偏离区间"

    # 奇偶比 (+2)
    odd = sum(1 for r in reds if r % 2 == 1)
    os_ = f"{odd}奇{FRONT_PICK - odd}偶"
    topr = [r for r, _ in stats["top_odd"][:2]]
    if os_ in topr:
        sc += 2; det["奇偶"] = f"{os_} 常见"
    else:
        det["奇偶"] = f"{os_}"

    # 大小比 (mid=18) (+2)
    big = sum(1 for r in reds if r >= 18)
    ss_ = f"{big}大{FRONT_PICK - big}小"
    tops = [r for r, _ in stats["top_size"][:2]]
    if ss_ in tops:
        sc += 2; det["大小"] = f"{ss_} 常见"
    else:
        det["大小"] = f"{ss_}"

    # 三区覆盖 (+2): 1-11 / 12-23 / 24-35
    z1 = sum(1 for r in reds if 1 <= r <= 11)
    z2 = sum(1 for r in reds if 12 <= r <= 23)
    z3 = sum(1 for r in reds if 24 <= r <= 35)
    if z1 >= 1 and z2 >= 1 and z3 >= 1:
        sc += 2; det["分区"] = f"{z1}-{z2}-{z3} 全覆盖"
    elif z1 >= 1 and z3 >= 1:
        sc += 1; det["分区"] = f"{z1}-{z2}-{z3}"
    else:
        det["分区"] = f"{z1}-{z2}-{z3} 缺区"

    # 跨度 (+1)
    sp = max(reds) - min(reds)
    if abs(sp - stats["span_mean"]) < 8:
        sc += 1; det["跨度"] = f"{sp} 接近均值{stats['span_mean']}"
    else:
        det["跨度"] = f"{sp}"

    return sc, det


def _position_analysis(full_history, window=20):
    """
    分位分析：大乐透前区 5 个位置独立统计。
    近 N 期，每个位置的号码分布、频率。
    每位推荐 TOP3。
    """
    if not full_history or len(full_history) < window:
        return None

    data = full_history[:window]
    positions = {}

    for pos in range(FRONT_PICK):
        nums = Counter()
        for r in data:
            num = r["front"][pos]
            nums[num] += 1

        top3 = [n for n, _ in nums.most_common(3)]
        recommend = list(top3)

        # 第3个推荐从剩余高频号中取
        if len(recommend) < 3:
            for n, c in nums.most_common(10):
                if n not in recommend:
                    recommend.append(n)
                    if len(recommend) >= 3:
                        break

        positions[pos] = {
            "top_numbers": [(n, c) for n, c in nums.most_common(5)],
            "recommend": recommend[:3],
            "hot": [n for n, _ in nums.most_common(2)],
        }

    # 组合推荐：每位取 hot[0] 组成 1 注，hot[1] 组成第 2 注
    combo1 = sorted([positions[i]["hot"][0] for i in range(FRONT_PICK)])
    combo2 = sorted([
        positions[i]["hot"][1] if len(positions[i]["hot"]) > 1 else positions[i]["recommend"][0]
        for i in range(FRONT_PICK)
    ])

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
    prefer_cold = set()
    prefer_hot = set()
    if multi and "consensus" in multi:
        prefer_cold = set(multi["consensus"]["front_cold"][:6])
        prefer_hot = set(multi["consensus"]["front_hot"][:6])

    anom = set(stats["front_anom"])

    miss_sorted = sorted(stats["_front_miss"].items(), key=lambda x: -x[1])
    high_miss = {n for n, _ in miss_sorted[:10]}

    last_fronts = stats.get("last_front", set())

    sum_lo, sum_hi = stats["sum_p20_p80"]
    sum_mean = stats["sum_mean"]

    target_odd_ratios = []
    for ratio_str, _ in stats["top_odd"][:2]:
        target_odd_ratios.append(int(ratio_str[0]))

    target_big_ratios = []
    for ratio_str, _ in stats["top_size"][:2]:
        target_big_ratios.append(int(ratio_str[0]))

    span_mean = stats["span_mean"]

    return {
        "prefer_cold": prefer_cold,
        "prefer_hot": prefer_hot,
        "anom": anom,
        "high_miss": high_miss,
        "avoid_last": last_fronts,
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
    big = sum(1 for r in reds if r >= 18)
    if big in profile["target_big"]:
        sc += 2

    # 三区覆盖 (+1.5)
    z1 = sum(1 for r in reds if 1 <= r <= 11)
    z2 = sum(1 for r in reds if 12 <= r <= 23)
    z3 = sum(1 for r in reds if 24 <= r <= 35)
    if z1 >= 1 and z2 >= 1 and z3 >= 1:
        sc += 1.5

    # 偏好号命中 (+0.5 each, max +2)
    rset = set(reds)
    prefer = profile["prefer_cold"] | profile["prefer_hot"] | profile["anom"] | profile["high_miss"]
    prefer_hits = len(rset & prefer)
    sc += min(2, prefer_hits * 0.5)

    # 避开最近一期（轻微惩罚）
    if rset & profile["avoid_last"]:
        sc -= 0.5

    return round(min(10, max(0, sc)), 1)


def _gen_max_coverage(stats, multi=None, n=5000):
    """
    特征画像定向生成：加权采样 + 画像过滤 + 贪心最大覆盖。
    前区重叠 ≤3。
    """
    profile = _build_feature_profile(stats, multi)

    rm = stats["_front_miss"]; maxr = max(rm.values()) or 1
    anom = profile["anom"]
    hot_r = set(stats["front_hot"])
    last_r = profile["avoid_last"]

    def red_w(i):
        return max(0.1,
                   1
                   + (rm.get(i, 0) / maxr) * 1.5
                   + (2 if i in anom else 0)
                   + (1 if i in hot_r else 0)
                   + (-0.5 if i in last_r else 0))

    bm = stats["_back_miss"]; maxb = max(bm.values()) or 1
    banom = set(stats["back_anom"]); hot_b = set(stats["back_hot"])

    def back_w(i):
        return max(0.1,
                   1 + (bm.get(i, 0) / maxb) * 1.5
                   + (2 if i in banom else 0)
                   + (1 if i in hot_b else 0))

    pool_r = list(range(FRONT_MIN, FRONT_MAX + 1))
    pool_b = list(range(BACK_MIN, BACK_MAX + 1))
    rw = [red_w(i) for i in pool_r]
    bw = [back_w(i) for i in pool_b]

    # 加权采样生成候选
    candidates = []; seen = set(); att = 0
    while len(candidates) < n and att < n * 5:
        att += 1
        reds = tuple(sorted(random.choices(pool_r, weights=rw, k=FRONT_PICK)))
        if len(set(reds)) != FRONT_PICK or reds in seen:
            continue
        seen.add(reds)
        backs = tuple(sorted(random.choices(pool_b, weights=bw, k=BACK_PICK)))
        sc = _score_candidate_by_profile(list(reds), profile)
        if sc >= 5.0:
            candidates.append((sc, list(reds), list(backs)))

    # 候选不够时放宽阈值
    if len(candidates) < 20:
        candidates = []
        seen2 = set()
        for _ in range(n * 2):
            reds = tuple(sorted(random.choices(pool_r, weights=rw, k=FRONT_PICK)))
            if len(set(reds)) != FRONT_PICK or reds in seen2:
                continue
            seen2.add(reds)
            backs = tuple(sorted(random.choices(pool_b, weights=bw, k=BACK_PICK)))
            sc = _score_candidate_by_profile(list(reds), profile)
            candidates.append((sc, list(reds), list(backs)))

    # 贪心最大覆盖：前区重叠 ≤3
    candidates.sort(key=lambda x: -x[0])
    picks = []
    for item in candidates:
        sc, reds, backs = item
        rset = set(reds)
        overlap_ok = True
        for p in picks:
            if len(rset & set(p[1])) > 3:
                overlap_ok = False
                break
        if not overlap_ok:
            continue
        picks.append(item)
        if len(picks) == RECOMMEND_N:
            break

    # 放宽重叠限制
    if len(picks) < RECOMMEND_N:
        for item in candidates:
            if item in picks:
                continue
            picks.append(item)
            if len(picks) == RECOMMEND_N:
                break

    return picks, profile


def _predict_back(stats, multi=None):
    """
    后区独立评分：基于遗漏、z-score、多窗口共识，
    输出 Top3 推荐 + 各候选评分。
    """
    bm = stats["_back_miss"]
    bz = stats["back_z"]
    banom = set(stats["back_anom"])
    hot_b = set(stats["back_hot"])
    cold_b = set(stats["back_cold"])
    maxb = max(bm.values()) or 1

    cons_cold = set(); cons_hot = set()
    if multi and "consensus" in multi:
        cons_cold = set(multi["consensus"]["back_cold"])
        cons_hot = set(multi["consensus"]["back_hot"])

    candidates = []
    for num in range(BACK_MIN, BACK_MAX + 1):
        sc = 0
        miss_ratio = bm.get(num, 0) / maxb
        sc += miss_ratio * 3

        z_val = bz.get(num, 0)
        if z_val < -2:
            sc += 2
        elif z_val < -1:
            sc += 1

        if num in banom:
            sc += 1.5

        if num in cons_cold:
            sc += 1.5

        if num in hot_b:
            sc += 0.5

        if num in cold_b:
            sc -= 0.3

        if num in cons_hot:
            sc -= 0.5

        candidates.append((round(sc, 2), num))

    candidates.sort(key=lambda x: -x[0])
    return candidates[:3], candidates


def cmd_recommend(_):
    hist = _load_history()
    if not hist:
        print("无本地数据，请先运行: python dlt.py fetch"); sys.exit(1)

    data = hist[:ANALYZE_WINDOW]
    stats = _compute_stats(data, full_history=hist)
    multi = _compute_multi_stats(hist)
    picks, profile = _gen_max_coverage(stats, multi=multi)
    if not picks:
        print("候选生成失败，请重试"); sys.exit(1)

    back_top3, back_all = _predict_back(stats, multi=multi)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print("  [Step 3] 本期推荐（特征画像 + 最大覆盖策略）")
    print("=" * 60)
    print(f"  基于最近 {ANALYZE_WINDOW} 期 | {now}")
    print(f"  [!] 头奖概率固定: 1/{TOTAL_COMBOS:,}，评分仅为结构合理性\n")

    # 特征画像概览
    print("  ── 特征画像 ─────────────────────────────────────────")
    print(f"  目标和值区间: [{profile['sum_range'][0]}, {profile['sum_range'][1]}] (均值{profile['sum_mean']})")
    print(f"  目标奇偶比: {profile['target_odd']}  目标大小比: {profile['target_big']}")
    cold_anom = sorted(profile['prefer_cold'] | profile['anom'])
    print(f"  偏好号(冷/异常): {' '.join(f'{n:02d}' for n in cold_anom)}")
    print(f"  偏好号(热): {' '.join(f'{n:02d}' for n in sorted(profile['prefer_hot']))}")
    print(f"  避开近期: {' '.join(f'{n:02d}' for n in sorted(profile['avoid_last']))}")
    print()

    to_save = []
    all_fronts_covered = set()
    for idx, (sc, reds, backs) in enumerate(picks[:RECOMMEND_N]):
        strat = STRATS[idx] if idx < len(STRATS) else f"采样{idx+1}"
        rs = " ".join(f"{r:02d}" for r in sorted(reds))
        bs = " ".join(f"{b:02d}" for b in sorted(backs))
        s = sum(reds); sp = max(reds) - min(reds)
        odd = sum(1 for r in reds if r % 2 == 1)
        big = sum(1 for r in reds if r >= 18)
        all_fronts_covered |= set(reds)

        print(f"【第{idx+1}注】{strat}")
        print(f"  前区 {rs}  后区 {bs}")
        print(f"  画像匹配分: {sc}/10")
        print(f"  特征: 和值={s}  跨度={sp}  奇偶={odd}:{FRONT_PICK-odd}  大小={big}:{FRONT_PICK-big}\n")
        to_save.append({"idx": idx+1, "strategy": strat, "front": sorted(reds), "back": sorted(backs), "score": sc})

    total_front = FRONT_MAX - FRONT_MIN + 1  # 35
    print(f"  覆盖统计: {RECOMMEND_N}注共覆盖 {len(all_fronts_covered)} 个不同前区号 ({len(all_fronts_covered)}/{total_front})")
    print(f"  覆盖率: {len(all_fronts_covered)/total_front*100:.0f}%\n")

    # 后区独立推荐
    print("  ── 后区推荐 ─────────────────────────────────────────")
    for rank, (sc, num) in enumerate(back_top3, 1):
        print(f"  TOP{rank}: {num:02d}  评分 {sc}")
    print()

    # 分位推荐
    pos = _position_analysis(hist, window=20)
    if pos:
        print("  ── 分位推荐（近20期每位独立统计）──────────────────")
        pos_names = ["第1位(龙头)", "第2位", "第3位", "第4位", "第5位(凤尾)"]
        for i in range(FRONT_PICK):
            p = pos["positions"][i]
            rec_str = " ".join(f"{n:02d}" for n in p["recommend"])
            hot_str = " ".join(f"{n:02d}" for n in p["hot"])
            print(f"  {pos_names[i]}: 热号{hot_str}  推荐 {rec_str}")
        for ci, combo in enumerate(pos["combos"], 1):
            cs = " ".join(f"{n:02d}" for n in combo)
            print(f"  分位组合{ci}: {cs}")
        print()

    arch = _load_archive()
    arch.append({"timestamp": now, "based_on": stats["latest_period"],
                 "window": ANALYZE_WINDOW, "predictions": to_save,
                 "back_predictions": [{"rank": i+1, "num": n, "score": s} for i, (s, n) in enumerate(back_top3)],
                 "actual": None, "review": None})
    _save_archive(arch)
    print(f"  预测存档: {ARCHIVE_FILE}")

    all_hits = [r["hit_front"] for e in arch if e.get("review") for r in e["review"]]
    if all_hits:
        total = len(all_hits); mx = max(all_hits); avg = statistics.mean(all_hits)
        print(f"  历史: {total} 次预测  前区最高 {mx}/{FRONT_PICK}  均值 {avg:.2f}/{FRONT_PICK}")

    out = {
        "based_on": stats["latest_period"], "window": ANALYZE_WINDOW, "timestamp": now,
        "picks": [{
            "rank": i+1, "strategy": STRATS[i] if i < len(STRATS) else f"采样{i+1}",
            "front": sorted(p[1]), "back": sorted(p[2]), "score": p[0],
            "features": {
                "sum": sum(p[1]), "span": max(p[1]) - min(p[1]),
                "odd_even": f"{sum(x%2 for x in p[1])}:{FRONT_PICK-sum(x%2 for x in p[1])}",
                "big_small": f"{sum(1 for x in p[1] if x>=18)}:{FRONT_PICK-sum(1 for x in p[1] if x>=18)}"
            }
        } for i, p in enumerate(picks[:RECOMMEND_N])],
        "back_top3": [{"rank": i+1, "num": n, "score": s} for i, (s, n) in enumerate(back_top3)],
        "coverage": {"unique_front": len(all_fronts_covered),
                     "total": FRONT_MAX - FRONT_MIN + 1,
                     "pct": round(len(all_fronts_covered) / (FRONT_MAX - FRONT_MIN + 1) * 100, 1)},
        "profile": profile,
    }
    print("\n[LLM_RECOMMEND_JSON_START]")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=list))
    print("[LLM_RECOMMEND_JSON_END]")


def cmd_review(args):
    if len(args.nums) < 8:
        print("用法: python dlt.py review <期号> <前1> <前2> <前3> <前4> <前5> <后1> <后2>")
        sys.exit(1)
    period = args.nums[0]
    act_front = sorted(int(x) for x in args.nums[1:6])
    act_back = sorted(int(x) for x in args.nums[6:8])
    arch = _load_archive()
    if not arch:
        print("无预测记录，先运行 recommend"); sys.exit(1)
    last = arch[-1]

    print("=" * 60)
    print(f"  [Step 4] 复盘 — {period} 期")
    print("=" * 60)
    fs = " ".join(f"{n:02d}" for n in act_front)
    bs = " ".join(f"{n:02d}" for n in act_back)
    print(f"开奖: 前区 {fs}  后区 {bs}\n")

    results = []
    for p in last["predictions"]:
        hf = len(set(p["front"]) & set(act_front))
        hb = len(set(p["back"]) & set(act_back))
        pz = _prize(hf, hb)
        fs2 = " ".join(f"{n:02d}" for n in p["front"])
        bs2 = " ".join(f"{n:02d}" for n in p["back"])
        print(f"  #{p['idx']} ({p['strategy']}) 画像分{p['score']}")
        print(f"    前 {fs2}  后 {bs2}  前{hf}/{FRONT_PICK} 后{hb}/{BACK_PICK} {pz}\n")
        results.append({"idx": p["idx"], "hit_front": hf, "hit_back": hb, "prize": pz})

    # 后区复盘
    if last.get("back_predictions"):
        print("  ── 后区复盘 ──")
        for bp in last["back_predictions"]:
            hit = "✓" if bp["num"] in act_back else "×"
            print(f"    TOP{bp['rank']} {bp['num']:02d} 评分{bp['score']}  {hit}")
        print()

    last["actual"] = {"period": period, "front": act_front, "back": act_back}
    last["review"] = results
    _save_archive(arch)

    # 累计统计
    all_hits = [r["hit_front"] for e in arch if e.get("review") for r in e["review"]]
    if all_hits:
        total = len(all_hits); mx = max(all_hits); avg = statistics.mean(all_hits)
        print(f"累计: {total} 次预测  前区最高 {mx}/{FRONT_PICK}  均值 {avg:.2f}/{FRONT_PICK}")
        prizes = Counter(r["prize"] for e in arch if e.get("review") for r in e["review"])
        print(f"中奖记录: {dict(prizes)}")

    # 随机基准对比
    random_expect = FRONT_PICK * FRONT_PICK / (FRONT_MAX - FRONT_MIN + 1)  # ~0.71
    if all_hits:
        actual_avg = statistics.mean(all_hits)
        diff = actual_avg - random_expect
        print(f"\n── 随机基准对比 ──")
        print(f"  随机期望: 每注 {random_expect:.2f}/{FRONT_PICK} 前区球")
        print(f"  实际均值: 每注 {actual_avg:.2f}/{FRONT_PICK} 前区球")
        if diff > 0.05:
            print(f"  偏差: +{diff:.2f}（略高于随机，结构筛选有微弱正向信号）")
        elif diff < -0.05:
            print(f"  偏差: {diff:.2f}（略低于随机，说明结构筛选未命中）")
        else:
            print(f"  偏差: {diff:.2f}（与随机基本持平）")
        print(f"  [!] 样本量小，偏差不具统计显著性")


def cmd_all(args):
    """一键全流程：fetch → analyze → recommend"""
    cmd_fetch(args)
    print()
    cmd_analyze(args)
    print()
    cmd_recommend(args)


# ── 6. 入口 ──────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="大乐透分析工具")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    sub.add_parser("analyze")
    sub.add_parser("recommend")
    sub.add_parser("all")
    rv = sub.add_parser("review")
    rv.add_argument("nums", nargs="+", help="期号 前1 前2 前3 前4 前5 后1 后2")
    args = p.parse_args()

    if args.cmd == "fetch":
        cmd_fetch(args)
    elif args.cmd == "analyze":
        cmd_analyze(args)
    elif args.cmd == "recommend":
        cmd_recommend(args)
    elif args.cmd == "all":
        cmd_all(args)
    elif args.cmd == "review":
        cmd_review(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
