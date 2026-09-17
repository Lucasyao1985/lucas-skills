---
name: reddit-deal-closer
description: >
  Scan Reddit for people actively hiring developers to build custom AI tools, Claude Code skills,
  browser automation scripts, Discord/Telegram bots, n8n workflows, or custom integrations.
  Find leads who posted "looking for a developer", "willing to pay for a bot", "need someone to build",
  or "is there a tool that…" (unmet need → custom build opportunity).
  Full sales funnel: discover → qualify (budget/urgency/fit) → draft outreach → propose → close.

  找什么人：在 Reddit 上主动发帖找开发者/求工具/有预算的个人和企业
  接什么单：定制 Claude Code Skill、AI Agent 工作流、浏览器自动化、Discord Bot、n8n 工作流
  怎么获客：搜 Reddit 雇佣帖/付费信号/工具求购帖 → 评分筛选 → 草拟英文沟通 → 报价成交

  触发条件（任一命中）：
  - 用户想在 Reddit 上找**付费开发**的机会（定制 skill / automation / bot / 脚本）
  - 用户说"Reddit 有没有人要定制开发"、"帮我找需要开发 AI 工具的 Reddit 帖子"
  - 用户说"扫描 Reddit 外包需求"、"Reddit 扫单"、"Reddit 找开发项目"
  - 用户说"scan Reddit for dev gigs"、"find Reddit posts hiring developers"
  - 用户说"Reddit bot commissions"、"find people who need custom tools built on Reddit"
  - 用户说"Reddit 有人愿意花钱做 automation 吗"、"Reddit 接海外外包"
  - 用户说"帮我在 Reddit 上找付费做 skill 的客户"

  不触发（用其他 skill）：
  - 帮某个**具体产品**找种子用户 → reddit-seed-user-research
  - 普通 Reddit 搜索浏览 → 不需要 skill
  - LinkedIn 找工作 / BOSS直聘找工作 → linkedin-jobs / zhipin
trigger: |
  触发关键词（任一命中即触发）：
  - Reddit + 定制开发/定制skill/定制工具/外包/找人开发/付费开发
  - Reddit + 扫单/找项目/接外包/开发需求/雇佣帖
  - Reddit + 有没有人要/AI工具开发/自动化开发/bot开发
  - scan Reddit for + dev gigs/custom tools/hiring developers
  - Reddit + bot commissions/custom AI tools/automation gigs
  - find people on Reddit who need + custom built/developer hired/automation made
  - /reddit-deal-closer
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: [node, npx]
      npm: [playwright]
    os: [win32]
---

# /reddit-deal-closer — Reddit 开发需求扫描 + 付费客户成交

## 一句话概述

**找什么人**：在 Reddit 上主动发帖雇佣开发者、求购定制工具、有明确预算的海外客户
**接什么单**：Claude Code Skill、AI Agent 工作流、浏览器自动化、Discord/Telegram Bot、n8n 集成
**怎么获客**：搜索 Reddit 雇佣帖/付费信号/痛点需求 → 评分甄别 → 草拟英文沟通 → 报价 → 成交

全漏斗：`发现线索 → 甄别评分 → 草拟沟通 → 报价谈判 → 成交跟踪`

## 🚫 硬性规则：零用户交互

**从触发到输出报告，全程不询问用户任何问题。**

- 不要用 AskUserQuestion
- 不要停下来等用户确认
- 不要问"要不要"、"是不是"、"想不想"
- 不要分多轮对话
- 所有决策自动执行，结果一次性输出
- 唯一允许的用户交互：用户主动修改 portfolio.md 或 pipeline.md

## ⚠️ 交互原则

**零询问，全自动执行。**

- ❌ **永远不要用 AskUserQuestion**
- ❌ 不要问"今天扫哪个方向" → 用户没说就全渠道
- ❌ 不要问"要不要追这个 Warm lead" → 自动草拟
- ❌ 不要问"portfolio.md 要更新吗" → 用户主动说才更新
- ❌ 不要问任何问题，不要停下来等回复
- ✅ portfolio.md 不存在 → 读取现有文件自动推断，创建占位版本，继续执行
- ✅ 所有中间决策自动执行，结果放在报告里

## 与 reddit-seed-user-research 的区别

| | reddit-seed-user-research | reddit-deal-closer (本 skill) |
|---|---|---|
| **目的** | 推广一个**具体产品**，找种子用户 | 销售**定制开发服务**，找付费客户 |
| **搜索词** | 产品相关痛点和替代品 | 雇佣信号、预算信号、定制需求 |
| **输出** | 产品推荐回复 + 品牌洞察 | 销售沟通草稿 + 报价 + 线索漏斗 |
| **成果** | 产品用户增长 | **美元收入** |

## 工具清单

**核心搜索方式：Playwright 浏览器自动化（必须）**

Reddit 封锁了 WebFetch 和非浏览器请求，搜索引擎也无法有效索引 Reddit 雇佣帖。因此本 skill **必须**使用 Playwright 浏览器来访问 Reddit。

- **Playwright + Chrome**: 启动浏览器，加载用户的 Reddit cookie，直接访问 Reddit 搜索/子版页面
- **Bash**: 运行 Playwright 脚本（`npx playwright ...`），创建目录/文件
- **WebSearch**: 仅作辅助——偶尔能搜到 Reddit 帖子，但**不可作为主要搜索方式**
- **WebFetch**: 仅在 Playwright 不可用时尝试（大概率会被 Reddit 封锁）
- **Edit/Write**: 创建和更新 portfolio.md、pipeline.md、报告

**依赖：** `playwright` (npm) — 已在 zhipin skill 中安装，可复用。

---

## Phase 0: 前置检查

每次运行时，先检查以下文件：

### 0.1 portfolio.md — 服务能力档案

检查 `C:\Users\Lucas\.claude\skills\reddit-deal-closer\portfolio.md` 是否存在。

**如果不存在**，从该 skill 目录下的其他文件推断能力信息（references/ 目录、search.js 中的技术栈、pipeline.md 中的历史），自动创建 portfolio.md，然后继续执行。

**永远不要停下来问用户。直接创建，直接继续。**

### 0.2 cookies.txt — Reddit 认证

检查 `cookies.txt` 是否存在。

- **存在** → 继续，不询问
- **不存在** → **一行提示，不阻塞**：`💡 cookies.txt 缺失，无 cookie 模式下部分 subreddit 内容不可见。建议后续导出。` 然后直接进入 Phase 1。

**永远不要停下来等用户配置 cookie。**

---

## Phase 1: 线索发现 (Lead Discovery) — 多渠道扫描

### ⚠️ 为什么必须用 Playwright

实测结论：
- `WebSearch` → Reddit 雇佣帖几乎不出现在搜索结果中（被 SEO 淹没）
- `WebFetch` → Reddit 直接封锁非浏览器请求
- **唯一可靠方式：Playwright 启动 headless Chrome → 访问 old.reddit.com 搜索 → 提取帖子**

### 1.1 Cookie 检查

搜索前确认 `cookies.txt` 存在。缺失时仍可无登录扫描，但部分 subreddit 和完整帖子内容不可见。

### 1.2 五大获客渠道 (31 个 subreddit)

**不要只扫 r/forhire！** Reddit 上找到付费开发客户至少有 5 条渠道：

| 渠道 | Tier | 板块数 | 意图级别 | 典型线索 |
|------|------|--------|----------|----------|
| 🥇 **雇佣市场** | 1 | 8 个 | 🔥最高 — 明确 [HIRING] | r/forhire, r/hiring, r/remotejs, r/jobbit, r/Jobs4Bitcoins |
| 🥈 **技术社区** | 2 | 9 个 | ⚠️中 — 讨论中隐藏招聘 | r/ClaudeAI, r/Python, r/webdev, r/reactjs, r/Programming |
| 🥉 **Bot/自动化** | 3 | 6 个 | 🔥高 — 直接求开发 | r/Discord_Bots, r/n8n, r/automation, r/TelegramBots |
| 4️⃣ **SaaS/创业** | 4 | 5 个 | ⚠️需转化 — 找外包/合伙人 | r/SaaS, r/startups, r/Entrepreneur, r/indiehackers |
| 5️⃣ **AI/Agent** | 5 | 3 个 | 💡教育型 — 展示专业度引流 | r/AI_Agents, r/LangChain, r/OpenAI |

**完整的 31 个 subreddit 和搜索关键词硬编码在 `search.js` 的 TARGETS 对象中。**

### 1.3 执行搜索

```powershell
cd "C:\Users\Lucas\.claude\skills\reddit-deal-closer"
set NODE_PATH=C:\Users\Lucas\.claude\skills\zhipin\node_modules

# 全量扫描 (所有 31 个板块，耗时长)
node search.js all --limit 50 --min-score=25

# 按需扫特定板块（推荐）
node search.js r/forhire --limit 15 --min-score=25
node search.js r/hiring --limit 10 --min-score=25
node search.js r/SaaS --limit 10 --min-score=25
node search.js r/Discord_Bots --limit 10 --min-score=15
node search.js r/AI_Agents --limit 10 --min-score=20
```

脚本输出 JSON 帖子列表到 stdout，每条含 `_relevance` (相关性 0-100)、`_trust` (可信度 0-100)、`_trustFlags` (具体标记)。

### 1.4 自动过滤管道

search.js 内置 3 层过滤，依次执行：

**第 1 层 — shouldSkip() 硬过滤：**
- ❌ `[For Hire]` / `[Offer]` — 开发者在卖服务，不是你客户
- ❌ "No gen AI please" / "no AI code" — 明确排斥 AI 工具
- ❌ "free please" / "no budget" / "do this for free" — 无付费意愿
- ❌ 作者已删除 (u/[deleted])

**第 2 层 — relevanceScore() 相关性 0-100：**
- +25: developer, engineer, python, automation, bot, Claude, scraper...
- +15: software, SaaS, cloud, ML, mobile app...
- +8~15: 预算信号 `$X`, "budget", "rate", "salary"
- -50: 标题含 designer, video editor, writer, attorney, marketing... (非开发岗)
- -30: "script" 搭配 video/voice/actor 上下文 → 判断为视频脚本非编程

**第 3 层 — trustScore() 可信度 0-100：**
- 🚩 -40: Google Forms / Typeform 链接 (钓鱼)
- 🚩 -25: `.pages.dev` / `.netlify.app` 等免费域名 (仿冒)
- 🚩 -15: Telegram/WhatsApp 唯一联系方式
- 🚩 -10: 仅 DM 无公司信息
- ✅ +15: 有公司名 / 有网站
- ✅ +10: 需求详细 / 有技术栈 / 有预算 / 社区互动 >5 评论

**--min-score=N** 参数控制相关性门槛。推荐：Tier 1/2 用 25，Tier 3 用 15，Tier 4/5 用 20。

### 1.5 快捷模式（按用户意图选渠道）

用户说特定方向时，跳过全面扫描，直接聚焦：
- "找 Claude skill 客户" → r/ClaudeAI + r/ClaudeCode + r/forhire
- "找 bot 开发" → r/Discord_Bots + r/TelegramBots + r/forhire
- "找自动化外包" → r/automation + r/n8n + r/SaaS
- "找 web 外包" → r/forhire + r/webdev + r/SaaS
- "找 AI agent 客户" → r/AI_Agents + r/LangChain + r/ClaudeAI

**用户没说方向时，不要问，直接用全渠道扫描（`node search.js all`）。**

---

## Phase 2: 线索评分 (Lead Qualification)

### 2.1 评分矩阵

对每条线索打分，满分 100。每维度独立评分后加权求和。

| 维度 | 权重 | 30 分 | 20 分 | 10 分 | 5 分 | 0 分 | -10 分 |
|------|------|-------|-------|-------|------|------|--------|
| **预算信号** | 30% | 明确金额 "$X" / "budget $X" | 提及付费 "paid" "commission" "$$" | 暗示预算 "budget" "rate" | — | 无任何付费信号 | 期望免费 "free" "no budget" |
| **紧急程度** | 20% | — | 7天以内 + OP 在评论区活跃 | 7-30天 | 30-90天 | 90天以上 | 帖子已存档/锁定 |
| **范围匹配** | 25% | — | 定制 bot/脚本/自动化/skill | Web 全栈/MVP/工具 | 集成/API/工作流 | 一般技术帮助 | 与用户能力完全不匹配 |
| **需求详度** | 10% | — | — | 有清晰需求描述/技术规格 | 模糊但有方向 | 一句话/没细节 | "谁帮我做" 低质量 |
| **决策权** | 10% | — | — | 企业主/创始人/公司需求 | 独立开发者/个人项目 | 学生/Agent/中间人 | — |
| **Subreddit** | 5% | — | — | r/forhire r/ClaudeAI | r/slavelabour r/Discord_Bots | 通用 subreddit | 明确禁止 solicitation |

**评分示例：**

```
线索: "Willing to pay $200-300 for a Discord moderation bot"
  - 预算信号: 30 × (30/30) = 30 (明确报价 $200-300)
  - 紧急程度: 20 × (20/20) = 20 (2天前发布, OP在回复)
  - 范围匹配: 25 × (20/25) = 20 (Discord bot — 定制开发，非常匹配)
  - 需求详度: 10 × (10/10) = 10 (3段详细需求)
  - 决策权:   10 × (8/10)  = 8  (独立游戏开发者)
  - Subreddit: 5 × (4/5)   = 4  (r/Discord_Bots)
  总分: 92/100 (Hot Lead 🔥)
```

### 2.2 线索分级

| 标签 | 分数 | 含义 | 行动 |
|------|------|------|------|
| 🔥 **Hot** | ≥70 | 高预算信号 + 匹配 + 近期 | 立即草拟回复，优先处理 |
| 🌤️ **Warm** | 40-69 | 有潜力但缺关键信息 | 自动草拟回复，附在报告中供用户选择 |
| ❄️ **Cold** | <40 | 兴趣低或信息不足 | 记录到 pipeline，等更多信号 |
| 👀 **Monitor** | 不限 | 有学习价值的帖子模式 | 不回复，记录关键词/模式 |
| ⛔ **Skip** | 不限 | 明确不匹配、垃圾、违规 | 跳过不记录 |

**不要停下来问"是否要追 Warm leads"。** 自动草拟，放在报告里，用户自己决定。

### 2.3 输出格式（含双评分）

每条线索按以下格式输出给用户：

```
🔥 Hot Lead #1 — 📊 92/100 🛡️ 90/100
📌 r/forhire | 2 days ago | OP: u/username
🔗 https://www.reddit.com/r/forhire/comments/xxxxx
💰 Budget: $200-300 (explicit in post)
📋 Need: Custom Discord moderation bot with auto-role, welcome messages, spam filter
🏷️ Trust: COMPANY TECH_STACK BUDGET ENGAGED

中文速览：Discord 自动管理 bot，预算明确 $200-300，需求详细。高度匹配，可信度高。

评分明细：
  📊 相关性: 92/100 | 🛡️ 可信度: 90/100
```

**双评分说明：**
- 📊 **相关性** (relevance)：这个帖子有多匹配你的开发技能（自动化/bot/AI > web 全栈 > 测试 > 不匹配）
- 🛡️ **可信度** (trust)：这个帖子有多大概率是真的（公司名+网站+预算+互动 vs Google Forms+Telegram+免费域名）
- 🏷️ **Trust Flags**：可信度标记，绿色是正面信号，红色是红旗🚩

---

## Phase 3: 草拟沟通 (Draft Outreach)

### 3.1 回复原则

**黄金法则：先给价值，再谈交易。**
- 引用帖子具体内容（证明你不是群发）
- 展示专业度（提类似案例）
- 温和试探预算（不要一上来报价）
- 给低门槛的下一步（"DM 聊"、"Discord 5分钟"）
- 60-150 词，像人写的，不像模板

**禁止：**
- ❌ "I can build this for you" 开头的冷推销
- ❌ 过度承诺（"I'm the best developer"）
- ❌ 不披露身份（假装是路人推荐）
- ❌ 在明确求免费的帖子下推销
- ❌ 在 r/forhire 等有格式要求的 subreddit 不遵守格式
- ❌ 群发同一模板到多个帖子

### 3.2 模板选择

根据线索所在的销售阶段选择模板。模板详情见 [references/message-templates.md](references/message-templates.md)。

| 阶段 | 使用模板 | 目标 |
|------|----------|------|
| Hot Lead 初次接触 | **初接触 (Initial Outreach)** | 建立对话，展示专业度，问预算 |
| 3-5天无回复 | **跟进 (Follow-Up)** | 轻量提醒，提供额外价值 |
| 客户回复、范围明确 | **报价 (Proposal)** | 正式报价，复述范围，明确交付 |
| 客户说贵 | **谈判 A (Scope Adjustment)** | 降价不降质，给两个选项 |
| 客户嫌贵要找别人 | **谈判 B (Value Differentiation)** | 区分价值，问真实预算 |
| 客户接受报价 | **成交 (Closing)** | 收定金，开动，给第一个里程碑 |
| 项目已交付 | **交付后 (Post-Delivery)** | 维护提醒、referral、upsell |

### 3.3 草稿输出格式

每条回复草稿输出：

```markdown
### 回复草稿 — [Thread Title]

**适用模板:** 初接触
**中文策略：** [为什么用这个模板，想达到什么效果，回复的关键策略点]

**英文草稿（复制到 Reddit）：**
---
[英文回复正文，带 {VARIABLE} 占位符，用户填好后复制]
---

**中文翻译/说明：**
[每段的中文翻译或意图说明]
```

---

## Phase 4: 线索跟踪 (Pipeline Management)

### 4.1 销售阶段

```
Discovered → Qualified → Contacted → Engaged → Proposed → Negotiating → Won/Lost
                                                                       ↳ Stale (no reply)
```

| 阶段 | 含义 | 用户需要做什么 |
|------|------|---------------|
| **Discovered** | 搜索发现，尚未评分 | — |
| **Qualified** | 已评分 (Hot/Warm)，待用户审核 | 用户审阅线索，决定是否联系 |
| **Contacted** | 已发送初接触消息 | 用户在 Reddit 上发消息 |
| **Engaged** | 客户回复，对话进行中 | 用户告知进展 |
| **Proposed** | 已发送正式报价 | 用户在 Reddit/DM 中发报价 |
| **Negotiating** | 在谈判价格/范围 | 用户告知谈判进展 |
| **Won** 🏆 | 成交！已收定金 | 开始开发！ |
| **Lost** ❌ | 丢单 | 记录丢单原因 |
| **Stale** ⏰ | 2次跟进无回复 | 归档或放弃 |

### 4.2 更新 pipeline.md

每次运行结束时更新 `deals/pipeline.md`：
- 新增发现的线索（Discovered → Qualified）
- 更新已联系线索的状态（根据用户反馈）
- 标记需跟进的线索（Contacted 超过 5 天 → 提醒用户跟进）
- 更新 Won/Lost 记录

---

## Phase 5: 输出与报告 (Output)

### 5.1 每次运行输出

运行结束时输出多渠道汇总：

```
## 📊 本轮 Reddit 客户扫描总结

**扫描时间:** 2026-05-31 15:30
**覆盖渠道:**
  🥇 雇佣市场: r/forhire(8), r/hiring(7) = 15 条
  🥈 技术社区: r/ClaudeAI(22) = 22 条
  🥉 Bot/自动化: r/Discord_Bots(15) = 15 条
  4️⃣ SaaS/创业: r/SaaS(15), r/startups(13) = 28 条
  5️⃣ AI/Agent: r/AI_Agents(18) = 18 条

### 线索统计 (合并去重)
- 🔥 Hot Leads (📊≥70): N 个
- 🌤️ Warm Leads (📊40-69): N 个
- ❄️ Cold Leads (📊<40): N 个
- 🚩 红旗线索 (🛡️<50): N 个

### 活跃漏斗
- 待联系: N
- 已联系等待回复: N
- 进行中: N (est. $XXX)
- 本月已成交: N (实际 $XXX)

### 推荐今日行动
1. [最高优先] — 📊92 🛡️90 — [线索名] — [为什么]
2. [第二优先] — 📊63 🛡️90 — [线索名] — [为什么]
3. [跟进提醒] — [线索名] — [已等N天]

中文速览：[用中文总结本轮扫描的关键发现和推荐行动]
```

### 5.2 首次使用：创建文件

首次运行时自动创建（不询问用户）：
- `portfolio.md`（从现有文件推断能力信息，自动生成）
- `deals/pipeline.md`（初始化空跟踪表）

---

## Cookie 认证详解

### 格式

文件：`cookies.txt` 在 skill 目录
格式：每行一个 `name=value`

```
reddit_session=eyJ...your_session_token
csrf_token=7c7d392c8a48c70b16cf7fb229dadf77
```

### 导出方法

1. Chrome 登录 Reddit → F12
2. Application → Storage → Cookies → `https://www.reddit.com`
3. 找到 `reddit_session`（或 `token_v2`）和 `csrf_token`
4. 复制 Value 列
5. 写入 `cookies.txt`：`name=value`，每行一个

### 使用方式

WebFetch 时带 Cookie 头：
```
Cookie: reddit_session=xxx; csrf_token=yyy
```

### 安全

- ✅ 仅用于 WebFetch **读取**操作
- ✅ cookies.txt 在 .gitignore 中排除
- ❌ 永不用于 POST/投票/发帖
- ❌ 永不出现在报告或输出中
- ⚠️ Cookie 有效期 ~1年，失效后需重新导出

---

## 安全与声誉规则

1. **永不自动发帖**。所有消息是草稿，用户审核后手动发布。
2. **披露身份**。提及"我提供服务"时不隐藏。
3. **不群发**。每条回复针对具体帖子定制。
4. **遵守 subreddit 规则**：
   - r/forhire: 必须用 `[For Hire]` 标签，某些要求写明 rate
   - r/slavelabour: 最低 $5，明确标价
   - r/ClaudeAI: 禁止纯推销，必须是技术讨论
   - 各 subreddit 的 sidebar/wiki 规则优先
5. **不伪装身份**。不用马甲号、不假装路人。
6. **不在求免费帮助的帖子下推销**。如果帖子明确求免费帮助且无预算信号，跳过。
7. **交易安全**：建议用 PayPal Goods & Services（有 buyer protection）建立信任，或 Wise（费率低）。首次合作建议收 50% 定金。

---

## 使用场景示例

### 场景 1: 首次使用

```
用户: Reddit找客户
Skill: 
  → Phase 0: 发现没有 portfolio.md
  → 自动从 references/ 和 search.js 推断能力，创建 portfolio.md
  → cookies.txt 缺失？一行提示，不阻塞
  → 直接进入 Phase 1 搜索
```

### 场景 2: 日常扫单

```
用户: 帮我在Reddit上看看有没有人要定制skill
Skill:
  → Phase 0: portfolio.md 和 cookies.txt 都存在 ✓（无询问）
  → Phase 1: 用户没说方向 → 直接全渠道扫描
  → 执行: node search.js all --limit 50 --min-score=25
  → 脚本输出 JSON，合并去重
  → Phase 2: 评分，每条带 📊相关性 + 🛡️可信度
  → 发现 5 Hot + 8 Warm + 1 红旗(Google Form)
  → Phase 3: 为 3 Hot + 5 Warm 草拟回复（自动，不问用户）
  → Phase 4: 更新 pipeline.md
  → Phase 5: 多渠道总结输出
```

### 场景 3: 定向搜索

```
用户: 帮我找需要定制 Discord bot 的客户
Skill:
  → Phase 1: 聚焦 Tier 3 (Bot/自动化)
  → node search.js r/Discord_Bots --limit 15 --min-score=15
  → node search.js r/TelegramBots --limit 10
  → 输出 bot 开发需求列表 + 可信度标记
```

### 场景 3: 跟进提醒

```
用户: 帮我看看之前联系的客户有没有需要跟进的
Skill:
  → Phase 0: 检查文件 ✓
  → Phase 4: 读取 pipeline.md
  → 发现 2 个 Contacted 超过 5 天 → 自动草拟跟进消息
  → 检查是否有 Stale → 自动标记归档
  → 输出报告，不询问用户
```

---

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `search.js` 报错 "Cannot find module 'playwright'" | playwright 未安装 | `cd C:\Users\Lucas\.claude\skills\zhipin && npm install playwright` (复用 zhipin 的 node_modules) |
| Playwright 启动 Chromium 失败 | Chromium 未下载 | `npx playwright install chromium` |
| search.js 返回 0 结果 | Cookie 过期或 subreddit 无匹配 | 检查 cookies.txt 是否最新；尝试手动访问 Reddit 确认登录态 |
| 所有帖子被跳过 | 过滤规则太严格 | 检查 search.js 中 shouldSkip() 逻辑 |
| 大部分线索是 Cold | 目标 subreddit 不对 | 优先 r/forhire + r/ClaudeAI + r/Discord_Bots |
| 回复后无回音 | 消息太像模板、太推销 | 缩短消息，更个性化，只给价值不推销 |
| Cookie 过期 | Reddit session 到期 | 重新从 Chrome 导出 cookies.txt |
| pipeline.md 找不到 | 首次使用还没创建 | Phase 0 自动创建 |

---

## 可重复使用

本 skill 设计为可重复运行：
1. `portfolio.md` 保存能力档案（一次创建，长期维护）
2. `deals/pipeline.md` 保存线索漏斗（持续更新）
3. 每次运行发现新线索，更新旧线索状态
4. 历史报告可追溯

在相同时段（如每周一次）运行可保持线索漏斗健康。
