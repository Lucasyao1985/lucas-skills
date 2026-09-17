---
name: x-post-analyzer
description: Fetch and analyze X/Twitter post content including text, media, quotes, engagement data, and replies. Use when user shares an X/Twitter link, asks to "analyze a tweet", "what does this post say", or provides x.com/twitter.com URLs. Outputs structured Chinese analysis report.
metadata:
  author: Lucas
  version: 1.1.0
  input: X/Twitter URL
  output: Chinese analysis report
compatibility: 需要网络访问；依赖 WebFetch/WebSearch 工具与 fxtwitter API（https://api.fxtwitter.com）。
---

# X/Twitter 帖子分析器

自动获取并分析 X（Twitter）帖子内容，输出结构化中文报告。

## 使用方式

用户提供 X/Twitter 链接时自动触发，或用户明确要求分析推文时使用。

**示例触发语句：**
- "帮我看看这个推文 https://x.com/user/status/123"
- "分析这条推文的内容"
- "这个 X 帖子说了什么？"

## 工作流程

**优先使用内置 Workflow 脚本**：环境支持时直接运行
`scripts/x-post-workflow.js`（参数：X/Twitter URL）——它实现了下面的
Step 1-3 全流程（fetch 阶段 1 个 Agent 顺序回退 + 纯文本分析 Agent）。

无法运行 Workflow 脚本时，按以下步骤手动执行：

### Step 1: 解析 URL
从用户输入中提取 X/Twitter URL，识别用户名和帖子 ID。

### Step 2: 获取内容（单 Agent 顺序回退）
使用 1 个 Agent 按优先级依次尝试：
1. fxtwitter API（一次调用获取全部数据，成功率最高）
2. WebSearch（API 失败时搜索缓存）
3. 直接访问 x.com（最后手段，常被拦截）

### Step 3: 综合分析
使用纯文本 Agent（不调用任何工具）生成结构化中文报告。

### 权限优化
- 总工具调用次数：1-3 次（旧版 10+ 次）
- 分析阶段零工具调用，不触发权限弹窗
- 优先使用 fxtwitter API 减少域名访问

## 输出报告格式

### 基本信息
- 发帖人、发帖时间、发帖设备、用户简介、粉丝数、认证状态

### 帖子内容
- 原文 + 中文翻译

### 媒体附件
- 图片/视频描述和技术参数

### 引用推文
- 被引用内容（如有）

### 互动数据
- 浏览量、点赞、转发、回复、引用数

### 评论区要点
- 热门回复和讨论方向

### 主题分析
- 核心观点、文化背景、语言特征

### 传播情况
- 传播范围和影响力评估

## 错误处理

- 帖子已删除：尝试获取缓存内容
- 私密账号：提供公开可见信息
- 访问受限：自动切换回退方案
- 所有方式失败：诚实报告，建议用户直接访问

## 参考文档

- `references/fetch-strategies.md` — 抓取策略详解
- `references/report-template.md` — 报告模板
