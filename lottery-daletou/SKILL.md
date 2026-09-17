---
name: daletou
description: '大乐透走势数据分析工具。体彩官方API（webapi.sporttery.cn，gameNo=85）单一可靠源，多维度分析（遗漏值、冷热号、奇偶比、大小比、跨度、和值、012路、前后区分离分析），最大覆盖策略推荐。Trigger: "分析大乐透" "推荐大乐透号码" "大乐透走势" "大乐透冷热号" "大乐透预测" "dlt分析" "超级大乐透"'
license: MIT
metadata:
  version: 2.0
  author: lottery-skills
  openclaw:
    requires:
      bins:
        - python
    os:
      - win32
---

# 大乐透（v2.0 2026-04 官方接口）

所有计算由 Python 完成，Claude 只做解读，绝不自行运算。

⚠️ **免责声明：** 所有评分仅为组合结构合理性评估，不改变中奖概率。

## 环境

复用双色球 Conda 环境：
```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe -c "import requests,bs4; print('就绪')"
```

## 彩种规则

- **前区**：01-35 选 5
- **后区**：01-12 选 2
- **开奖时间**：周一、三、六 21:10
- **九个奖级**：一等奖（5+2）到九等奖（3个前区 或 1前区+2后区 或 2前区+1后区 或 2后区）

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
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/dlt.py fetch
```

从体彩官方 API（webapi.sporttery.cn，gameNo=85）抓取最近 100 期开奖数据，自动保存到 `~/.dlt_data/history.json`。

## Step 2：统计分析

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/dlt.py analyze
```

前后区分离分析：遗漏值、z-score 异常、冷热号、012路、奇偶、大小、和值、跨度。

## Step 3：生成推荐

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/dlt.py recommend
```

输出：4 注推荐（前区5+后区2），覆盖策略 + 结构评分。

## Step 4：开奖复盘

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/dlt.py review <期号> <前1>...<前5> <后1> <后2>
```

## 一键全流程

```cmd
D:\Conda\envs\ssq-lottery-analysis\python.exe {baseDir}/scripts/dlt.py all
```

## 示例

**示例 1：分析最新走势**
- 用户说："大乐透走势怎么样"
- 操作：运行 `{baseDir}/scripts/dlt.py analyze`
- 结果：前区/后区分离分析（遗漏值、z-score 异常、冷热号、012路、奇偶、大小、和值、跨度）

**示例 2：推荐号码**
- 用户说："推荐几注大乐透"
- 操作：`analyze` → `recommend`
- 结果：4 注推荐（前区5+后区2）+ 覆盖策略 + 结构评分

**示例 3：开奖复盘**
- 用户说："上期大乐透中了吗"
- 操作：运行 `{baseDir}/scripts/dlt.py review <期号> <前1>...<前5> <后1> <后2>`
- 结果：命中情况 + 预测存档对比

## 数据存储

| 文件 | 内容 |
|------|------|
| `~/.dlt_data/history.json` | 全量历史开奖数据 |
| `~/.dlt_data/latest_stats.json` | 最近一次统计结果 |
| `~/.dlt_data/predictions.json` | 预测存档 + 复盘记录 |

## 数据源

| 来源 | URL | 用途 |
|------|-----|------|
| 体彩官方API | `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85` | 唯一数据源，GET 请求，无需 Cookie |

废弃数据源（永远不要再使用）：500.com（已停更）

## 故障处理

| 症状 | 解决 |
|------|------|
| 缺少依赖 | `pip install requests beautifulsoup4` |
| 无本地数据 | 先运行 `dlt.py fetch` |
| FETCH_FAILED | 检查网络连接，稍后重试 `fetch` |
