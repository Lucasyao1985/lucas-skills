# 数据源与验证协议（v2.4）

> 本文是 `SKILL.md` 的参考细节层。权威实现见 `scripts/signal_agent.py`。

## 1. 端点清单（全部公开、无需 API key）

### 主源 — Binance 现货 `api.binance.com`
| 用途 | 端点 | 关键字段 |
|---|---|---|
| 实时价/24h统计 | `/api/v3/ticker/24hr?symbol={SYM}` | `lastPrice`, `closeTime`, `highPrice`, `lowPrice`, `volume`, `priceChangePercent` |
| K线 | `/api/v3/klines?symbol={SYM}&interval={IV}&limit={N}` | `[openTime,o,h,l,c,vol,...,closeTime,...]`；使用 `5m×48 / 15m×48 / 1h×48 / 4h×30` |
| 订单簿 | `/api/v3/depth?symbol={SYM}&limit=100` | `bids`, `asks`（全100档求和计深度） |
| 归集成交 | `/api/v3/aggTrades?symbol={SYM}&limit=500` | `q`=数量, `m`=true 表示 **taker 是卖方** |

### 衍生品 — Binance 合约 `fapi.binance.com`
| 用途 | 端点 | 说明 |
|---|---|---|
| **历史 OI** | `/futures/data/openInterestHist?symbol={SYM}&period=15m&limit=9` | `sumOpenInterest`；取最新值 vs ≈1h 前值计算真实 OI 变化 |
| 资金费率 | `/fapi/v1/premiumIndex?symbol={SYM}` | `lastFundingRate` 为**原始小数**（0.0001 = 0.01%） |
| 大户多空比 | `/futures/data/topLongShortAccountRatio?symbol={SYM}&period=5m&limit=1` | `longShortRatio` |

> ⚠️ **已失效端点**: `/fapi/v1/forceOrders` 与 `/futures/data/forceOrderStats`
> （爆仓数据）自 2026 年起**需要 API key**，实测返回 `-2014 API-key format invalid`。
> 爆仓因子已从评分引擎移除，权重归并至订单流组（详见 scoring-model.md）。

### 备源交叉验证（可选，缺失只降置信不阻断）
| 源 | 端点 | 字段 |
|---|---|---|
| OKX 现货 | `www.okx.com/api/v5/market/ticker?instId={BASE}-USDT` | `data[0].last` |
| CoinGecko | `api.coingecko.com/api/v3/simple/price?ids={ID}&vs_currencies=usd` | `{id}.usd`；币名映射表见 signal_agent.py `COINGECKO_IDS` |
| 恐惧贪婪 | `api.alternative.me/fng/?limit=1` | `data[0].value`（0-100） |
| **宏观日历** (v2.3) | `nfs.faireconomy.media/ff_calendar_thisweek.json` | `title/country/date/impact`；取 USD High/Medium 事件做静默窗门控，详见 macro-layer.md |
| **BTC/ETH 现货 ETF 净流入** (v2.4) | `farside.co.uk/btc/` · `farside.co.uk/eth/` | 日表 Total Net Flow（$M）；**模型层 WebFetch 抓取**（脚本直连被 Cloudflare 拦截），经 `--etf-flow-btc/-eth` 传入评分，详见 etf-flows.md |

## 2. 新鲜度校验规则

| 数据类型 | 最大允许时滞 | 超时处理 |
|---|---|---|
| Spot ticker (`closeTime`) | 60 s | 标记 notes；>120s 冒烟测试判失败 |
| K线最后一根 (`closeTime`) | 2 × interval | ≥2 个周期失鲜 → `DATA_STALE` 强制观望 |
| 历史 OI (`timestamp`) | 2 h | 缺失则该子项计 0 并记 notes |
| F&G | 24 h（设计如此） | 接受 |
| ETF 净流入 | 3 个已报告交易日（日线 T+1） | 未报告日跳过；抓取失败 → 子项计 0，不阻断 |

> 注：脚本对价格/OI/K线零缓存；唯一例外是宏观日历这类**排期型数据**
>（TTL 缓存无害）。ETF 净流入由模型层当场抓取后经 CLI 传入，天然单次有效。

## 3. 交叉验证协议

```
dev_okx = |price_binance − price_okx| / price_binance
dev_cg  = |price_binance − price_cg|  / price_binance
```

| 条件 | 动作 |
|---|---|
| 全部 ≤ 0.15% | ✅ confidence_base = 1.0 |
| 有偏差在 0.15%–0.50% | ⚠️ confidence_base = 0.85 |
| 任一 > 0.50% | 🚨 `DATA_CONFLICT` → 强制观望 |
| 备源全部不可用 | confidence_base 上限 0.80 |

## 4. 错误处理与降级阶梯

- **主机自动回退（v2.4）**：受限网络下 `api.binance.com` / `fapi.binance.com` 常被阻断
  （表现为 `<urlopen error timed out>` / curl `000`）。`signal_agent.py` 启动时会
  `resolve_hosts()` 依次探测 `SPOT_HOSTS` / `FAPI_HOSTS`，自动切到第一个可达主机。
  实测可用的现货镜像：`https://data-api.binance.vision`（合约端暂无公开可用镜像）。
  用 `BINANCE_SPOT_HOST` / `BINANCE_FAPI_HOST` 环境变量可强制指定主源；
  `--no-futures` 可跳过全部合约端点以免无谓等待。
- 所有请求：超时 8s、失败重试 1 次、响应上限 5MB。
- 单个端点失败 → 对应子因子计 0（或按上表降级），**绝不中断整个流程**。
- 全部失败 → 输出 `方向：观望` + `[SYSTEM_ERROR]`，进程退出码 2。
- 抓取优先级（配额受限时）：ticker + 15m/1h K线 + funding > depth + aggTrades + OI历史 > 备源 + 4h/5m。

## 5. 防缓存纪律

- 每次执行全部重新抓取，禁止复用上次结果或落盘缓存。
- 不使用任何持久状态；变量生命周期限于单次分析。
