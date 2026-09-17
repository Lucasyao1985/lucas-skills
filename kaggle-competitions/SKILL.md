---
name: kaggle-competitions
description: >
  Kaggle竞赛分析与参赛规划助手。查询当前活跃竞赛、按技术领域分类、评估竞赛价值、制定参赛策略。
  触发条件（任一命中）：
  - 用户提到"kaggle竞赛"、"kaggle比赛"、"kaggle competition"、"Kaggle赛事"
  - 用户问"有什么竞赛可以参加"、"现在有什么比赛"、"推荐参加什么竞赛"
  - 用户提到具体竞赛名称如ARC Prize、BirdCLEF、Playground Series、AIMO
  - 用户想了解竞赛奖金、截止时间、报名、组队
  - 用户问"kaggle刷牌"、"kaggle等级"、"kaggle grandmaster"
  - 用户想根据职业目标（ML Engineer/Research/Quant/Agent Dev）选择竞赛
  - 用户问AI/ML相关的比赛、黑客马拉松、hackathon
  不触发：一般机器学习问题、kaggle数据集使用（非竞赛）、纯模型训练问题。
user-invocable: true
metadata:
  author: Lucas
  version: 1.1.0
compatibility: 需要读取 references/competitions-2026.md（内置竞赛数据库）；
  刷新数据时需要网络与 WebSearch/WebFetch 工具。
---

# /kaggle-competitions — Kaggle 竞赛分析与参赛规划

## 触发决策树

```
用户提到竞赛/比赛/参赛
├── 明确说"kaggle" → 本skill
├── 说"AI竞赛"、"ML比赛"、"hackathon" → 本skill
├── 提到具体竞赛名(ARC Prize/BirdCLEF/Playground) → 本skill
├── 问"参加什么比赛好"、"推荐竞赛" → 本skill
├── 问"kaggle数据集"、"kaggle notebook"（非竞赛） → 不触发
├── 问一般ML/DL问题 → 不触发
└── 模糊 → 看上下文是否有竞赛意图
```

## 执行流程

收到用户请求后，严格按以下步骤执行：

### 第 1 步：判断用户意图

从用户输入中识别以下意图类型：

| 意图 | 关键词示例 | 执行动作 |
|------|-----------|----------|
| 全景概览 | "有哪些竞赛"、"当前比赛"、"推荐参加什么" | → 第 2 步：加载参考数据，输出分类概览 |
| 领域筛选 | "LLM竞赛"、"CV比赛"、"量化比赛"、"AGI竞赛" | → 第 3 步：按领域过滤并排序 |
| 竞赛详情 | 具体竞赛名称 | → 第 4 步：输出单个竞赛详情 |
| 职业规划 | "ML Engineer参加什么"、"求职"、"简历" | → 第 5 步：按职业目标推荐 |
| 时间紧迫 | "快截止的"、"还能报名的"、"30天内" | → 第 6 步：按截止时间排序 |
| 奖金排序 | "奖金最高"、"最值钱"、"奖金排名" | → 第 7 步：按奖金排序 |
| 参赛策略 | "怎么准备"、"组队"、"参赛建议" | → 第 8 步：输出策略建议 |

### 第 2 步：加载参考数据

```
读取 references/competitions-2026.md 获取最新竞赛数据库
```

数据文件包含：
- 所有活跃竞赛的结构化信息
- 技术领域分类
- 综合推荐指数（1~10）
- 价值评估维度（求职/简历/Agent/LLM/RL/科研/商业）
- 优先参赛路线图

### 第 3 步：按领域筛选输出

支持的技术领域：
- 🧠 LLM 与 AI Agent
- 🤖 推理与 AGI
- 🖼️ 计算机视觉
- 🎵 语音与音频
- 💊 生物医药与健康
- 📈 金融量化
- 🔬 科学计算
- ⚽ 数据科学与预测建模

输出格式：表格，包含竞赛名称、奖金、截止时间、推荐指数、推荐理由。

### 第 4 步：竞赛详情输出

对单个竞赛，输出：
1. 基本信息（名称、主办方、奖金、截止、团队限制）
2. 技术方向与任务描述
3. 关键约束（如有）
4. 价值评估雷达图（7维度1~10分）
5. 综合推荐指数与理由
6. 参赛建议（如何准备、技术栈建议）

### 第 5 步：按职业目标推荐

根据用户职业方向，推荐对应的竞赛组合：

**ML Engineer 路线：**
- 重点：LMM工程实战 + Tabular基础 + 多模态经验
- 核心竞赛：Gemma 4 Good + Playground Series + BirdCLEF

**Research Scientist 路线：**
- 重点：AGI推理研究 + 数学AI + 跨学科
- 核心竞赛：ARC Prize（三赛道） + AIMO + AI Cup

**AI Agent Developer 路线：**
- 重点：流体智能 + 边缘部署 + Pipeline实战
- 核心竞赛：ARC Prize AGI-3 + Gemma 4 + Playground

**Quant 路线：**
- 重点：金融ML + 推理能力 + Tabular处理
- 核心竞赛：Hull Tactical + ARC Prize + Playground

### 第 6 步：按截止时间排序

输出格式：
```
🔴 P0（0~7天）：立即行动
🟡 P1（7~30天）：短期冲刺
🟢 P2（1~3个月）：中期规划
⚪ P3（3个月+）：长线布局
```

每个竞赛附带：剩余天数、奖金、紧急行动建议。

### 第 7 步：按奖金排序

输出 Top 10 奖金排行榜，附带总奖金池统计。

### 第 8 步：参赛策略输出

根据用户具体问题，提供：
- 竞赛配对建议（同时参加可最大化收益的组合）
- 时间分配建议
- 技术准备清单
- Kaggle 等级提升路径

## 输出格式规范

### 概览表格
```markdown
| 排名 | 竞赛名称 | 奖金 | 截止时间 | 推荐指数 | 状态 |
```

### 价值评估
```markdown
| 维度 | 评分 | 说明 |
|------|------|------|
| 求职竞争力 | ⭐⭐⭐⭐⭐ | ... |
| 简历含金量 | ⭐⭐⭐⭐ | ... |
| AI Agent能力 | ⭐⭐⭐ | ... |
| LLM工程能力 | ⭐⭐⭐⭐⭐ | ... |
| 强化学习 | ⭐⭐ | ... |
| 科研价值 | ⭐⭐⭐⭐ | ... |
| 商业化价值 | ⭐⭐⭐⭐ | ... |
```

### 路线图格式
```markdown
### 🚨 第一梯队：立即行动（0~7天）
| 优先 | 竞赛 | 奖金 | 截止 | 行动建议 |
```

## 数据更新策略

参考数据文件 `references/competitions-2026.md` 基于 2026年5月 的公开信息。
如用户需要最新数据，执行以下步骤：
1. 用 WebSearch 搜索 "kaggle competitions 2026 active"
2. 用 WebFetch 访问 https://www.kaggle.com/competitions?listOption=active
3. 补充搜索具体竞赛名获取详情
4. 更新参考数据文件

> **注意：** Kaggle 网站为纯 JavaScript 渲染 SPA，WebFetch 可能无法获取完整数据。
> 此时建议用户直接访问 https://www.kaggle.com/competitions?listOption=active

## 关键约束提醒

当用户询问 ARC Prize 时，必须强调：
- 评估期间**禁止联网**
- **禁止使用 API 模型**（GPT、Claude 等）
- 必须**本地运行**
- 必须**开源所有代码**（CC0 或 MIT-0 许可证）
- 所有方案必须附带 **Solution Writeup**

当用户询问 Playground Series 时，说明：
- 无现金奖金，仅 Kaggle 周边商品
- 但对 Kaggle 等级（Expert → Master → Grandmaster）至关重要
- 每月一个，是最佳练手/刷牌途径

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 竞赛数据过期 | 参考数据非实时 | 按"数据更新策略"刷新 |
| 用户要找的竞赛不在列表中 | 竞赛太新或已结束 | 用 WebSearch 搜索确认 |
| Kaggle页面无法抓取 | JS渲染SPA | 建议用户浏览器直接访问 |
| 用户不知道选哪个 | 意图不明确 | 询问职业目标和技术背景 |

## 注意事项

- 竞赛截止时间可能随时调整，以 Kaggle 官方页面为准
- 部分竞赛的奖金和团队限制未能确认，标注"待确认"
- 不编造不存在的竞赛数据，无法确认时明确告知用户
- 推荐指数基于多维度综合评估，仅供参考
