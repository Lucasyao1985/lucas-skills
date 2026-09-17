---
name: lottery-ssq
description: '双色球（SSQ）走势数据分析工具。500.com 数据源（cwl.gov.cn 已失效），多窗口分析（10/20/30/50期并行）、特征画像推荐、蓝球独立预测、复盘对比。Use when user asks 分析双色球、双色球走势、推荐双色球号码、双色球预测、ssq 分析。'
license: MIT
metadata:
  version: 6.3
  author: lottery-skills
  openclaw:
    requires:
      bins:
        - python
    os:
      - win32
---

# 双色球（v6.3 2026-05 数据源迁移至 500.com）

概率 1/17,720,024。所有计算由 Python 完成，Claude 只做解读，绝不自行运算。

⚠️ **免责声明：** 所有评分仅为组合结构合理性评估（和值、奇偶、分区是否符合历史分布），不改变中奖概率。头奖概率固定 1/17,720,024。

## 环境

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe -c "import requests,bs4; print('就绪')"
```

## v6.3 改动（2026-05）

- **数据源**：`500.com` HTML 表格（cwl.gov.cn 被 WAF 拦截 403，不可用）
- **分位分析**：6 个红球位置独立统计（频率、012路、奇偶、质合），每位 TOP3 推荐 + 2 注组合
- **蓝球独立预测**：独立评分模块，蓝球 TOP3
- 多窗口分析：10/20/30/50 期并行
- 特征画像推荐 + 候选池 5000

## 工作流路由

| 用户说 | 执行 |
|--------|------|
| 分析 / 看数据 / 最新走势 | Step 2 |
| 推荐号码 / 帮我选 / 出号 | Step 2 → Step 3 |
| 更新 / 抓最新 / 今天开奖了吗 | Step 1 → 2 → 3 |
| 复盘 / 中了吗 / 上期结果 | Step 4 |
| 全部 / 一键 | Step 1 → 2 → 3 |

## ⚠️ 执行约束（强制）

本 skill 遵循 skill-execution-guard 四层防御框架。

**更新数据时，必须且只能执行以下命令：**

**禁止**：
- 自行编写 Python/Shell 代码调用外部 API
- 修改脚本中的硬编码参数（gameNo、URL、Headers、issueCount 等）
- 使用此 SKILL.md 以外的数据源
- 在脚本之外执行任何网络请求获取开奖数据

**违规后果**：自行编写的代码极有可能引入已修复的 bug（字段名错误、请求头缺失），导致数据更新失败或数据损坏。

---

## Step 1：联网抓取

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/ssq.py fetch
```

开奖时间：周二、周四、周日 21:15，建议等 10 分钟后再抓。
**注意：fetch 会自动复盘上期预测。**

## Step 2：统计分析

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/ssq.py analyze
```

**多窗口输出（新增 v6）：**
- 10/20/30/50 期各窗口的异常冷号、和值均值
- 共识分析：所有窗口一致判定的冷/热号、分歧号（短冷长热→可能回补，短热长冷→趋势退潮）

**必须解读的字段：**
- `red_anom` / `blue_anom` → 统计异常沉寂号（z-score < -2σ）
- `red_miss_top5` / `blue_miss_top3` → 遗漏 TOP
- `red_hot/cold` → 近 20 期冷热
- `sum_p20_p80` → 和值 60% 概率区间

## Step 3：生成推荐

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/ssq.py recommend
```

输出：4 注红球 + 蓝球 TOP3 + 特征画像 + 覆盖统计。

**画像匹配分：** 0-10，评估组合与特征画像的匹配度。高分 ≠ 高中奖率。

**蓝球模块（新增 v6）：** 独立评分，基于遗漏、z-score、多窗口共识，输出 TOP3。

## Step 4：开奖复盘

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/ssq.py review <期号> <红1>...<红6> <蓝>
```

v6 新增：
- 蓝球 TOP3 复盘（命中/未命中）
- 随机基准对比（实际均值 vs 随机期望 1.09/6 红球）

## 一键全流程

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/ssq.py all
```

## 示例

**示例 1：分析最新走势**
- 用户说："分析一下双色球"
- 操作：运行 `{baseDir}/scripts/ssq.py analyze`
- 结果：输出 10/20/30/50 期多窗口统计、冷热号共识、异常沉寂号，解读 red_anom / red_miss_top5 / sum_p20_p80 等关键字段

**示例 2：推荐号码**
- 用户说："帮我推荐几注双色球"
- 操作：数据已最新则直接 `analyze` → `recommend`，否则先 `fetch`
- 结果：4 注红球 + 蓝球 TOP3 + 特征画像匹配分

**示例 3：开奖复盘**
- 用户说："上期中了吗"
- 操作：运行 `{baseDir}/scripts/ssq.py review <期号> <红1>...<红6> <蓝>`
- 结果：红球/蓝球命中情况、蓝球 TOP3 复盘、随机基准对比

## 数据存储

| 文件 | 内容 |
|------|------|
| `~/.ssq_data/history.json` | 全量历史开奖数据 |
| `~/.ssq_data/latest_stats.json` | 最近一次统计结果 |
| `~/.ssq_data/predictions.json` | 预测存档 + 复盘记录（v6 格式含 blue_predictions） |

详细文档：数据源见 `references/DATA_SOURCES.md`，环境安装见 `references/INSTALL.md`，游戏规则见 `references/RULES.md`。

## 故障处理

| 症状 | 解决 |
|------|------|
| 缺少依赖 | `pip install requests beautifulsoup4` |
| 无本地数据 | 先运行 `ssq.py fetch` |
| FETCH_FAILED | 检查网络连接，稍后重试 `fetch` |
| HTTP 503 | 等 1-2 分钟重试 |
