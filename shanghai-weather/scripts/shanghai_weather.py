#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上海天气查询脚本 - 数据来源: 上海市气象局 (sh.cma.gov.cn)

用法:
    python shanghai_weather.py                 # 获取全部(实时/今日/五日/预警/AQI/生活指数)
    python shanghai_weather.py today           # 仅今日预报
    python shanghai_weather.py now             # 仅实时观测
    python shanghai_weather.py forecast        # 仅五日预报
    python shanghai_weather.py alerts          # 仅灾害预警
    python shanghai_weather.py aqi             # 仅空气质量预报
    python shanghai_weather.py guide           # 仅生活气象指数
    python shanghai_weather.py --station 58367 # 指定站点(默认58367=徐家汇)
"""
import argparse
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    sys.stdout.write("错误: 需要 requests 库。请运行: pip install requests\n")
    sys.exit(1)

BASE = "http://smb.shweather.cn:5678/smb/Home/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
TIMEOUT = 30


def fetch(path):
    """抓取接口并解析为 JSON。失败时抛异常。"""
    resp = requests.get(BASE + path, headers=HEADERS, timeout=TIMEOUT)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    return resp.json()


def get_today(station):
    d = fetch("TodayWeather?stationid=%s" % station)
    out = []
    out.append("== 今日天气 (发布: %s) ==" % d.get("datatimess", ""))
    out.append("天气: %s (夜间: %s)" % (d.get("weather", ""), d.get("weathernight", "")))
    out.append("温度: %s ~ %s ℃" % (d.get("mintemp", ""), d.get("maxtemp", "")))
    if d.get("wind") or d.get("windspeed"):
        out.append("风力: %s %s" % (d.get("wind", ""), d.get("windspeed", "")))
    if d.get("waterprobability"):
        out.append("降水概率: %s%%" % d.get("waterprobability"))
    return "\n".join(out)


def get_now():
    d = fetch("GetStationListSH")
    out = []
    out.append("== 实时观测 (徐家汇站 %s) ==" % d.get("updatetime", ""))
    out.append("气温: %s ℃  湿度: %s%%" % (d.get("temperature", ""), d.get("humidity", "")))
    out.append("风向/风力: %s %s" % (d.get("wid", ""), d.get("wdlive", "")))
    out.append("气压: %s hPa" % d.get("airpress", ""))
    out.append("小时降水: %s mm" % d.get("rainhour", ""))
    return "\n".join(out)


def get_forecast(station):
    items = fetch("WeatherServiceFiveDay?stationid=%s" % station)
    if not items:
        return "== 五日预报 ==\n暂无数据"
    out = ["== 五日预报 (发布: %s) ==" % items[0].get("datatimes", "")]
    for d in items:
        day = d.get("foretime", "")[:10]
        out.append(
            "- %s %s: %s~%s℃, %s/%s, %s%s, 降水%s%%"
            % (
                day,
                d.get("week", ""),
                d.get("mintemp", ""),
                d.get("maxtemp", ""),
                d.get("weather", ""),
                d.get("weathernight", ""),
                d.get("wind", ""),
                d.get("windspeed", ""),
                d.get("waterprobability", ""),
            )
        )
    return "\n".join(out)


def get_alerts():
    items = fetch("GetAlertListByType?type=sh")
    if not items:
        return "== 灾害预警 ==\n当前无生效预警"
    out = ["== 灾害预警 =="]
    for d in items:
        out.append(
            "- %s [%s]: %s" % (d.get("publishtime", ""), d.get("signaltype", ""), d.get("signaltitle", ""))
        )
    return "\n".join(out)


def get_aqi():
    d = fetch("GetTextinfoAQI")
    out = ["== 空气质量预报 (发布: %s) ==" % d.get("publishtimes", "")]
    for it in d.get("data", []):
        time = it.get("time", "").replace("<br/>", " ")
        first = re.sub(r"<[^>]+>", "", it.get("first", "-"))
        out.append("- %s: AQI %s, 首要污染物 %s" % (time, it.get("quality", ""), first))
    return "\n".join(out)


def get_guide():
    items = fetch("GetGuidePointList")
    if not items:
        return "== 生活气象指数 ==\n暂无数据"
    out = ["== 生活气象指数 =="]
    for d in items:
        level = re.sub(r"级$", "", d.get("guidepointlevel", ""))
        out.append(
            "- %s: %s级 (%s) - %s"
            % (
                d.get("guidepointname", ""),
                level,
                d.get("leveltips", ""),
                d.get("guidepointtips", ""),
            )
        )
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="上海天气查询")
    parser.add_argument("section", nargs="?", default="all",
                        choices=["all", "today", "now", "forecast", "alerts", "aqi", "guide"],
                        help="要查询的内容")
    parser.add_argument("--station", default="58367", help="站点ID(默认58367=徐家汇)")
    args = parser.parse_args()

    handlers = {
        "all": [get_today, get_now, get_forecast, get_alerts, get_aqi, get_guide],
        "today": [get_today],
        "now": [get_now],
        "forecast": [get_forecast],
        "alerts": [get_alerts],
        "aqi": [get_aqi],
        "guide": [get_guide],
    }
    for fn in handlers[args.section]:
        try:
            if fn is get_today or fn is get_forecast:
                print(fn(args.station))
            else:
                print(fn())
        except Exception as e:
            print("[错误] 获取数据失败: %s" % e)
        print()


if __name__ == "__main__":
    main()
