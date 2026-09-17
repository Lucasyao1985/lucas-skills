---
name: crypto-signal-agent
description: >-
  Production-grade multi-asset directional signal engine for Binance USDT pairs,
  covering mainstream coins (BTC, ETH, SOL, BNB, XRP, DOGE, ADA, AVAX, LINK)
  and any other USDT pair. Up-to-14-factor weighted scoring (trend 30%, volume
  20%, derivatives 25%, order flow 15%, sentiment 10% incl. BTC/ETH spot-ETF
  net flows), per-coin risk calibration, dual-source cross-validation
  (Binance + OKX + CoinGecko), macro event gating, risk-gated output. Use when
  the user asks for crypto trade signals, 1-hour direction outlook, BTC/ETH
  ETF 资金流分析, 多空方向分析, 行情信号, 主流币/DOGE 行情, or position PnL
  (持仓盈亏). Generates research signals only — never executes trades.
metadata:
  author: crypto-signal-team
  version: "2.4.0"
allowed-tools: Bash
compatibility: "需要 Python 3.8+（脚本零第三方依赖）；ETF 覆盖层需模型侧网页抓取能力（WebFetch）。数据源: Binance 现货+合约、OKX、CoinGecko、Fear & Greed、Farside ETF。仅生成方向信号，不执行交易。"
---

# Crypto Signal Agent

对任意币安 USDT 交易对输出 **1 小时展望的方向信号**（做多/做空/观望），
基于多因子加权评分 + 主流币画像校准 + 双源交叉验证 + 风控门控。

## 支持币种

内置 9 大主流币画像（风控阈值按币校准，BTC/ETH 额外含现货 ETF 资金流因子）：
BTC、ETH、SOL、BNB、XRP、**DOGE**、ADA、AVAX、LINK。
其余任意币安 USDT 交易对同样支持（未收录币种走保守默认画像，
见 `references/scoring-model.md` §2 币种画像表）。

## 快速开始

```bash
# 权威实现（纯标准库，任何 Python 3.8+ 可跑，无需 pip install）
python scripts/signal_agent.py                    # 默认 BTCUSDT
python scripts/signal_agent.py ETHUSDT DOGEUSDT   # 多币种（DOGE 等主流币直接写）
python scripts/signal_agent.py --major            # 扫描全部 9 大主流币（约 1 分钟）
python scripts/signal_agent.py BTCUSDT --json     # 机器可读（含子因子明细）
python scripts/signal_agent.py BTCUSDT --debug    # stderr 显示计算过程

# BTC/ETH 附带现货 ETF 资金流（近3交易日净流入 $M，旧→新；抓取见 etf-flows.md §1）
# 注意：首值为负数时必须用 = 连接，否则 argparse 会把 -236.5 当选项
python scripts/signal_agent.py BTCUSDT --etf-flow-btc=-236.5,101.1,730.8

# 冒烟测试（离线数学单测 + 在线端到端契约校验）
python tests/smoke_test.py                # 全部
python tests/smoke_test.py --offline      # 仅离线部分
```

脚本不可用时（无 Python），按 `references/data-sources.md` 的端点清单用 curl
抓取数据，人工/模型按 `references/scoring-model.md` 公式计算。

## 执行协议

| 步骤 | 动作 | 细节 |
|---|---|---|
| 1 | 解析用户指定的交易对（缺省 BTCUSDT；自动补 USDT 后缀；`--major` 覆盖主流币清单） | |
| 2 | **仅 BTC/ETH**：用模型侧网页抓取取 Farside 近 3 个已报告交易日 ETF 净流入（失败则跳过，自动降级） | etf-flows.md §1 |
| 3 | 运行 `signal_agent.py`（BTC/ETH 附带 `--etf-flow-btc` / `--etf-flow-eth` 传入合计前逐日数值） | |
| 4 | 脚本内置：并行抓取端点 → 新鲜度校验 → OKX/CoinGecko 交叉验证 → 14 因子评分 → 币种画像风控 → 宏观门控 | data-sources.md / scoring-model.md / risk-and-pnl.md / macro-layer.md |
| 5 | 按输出契约呈现结果；解读数据时结合步骤 2 的 ETF 逐日节奏（连续同向才算趋势） | etf-flows.md §3 |

## 输出契约（强制）

stdout 第一行必须是 `方向：`，值只能是 `做多` / `做空` / `观望`：

```
方向：[做多 / 做空 / 观望]

入场区间：$XX,XXX – $XX,XXX        （观望时填 —）
止损位：$XX,XXX                    （观望时填 —）
目标位：$XX,XXX（主）/ $XX,XXX（延伸）（观望时填 —）

方向评分：±XX.X / 100
执行方案：

  胜率评分：XX %
  信号强度：XX / 100
  数据可信度：XX %
  数据时间：YYYY-MM-DD HH:MM:SS UTC
  风控标记：（仅触发时输出）
```

规则：
- 所有价格必须来自**本次实时抓取**，禁止使用缓存或记忆中的价格
- 观望时入场/止损/目标全部为 `—`
- 不输出推理过程、中间计算值、工具调用日志、免责声明（stdout）
- 不同时给出多个方向；置信度 <70% 强制观望

## 持仓盈亏模式

用户提供持仓信息（方向/开仓价/数量/保证金/杠杆/浮动盈亏）时，
按 `references/risk-and-pnl.md` §3 计算。**铁律：方向以用户陈述为准；
浮动盈亏以用户实盘数字为 ground truth；建议平仓前先确认。**

## 参考文档

| 文件 | 内容 |
|---|---|
| `references/data-sources.md` | 端点清单、新鲜度规则、交叉验证、降级阶梯 |
| `references/scoring-model.md` | 因子权重表、全部公式、主流币画像 |
| `references/etf-flows.md` | BTC/ETH 现货 ETF 资金流抓取与评分协议 |
| `references/risk-and-pnl.md` | 风控标记、入场计算、持仓盈亏计算器 |
| `references/macro-layer.md` | 美联储事件静默窗、BTC 联动门控 |
| `references/accuracy-notes.md` | 准确率设计、已知局限、版本修复清单 |

## 守则

- 本 skill 只产出研究性方向信号：**不下单、不管钱、不构成投资建议**。
- 极端行情（ATR 超币种阈值、资金费率 >0.10%/期、深度低于币种下限）宁可观望。
- FOMC/CPI/非农等高影响事件前后（静默窗内）不出方向信号；对话中用户问及
  宏观背景或 ETF 流向解读时，由运行本 skill 的模型结合实时数据/新闻解读，
  脚本层不做新闻 NLP。
- ETF 净流入是顺势慢变量（日线 T+1）：单日大额不算趋势，连续 3 日同向才
  提升叙事权重（见 etf-flows.md §3）。
- 目标持有期 1 小时；短线刷单或长线持仓场景需重新校准（见 accuracy-notes.md §5）。
