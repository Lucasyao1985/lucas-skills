# BTC/ETH 现货 ETF 资金流覆盖层（v2.4）

> ETF 净流入是**机构增量买卖盘**的直接度量：净流入 = 增量买盘（顺势利多），
> 净流出 = 增量卖盘（顺势利空）。注意与 F&G / 资金费率的**逆向**语义相反。
> 只覆盖 BTC 与 ETH（其他币种无现货 ETF，情绪组自动回到 50/50 旧权重）。

## 1. 数据抓取（模型层执行，脚本层不可达）

**首选源 — Farside Investors**（脚本直接 curl/urllib 会被 Cloudflare 拦截，
必须用模型侧网页抓取工具，如 WebFetch，实测可用）：

- BTC: `https://farside.co.uk/btc/`
- ETH: `https://farside.co.uk/eth/`

WebFetch 提示词模板（照抄即可）：

```
This page contains a table of daily Bitcoin spot ETF net flows
(Total Net Flow per day, in $M). Report the Total Net Flow values
for the last 3 trading days with reported data (skip rows that are
dashes / not yet reported), with dates. Parentheses mean negative.
```

解析规则：
- 括号 `(201.9)` = 负数 → `-201.9`；单位 $M。
- **跳过数据未出全的行**（当日/未报告行显示 `—` 或全 0，报告截止一般为美东
  收盘后）。只取**最近 3 个已报告交易日**，按旧→新排列。
- 换算成合计值传给脚本：`--etf-flow-btc M1,M2,M3`（旧→新，逗号分隔）。

示例（2026-09-03 实测数据）：

```bash
# 注意：首值为负数时必须用 = 连接（argparse 会把 -236.5 当选项）
python scripts/signal_agent.py BTCUSDT --etf-flow-btc=-236.5,101.1,730.8
python scripts/signal_agent.py ETHUSDT  --etf-flow-eth=41.2,-18.7,96.4
```

## 2. 评分公式（脚本内 `etf_tier`）

```
sum3 = 近3个已报告交易日净流入合计（$M）
etf_score = clip(sum3 / 5, −80, +80)      # ±400 $M/3日 → 满分
```

| sum3 | 分值 | 解读 |
|---|---|---|
| ≥ +400 | +80 | 机构强劲吸筹，顺势强利多 |
| +100 ~ +400 | +20 ~ +80 | 温和流入 |
| −100 ~ +100 | ±20 | 噪声区 |
| −400 ~ −100 | −20 ~ −80 | 温和流出 |
| ≤ −400 | −80 | 机构持续撤资，顺势强利空 |

情绪组（全局 10%）内部权重：有 ETF 数据时 `F&G 35% / 资金费率 35% / ETF 30%`；
无数据时回到 `50/50/0`（见 scoring-model.md §1）。

## 3. 降级与防误判

- 抓取失败 / 解析失败 / 参数非法 → **省略 `--etf-flow-*` 即可**，ETF 子项计 0，
  不罚分、不阻断、不加风控标记（仅少一个信息源）。
- ETF 数据是**日线 T+1** 口径（当日数据收盘后才发布），对 1 小时展望而言属于
  慢变量：它改变的是机构背景，不追日内脉冲。连续 3 日同向才有含义，单日大额
  且与价格背离时不加倍权重。
- 美国节假日 / 周末无报告行，属于正常，不算数据过期。
- Farside 不可用时可用 SoSoValue / CoinGlass 网页版人工读数替代（同样取近
  3 个已报告日合计），口径一致。
