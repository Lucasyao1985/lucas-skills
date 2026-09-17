---
name: shanghai-weather
description: 查询上海天气，数据来自上海市气象局官网（sh.cma.gov.cn 后台接口）。可获取实时观测、今日预报、五日预报、灾害预警、空气质量预报和生活气象指数。Use when user asks "上海天气"、"上海今天天气"、"上海天气预报"、"上海未来几天天气"、"上海空气质量"、"上海预警"、"上海生活指数"、shanghai weather、how is the weather in shanghai.
metadata:
  author: Lucas
  version: 1.0.0
  category: weather
  license: MIT
---

# 上海天气查询

查询上海（默认徐家汇站 58367）的实时天气与预报。数据源为上海市气象局官网后台接口 `http://smb.shweather.cn:5678/smb/Home/`，全部为公开页面使用的 JSON 接口。

## Instructions

### Step 1: 运行查询脚本

运行脚本获取全部天气信息：

```bash
python scripts/shanghai_weather.py
```

也可以按需只查询某一部分：

```bash
python scripts/shanghai_weather.py today      # 今日预报
python scripts/shanghai_weather.py now        # 实时观测
python scripts/shanghai_weather.py forecast   # 五日预报
python scripts/shanghai_weather.py alerts     # 灾害预警
python scripts/shanghai_weather.py aqi        # 空气质量预报
python scripts/shanghai_weather.py guide      # 生活气象指数
python scripts/shanghai_weather.py --station 58367   # 指定站点ID
```

脚本使用系统网络（含系统代理）。脚本依赖 `requests` 库，若报错请先 `pip install requests`。

### Step 2: 汇总并回答用户

拿到脚本输出后，按用户的具体问题整理成简洁的答复。例如用户问"上海今天天气怎么样"，优先给出：

- 今日天气（白天/夜间天气、最高/最低温、风、降水概率）
- 实时观测（当前气温、湿度、风）
- 如有关键预警（台风/暴雨等），务必首先提示

默认输出包含六大块：今日天气、实时观测、五日预报、灾害预警、空气质量预报、生活气象指数。天气变化大或有预警时提醒用户注意。

## Examples

Example 1: 用户问"上海今天天气"

```bash
python scripts/shanghai_weather.py today
```

输出今日天气（天气、温度、风力、降水概率），如有预警再运行 `alerts` 补充提示。

Example 2: 用户问"上海未来几天的天气"

```bash
python scripts/shanghai_weather.py forecast
```

按日期列出未来五天的天气、温度、风力和降水概率。

Example 3: 用户问"上海适合洗车吗"

```bash
python scripts/shanghai_weather.py guide
```

在生活指数中查找"洗晒指数"、"洗车指数"并直接给出结论。

## Troubleshooting

Error: `requests` 未安装
- Cause: 环境缺少 requests 库
- Solution: 运行 `pip install requests`

Error: 接口请求超时或报 502/连接失败
- Cause: 网络不通或代理异常，该接口需走网络访问
- Solution: 检查网络/代理后重试；可在脚本运行前确认 `python -c "import requests; requests.get('http://smb.shweather.cn:5678/smb/Home/GetTextinfoAQI', timeout=10)"` 能返回。

Error: 输出乱码
- Cause: 控制台编码不是 UTF-8
- Solution: 脚本已强制 UTF-8 输出，若仍乱码请用 `PYTHONIOENCODING=utf-8` 运行。
