#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
排列五（排列5）数据分析工具 v1.0
用法:
  python pick5.py fetch      # 联网抓取最新数据
  python pick5.py analyze    # 分析最近30期，输出统计
  python pick5.py recommend  # 生成5注推荐+置信度+投注类型
  python pick5.py all        # 一键全流程
  python pick5.py review <期号> <万> <千> <百> <十> <个>

依赖: pip install requests beautifulsoup4
复用 Conda 环境: D:\Conda\envs\ssq-lottery-analysis\
数据存储: C:\Users\用户名\.pl5_data\

排列5规则: 每期5位数字(万/千/百/十/个)，每位0-9，直选奖金100,000元
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

TOTAL_COMBOS   = 100000
ANALYZE_WINDOW = 30
RECOMMEND_N    = 5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.lottery.gov.cn/",
    "Origin": "https://www.lottery.gov.cn",
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}
NO_PROXY = {"http": "", "https": ""}
DATA_DIR  = Path.home() / ".pl5_data"
HIST_FILE = DATA_DIR / "history.json"
ARCHIVE_FILE = DATA_DIR / "predictions.json"
STATS_FILE = DATA_DIR / "latest_stats.json"


# ── 1. 数据抓取 ──────────────────────────────────────

def fetch_from_sporttery(page_size=100, timeout=20):
    """体彩官方API（排列5 gameNo=350133）"""
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    params = {
        "gameNo": "350133",    # 350133 = 排列5
        "provinceId": "0",
        "pageSize": str(page_size),
        "isVerify": "1",
        "pageNo": "1",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS,
                           timeout=timeout, proxies=NO_PROXY)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorCode") != "0":
            raise Exception(data.get("errorMsg", "API返回异常"))

        records = []
        for item in data.get("value", {}).get("list", []):
            period = item.get("lotteryDrawNum", "")
            result_str = item.get("lotteryDrawResult", "")
            nums = [int(x) for x in result_str.split() if x.isdigit()]
            if len(nums) == 5:
                wan, qian, bai, shi, ge = nums
                sum_val = wan + qian + bai + shi + ge
                span = max(nums) - min(nums)
                records.append({
                    "period": period,
                    "wan": wan,
                    "qian": qian,
                    "bai": bai,
                    "shi": shi,
                    "ge": ge,
                    "sum_val": sum_val,
                    "span": span,
                    "date": item.get("lotteryDrawTime", "")[:10],
                })
        print(f"  sporttery.cn: 拉取 {len(records)} 期")
        return records
    except Exception as e:
        print(f"  sporttery.cn 抓取失败: {e}")
        return []


def cmd_fetch(args):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 58)
    print("  [Step 1] 联网抓取")
    print("=" * 58)

    periods = getattr(args, 'periods', 100) or 100
    records = fetch_from_sporttery(periods)
    if not records:
        print("FETCH_FAILED:网络请求失败或 API 返回异常")
        return

    existing  = _load_history()
    exist_set = {r["period"] for r in existing}
    new_n     = 0
    for r in records:
        if r["period"] not in exist_set:
            existing.append(r); new_n += 1
    existing.sort(key=lambda x: x["period"], reverse=True)
    _save_history(existing)

    lat = existing[0]
    nums = f"{lat['wan']} {lat['qian']} {lat['bai']} {lat['shi']} {lat['ge']}"
    print(f"新增 {new_n} 期，本地共 {len(existing)} 期")
    print(f"最新: {lat['period']}  开奖号 {nums}  和值={lat['sum_val']}")

    api_latest = records[0]["period"] if records else None
    local_latest = lat["period"]
    if api_latest and api_latest == local_latest:
        print(f"FETCH_OK:{local_latest}")
    elif api_latest and api_latest > local_latest:
        print(f"UPDATE_FAILED:本地 {local_latest} 仍落后于 API {api_latest}")
    else:
        print(f"FETCH_OK:{local_latest}")


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

def _load_stats():
    if STATS_FILE.exists():
        try: return json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except: pass
    return {}

def _save_stats(d):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 2. 统计分析 ──────────────────────────────────────

def cmd_analyze(_):
    """分析最近30期，输出统计"""
    print("=" * 58)
    print("  [Step 2] 统计分析（最近30期）")
    print("=" * 58)

    history = _load_history()
    if not history:
        print("无历史数据，请先运行 fetch")
        return

    recent = history[:30]
    latest = recent[0]
    print(f"最新: {latest['period']}  开奖号 {latest['wan']} {latest['qian']} {latest['bai']} {latest['shi']} {latest['ge']}")
    print(f"      和值={latest['sum_val']}  跨度={latest['span']}\n")

    positions = ['wan', 'qian', 'bai', 'shi', 'ge']
    pos_names = ['万位', '千位', '百位', '十位', '个位']

    # 各位统计
    stats = {}
    for pos, name in zip(positions, pos_names):
        nums = [r[pos] for r in recent]
        cnt = Counter(nums)
        hot = cnt.most_common(3)
        cold = cnt.most_common()[-3:] if len(cnt) >= 3 else cnt.most_common()
        stats[pos] = {"hot": hot, "cold": cold, "counter": cnt}
        print(f"── {name}热号 ──")
        for n, c in hot:
            print(f"  {n}: {c}次")
        print(f"  冷号: {', '.join(str(n) for n, _ in cold)}")

    # 遗漏值
    print("\n── 遗漏值（各位）──")
    miss_top = {}
    for pos, name in zip(positions, pos_names):
        for digit in range(10):
            for i, r in enumerate(recent):
                if r[pos] == digit:
                    miss_top[f"{name}_{digit}"] = i
                    break
            else:
                miss_top[f"{name}_{digit}"] = 30
        sorted_miss = sorted(miss_top.items(), key=lambda x: x[1], reverse=True)[:5]
        parts = [f"{k.split('_')[-1]}={v}期" for k, v in sorted_miss]
        print(f"  {name}: {', '.join(parts)}")

    # 和值
    sums = [r['sum_val'] for r in recent]
    sum_p20 = sorted(sums)[int(len(sums)*0.2)]
    sum_p80 = sorted(sums)[int(len(sums)*0.8)]
    print(f"\n── 和值 ──  均值={statistics.mean(sums):.1f}  σ={statistics.stdev(sums):.1f}  区间[{sum_p20}-{sum_p80}]")

    # 跨度
    spans = [r['span'] for r in recent]
    print(f"── 跨度 ──  均值={statistics.mean(spans):.1f}  σ={statistics.stdev(spans):.1f}")

    # 全局热号/冷号
    all_digits = []
    for r in recent:
        all_digits.extend([r[p] for p in positions])
    all_cnt = Counter(all_digits)
    hot_all = all_cnt.most_common(5)
    cold_all = all_cnt.most_common()[-5:]
    print(f"\n── 全局热号 ──  {', '.join(f'{n}({c}次)' for n, c in hot_all)}")
    print(f"── 全局冷号 ──  {', '.join(f'{n}({c}次)' for n, c in cold_all)}")

    # 奇偶比
    odd_counts = [sum(1 for p in positions if r[p] % 2 == 1) for r in recent]
    even_counts = [5 - o for o in odd_counts]
    odd_avg = statistics.mean(odd_counts)
    print(f"\n── 奇偶比 ──  奇数均值={odd_avg:.1f}  偶数均值={5-odd_avg:.1f}")

    # 大小比（0-4小，5-9大）
    big_counts = [sum(1 for p in positions if r[p] >= 5) for r in recent]
    small_counts = [5 - b for b in big_counts]
    big_avg = statistics.mean(big_counts)
    print(f"── 大小比 ──  大数均值={big_avg:.1f}  小数均值={5-big_avg:.1f}")

    # 012路分析
    for route in range(3):
        route_counts = [sum(1 for p in positions if r[p] % 3 == route) for r in recent]
        print(f"── {route}路 ──  均值={statistics.mean(route_counts):.1f}")

    # 保存统计结果
    stats_data = {
        "latest_period": latest["period"],
        "latest_nums": [latest['wan'], latest['qian'], latest['bai'], latest['shi'], latest['ge']],
        "sum_mean": round(statistics.mean(sums), 1),
        "sum_std": round(statistics.stdev(sums), 1),
        "sum_p20_p80": [sum_p20, sum_p80],
        "span_mean": round(statistics.mean(spans), 1),
        "span_std": round(statistics.stdev(spans), 1),
        "hot_by_pos": {pos: stats[pos]["hot"] for pos in positions},
        "cold_by_pos": {pos: stats[pos]["cold"] for pos in positions},
        "hot_digit": hot_all,
        "cold_digit": cold_all,
        "odd_avg": round(odd_avg, 1),
        "big_avg": round(big_avg, 1),
        "pos_freq": {pos: dict(Counter([r[pos] for r in recent])) for pos in positions},
        "miss_top": miss_top,
    }
    _save_stats(stats_data)


# ── 3. 生成推荐 ──────────────────────────────────────

def cmd_recommend(args):
    """生成推荐"""
    print("=" * 58)
    print("  [Step 3] 生成推荐")
    print("=" * 58)

    history = _load_history()
    if not history:
        print("无历史数据，请先运行 fetch")
        return

    recent = history[:30]
    positions = ['wan', 'qian', 'bai', 'shi', 'ge']
    pos_names = ['万位', '千位', '百位', '十位', '个位']

    # 各位热号（前3）
    hot_by_pos = {}
    for pos, name in zip(positions, pos_names):
        hot = [n for n, _ in Counter(r[pos] for r in recent).most_common(3)]
        hot_by_pos[pos] = hot
        print(f"{name}热号: {hot}")

    count = getattr(args, 'count', 5) or 5
    print(f"\n── 推荐{count}注 ──")
    recs = []
    for i in range(count):
        rec = [random.choice(hot_by_pos[pos]) for pos in positions]
        recs.append(rec)
        s = sum(rec)
        sp = max(rec) - min(rec)
        print(f"  第{i+1}注: {' '.join(map(str, rec))}  和值={s}  跨度={sp}")

    # 存档
    archive = _load_archive()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "recommend",
        "recommendations": recs,
    }
    archive.append(entry)
    _save_archive(archive)


# ── 4. 复盘 ──────────────────────────────────────────

def cmd_review(args):
    """复盘"""
    if len(args.nums) != 6:
        print("用法: review <期号> <万> <千> <百> <十> <个>")
        return
    period = args.nums[0]
    user_nums = [int(x) for x in args.nums[1:6]]

    history = _load_history()
    found = next((r for r in history if r['period'] == period), None)
    if not found:
        print(f"未找到期号 {period}")
        return

    actual = [found['wan'], found['qian'], found['bai'], found['shi'], found['ge']]
    print(f"期号 {period} 开奖: {' '.join(map(str, actual))}")
    print(f"您的号码: {' '.join(map(str, user_nums))}")

    matches = sum(1 for a, b in zip(user_nums, actual) if a == b)
    print(f"匹配数: {matches}/5")

    if matches == 5:
        print("恭喜！直选中奖！奖金 100,000 元！")
    elif matches >= 3:
        print(f"匹配 {matches} 位，不错！")
    else:
        print(f"匹配 {matches} 位，继续加油！")


# ── 入口 ──────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="排列五（排列5）数据分析工具 v1.0")
    sub = p.add_subparsers(dest="cmd")

    fetch_p = sub.add_parser("fetch")
    fetch_p.add_argument("--periods", type=int, default=100, choices=[30, 50, 100])

    sub.add_parser("analyze")

    rec_p = sub.add_parser("recommend")
    rec_p.add_argument("--count", type=int, default=5)

    sub.add_parser("all")

    rv = sub.add_parser("review")
    rv.add_argument("nums", nargs="+")

    args = p.parse_args()

    if args.cmd == "fetch":       cmd_fetch(args)
    elif args.cmd == "analyze":   cmd_analyze(args)
    elif args.cmd == "recommend": cmd_recommend(args)
    elif args.cmd == "all":
        cmd_fetch(args); print(); cmd_analyze(args); print(); cmd_recommend(args)
    elif args.cmd == "review":    cmd_review(args)
    else: p.print_help()

if __name__ == "__main__":
    main()
