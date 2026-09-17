---
name: pl5
description: '排列5数据分析工具。体彩官方API（webapi.sporttery.cn，gameNo=350133）单一可靠源，5位数分析（万/千/百/十/个位）、和值、跨度、冷热号统计。Trigger: "分析排列5" "排列五预测" "排列5推荐" "排列5走势"'
license: MIT
metadata:
  version: 1.0
  author: lottery-skills
  openclaw:
    requires:
      bins:
        - python
    os:
      - win32
---

# 排列5（v1.0 2026-05-19）

概率 1/100,000。所有计算由 Python 完成，Claude 只做解读，绝不自行运算。

## 彩种规则

- 每期开奖 5 位数字（万位、千位、百位、十位、个位），每位 0-9
- **直选**：5 位全中，单注奖金 **100,000 元**（固定奖金）
- **开奖时间**：每天一期，约 20:25
- 与排列3使用同一摇奖机，前3位即为排列3开奖号
- 数据覆盖排列3（前3位），因此不单独重复分析排列3数据

## 工作流路由

| 用户说 | 执行 |
|--------|------|
| 看数据 / 最新走势 | Step 2 |
| 推荐号码 / 帮我选 | Step 2 → Step 3 |
| 更新 / 抓最新数据 | Step 1 → 2 → 3 |
| 复盘 / 中了吗 / 上期结果 | Step 4 |
| 一键全流程 | Step 1 → 2 → 3 |

## ⚠️ 执行约束（强制）

本 skill 遵循 skill-execution-guard 四层防御框架。

**更新数据时，必须且只能执行以下命令：**

**禁止：**
- 自行编写 Python/Shell 代码调用外部 API
- 修改脚本中的硬编码参数（URL、lotteryId、pageSize 等）
- 使用此 SKILL.md 以外的数据源
- 在脚本之外执行任何网络请求获取开奖数据

---

## Step 1：联网抓取

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/pick5.py fetch [--periods 30|50|100]
```

从体彩官方API（webapi.sporttery.cn，gameNo=350133）抓取数据。默认拉取 100 期。

## Step 2：统计分析

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/pick5.py analyze
```

**必须解读的字段：**
- `miss_top` → 各位置遗漏 TOP3
- `hot_by_pos` / `cold_by_pos` → 各位置近20期冷热号（出现频率）
- `hot_digit` / `cold_digit` → 全局（跨位置）热号/冷号
- `sum_p20_p80` → 和值 60% 概率区间
- `span_mean` → 跨度均值
- `pos_freq` → 每位数字实际频率表

## Step 3：生成推荐

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/pick5.py recommend [--count 5]
```

输出：5 注推荐 + 和值 + 跨度 + 置信度。

## Step 4：开奖复盘

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/pick5.py review <期号> <万> <千> <百> <十> <个>
```

## 一键全流程

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/pick5.py all
```

## 示例

**示例 1：分析走势**
- 用户说："排列5走势分析"
- 操作：运行 `{baseDir}/scripts/pick5.py analyze`
- 结果：各位置遗漏 TOP3、冷热号、和值区间、跨度均值、频率表

**示例 2：推荐号码**
- 用户说："推荐几注排列5"
- 操作：`analyze` → `recommend`
- 结果：5 注推荐 + 和值 + 跨度 + 置信度

**示例 3：开奖复盘**
- 用户说："排列5上期中了吗"
- 操作：运行 `{baseDir}/scripts/pick5.py review <期号> <万> <千> <百> <十> <个>`
- 结果：命中情况 + 预测存档对比

## 数据存储

| 文件 | 内容 |
|------|------|
| `~/.pl5_data/history.json` | 全量历史开奖数据 |
| `~/.pl5_data/latest_stats.json` | 最近一次统计结果 |
| `~/.pl5_data/predictions.json` | 预测存档 + 复盘记录 |

## 数据源

| 来源 | URL | 用途 |
|------|-----|------|
| 体彩官方API | `https://webapi.sporttery.cn/gateway/lottery/getDigitalDrawInfoV1.qry?param=35,0;350133,0&isVerify=1` | 唯一数据源，GET 请求，无需 Cookie |
| 体彩页面 | `https://www.lottery.gov.cn/plwf/` | 页面验证（备选） |

**注意：** 排列五的 gameNo 是 350133（不是284），需要与排列三（gameNo=35）一起查询。

## 故障处理

| 症状 | 解决 |
|------|------|
| 缺少依赖 | `pip install requests beautifulsoup4` |
| 无本地数据 | 先运行 `pick5.py fetch` |
| FETCH_FAILED | 检查网络连接，稍后重试 `fetch` |
| 数据源变更 | 如 webapi.sporttery.cn 不可用，检查页面网络请求获取最新API端点 |
