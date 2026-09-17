# 双色球数据来源说明

## 唯一数据源

### 500.com 开奖历史页（datachart.500.com）✅

**URL：** `https://datachart.500.com/ssq/history/newinc/history.php?limit=N`

**状态：** ✅ 当前唯一数据源（v6.3 起）

**请求方式：** GET，返回 HTML 表格

**请求头：**
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
```

**解析方式：** 正则提取 `<tr>/<td>`，每行字段：
- 期号（如 "2026080"）
- 红球 6 个（第 3-8 列）
- 蓝球 1 个（第 9 列）
- 奖池、销售额
- 开奖日期

---

## 废弃数据源（永远不要再使用）

| 废弃源 | URL | 废弃原因 |
|--------|-----|---------|
| 中福彩官网 cwl.gov.cn | `www.cwl.gov.cn` | WAF 拦截返回 403（v6.3 起不可用） |
| 新浪彩票 | `lotto.sina.cn` | 停更，滞后至少 2 期 |
| 中彩网 | `zhcw.com` | 缓存严重，数据不准确 |

---

## 数据更新频率

### 官方开奖时间
- **周二：** 21:15
- **周四：** 21:15
- **周日：** 21:15

**建议：** 开奖后等待 10 分钟再抓取数据，确保数据已完全写入。

---

## 脚本说明

**脚本：** `scripts/ssq.py`

```bash
# 抓取最新数据（自动复盘上期预测）
python scripts/ssq.py fetch

# 统计分析（最近 30 期）
python scripts/ssq.py analyze

# 生成推荐（4 注 + 蓝球 TOP3）
python scripts/ssq.py recommend

# 一键全流程
python scripts/ssq.py all

# 复盘
python scripts/ssq.py review <期号> <红1>...<红6> <蓝>
```

---

## 数据存储

| 文件 | 内容 |
|------|------|
| `~/.ssq_data/history.json` | 全量历史开奖数据 |
| `~/.ssq_data/latest_stats.json` | 最近一次统计结果 |
| `~/.ssq_data/predictions.json` | 预测存档 + 复盘记录 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v6.3 | 2026-05 | 数据源迁移至 500.com（cwl.gov.cn 被 WAF 拦截 403） |
| v6.2 | 2026-04 | 完全迁移至 cwl.gov.cn 官方 API，删除所有废弃数据源 |
| v6.1 | 2026-02 | 分位分析、蓝球独立预测、多窗口分析 |

---

**最后更新：** 2026-08-09
