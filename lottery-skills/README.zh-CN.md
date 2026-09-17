# 中国彩票分析工具集
<p align="center">
  <a href="https://github.com/Lucasyao1985/lottery-skills">GitHub</a> | <a href="https://github.com/Lucasyao1985/lottery-skills/issues">Report Issue</a>
</p>
<p align="center">
  <a href="https://github.com/Lucasyao1985/lottery-skills"><img alt="Release version" src="https://img.shields.io/github/v/release/Lucasyao1985/lottery-skills?color=2da44e&label=Latest&style=for-the-badge" /></a>
  <a href="https://www.python.org/downloads/"><img alt="Python version" src="https://img.shields.io/badge/Python-3.8%2B-0969da?style=for-the-badge" /></a>
  <a href="https://github.com/Lucasyao1985/lottery-skills/commits"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Lucasyao1985/lottery-skills?color=0969da&label=Last%20commit&style=for-the-badge" /></a>
  <a href="README.zh-CN.md"><img alt="中文" src="https://img.shields.io/badge/中文-da3633?style=for-the-badge" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-2da44e?style=for-the-badge" /></a>
</p>

---

**中国彩票分析工具集是一组 Python 工具，用于分析中国福利彩票和体育彩票的开奖数据。** 涵盖双色球、大乐透、排列3和排列5，全部基于官方 API。

<table>
<tr><td><b>官方数据源</b></td><td>所有工具直接使用官方彩票 API（500.com、webapi.sporttery.cn），无第三方爬虫。</td></tr>
<tr><td><b>多维度分析</b></td><td>遗漏值、冷热号、奇偶比、跨度、和值、012路等全方位分析。</td></tr>
<tr><td><b>智能推荐</b></td><td>基于统计规律生成号码推荐。</td></tr>
<tr><td><b>复盘对比</b></td><td>将历史预测与实开结果对比，评估策略有效性。</td></tr>
</table>

## 工具列表

| 工具 | 说明 | 官方接口 | 版本 |
|------|------|----------|------|
| `ssq/` | 双色球 | 500.com (HTML) | v6.3 |
| `daletou/` | 大乐透 | webapi.sporttery.cn (gameNo=85) | v2.0 |
| `pl3/` | 排列3 | webapi.sporttery.cn (gameNo=35) | v3.0 |
| `pl5/` | 排列5 | webapi.sporttery.cn (gameNo=350133) | v1.0 |

## 数据源

全部迁移至**官方原始 API**，无第三方依赖：
- 双色球：福利彩票 `https://datachart.500.com/ssq/history/newinc/history.php`（cwl.gov.cn 已被 WAF 拦截）
- 大乐透/排列3/排列5：体育彩票 `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry`

---

## 快速安装

```bash
git clone https://github.com/Lucasyao1985/lottery-skills.git
cd lottery-skills
pip install requests beautifulsoup4
```

## 使用方法

### 一键全流程（抓取 + 分析 + 推荐）

```bash
python ssq/scripts/ssq.py all
python daletou/scripts/dlt.py all
python pl3/scripts/pick3.py all
python pl5/scripts/pick5.py all
```

### 分步执行

#### 抓取最新开奖数据
```bash
python ssq/scripts/ssq.py fetch
python daletou/scripts/dlt.py fetch
python pl3/scripts/pick3.py fetch
python pl5/scripts/pick5.py fetch
```

#### 统计分析
```bash
python ssq/scripts/ssq.py analyze
python daletou/scripts/dlt.py analyze
python pl3/scripts/pick3.py analyze
python pl5/scripts/pick5.py analyze
```

#### 生成推荐
```bash
python ssq/scripts/ssq.py recommend
python daletou/scripts/dlt.py recommend
python pl3/scripts/pick3.py recommend
python pl5/scripts/pick5.py recommend
```

#### 复盘对比
```bash
python ssq/scripts/ssq.py review <期号> <红1>...<红6> <蓝>
python daletou/scripts/dlt.py review <期号> <前1>...<前5> <后1> <后2>
python pl3/scripts/pick3.py review <期号> <百位> <十位> <个位>
python pl5/scripts/pick5.py review <期号> <万> <千> <百> <十> <个>
```

## 数据存储

所有数据存储在用户目录下的独立文件夹中：

| 工具 | 路径 |
|------|------|
| 双色球 | `~/.ssq_data/` |
| 大乐透 | `~/.dlt_data/` |
| 排列3 | `~/.pl3_data/` |
| 排列5 | `~/.pl5_data/` |

每个目录包含：
- `history.json` — 历史开奖数据
- `latest_stats.json` — 最新统计结果
- `predictions.json` — 预测归档 + 复盘记录

## 项目结构

```
lottery-skills/
├── README.md                # 英文文档
├── README.zh-CN.md          # 中文文档
├── ssq/                     # 双色球
├── daletou/                 # 大乐透
├── pl3/                     # 排列3
├── pl5/                     # 排列5
├── _reviews/                # 预测复盘数据
```

## 许可证

MIT — 见 [LICENSE](LICENSE)。

由 [opencode](https://github.com/anomalyco/opencode) 构建。