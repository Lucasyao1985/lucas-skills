# Message Templates — Reddit 销售话术模板

每个模板含英文正文（`{VARIABLE}` 占位符，用户填好后可直接复制到 Reddit）、中文策略说明、适用时机、及红旗警告。

---

## 模板 1: 初接触 (Initial Outreach)

**适用:** Hot Lead，第一次联系
**目标:** 建立对话，展示专业度，温和试探预算
**长度:** 60-120 词

### 英文模板 A — 对方明确说了需要什么

```
Hey! I saw your post in r/{SUBREDDIT} about needing {BRIEF_NEED_SUMMARY}.

I build custom {TOOL_TYPE} for clients — I've done similar projects like {EXAMPLE_1} (a {DESCRIPTION_1}) and {EXAMPLE_2} (a {DESCRIPTION_2}).

For what you described, the approach would be {TECH_APPROACH_ONE_LINER}. Happy to walk through how I'd scope it if you're interested.

Quick question — do you have a rough budget range in mind for this? If you're still looking for someone, I can put together a short proposal.

Feel free to DM me here or on Discord: {DISCORD_HANDLE}
```

### 英文模板 B — 对方在问"有没有这样的工具"（潜在定制机会）

```
Hey! Came across your post looking for a tool that {PROBLEM_DESCRIPTION}.

Just wanted to mention — if you can't find an existing tool that does exactly this, you could have a custom {TOOL_TYPE} built for around ${PRICE_RANGE}. I've built similar things for clients where off-the-shelf tools didn't fit their workflow.

For example, I built {EXAMPLE} that {VALUE_PROPOSITION}.

Not trying to sell you anything — just putting the option out there since I see this gap come up a lot. If you want to explore what a custom build would look like, happy to chat.

Either way, hope you find what you're looking for!
```

### 中文策略说明

核心策略：**先展示你懂他在说什么 → 证明你做过类似的 → 温和问预算 → 给低门槛下一步。**

- 引用具体帖子内容是最关键的一步——证明你不是群发
- `{EXAMPLE_1}` 和 `{EXAMPLE_2}` 要从 portfolio.md 中选最相关的
- 不要一上来就报价。先建立对话，了解完整需求后再报价
- "DM me" 比 "check out my website" 更自然、更低门槛
- 不做 hard sell——"Not trying to sell you anything" 降低防御

### 红旗警告
- ❌ 不要用在 r/forhire —— 那里有特定格式要求，用模板 1-C
- ❌ 不要在求免费帮助的帖子用 —— 跳过或只给技术建议
- ❌ 不要不引用帖子具体内容就群发

### 模板 1-C — r/forhire 专用格式

```
[For Hire] Custom Claude Code Skill / AI Automation Developer

I build custom AI automation tools, Claude Code skills, and workflow automations.

**What I can build for you:**
- Claude Code custom skills (browser automation, data processing, API integration)
- AI agent workflows (multi-step reasoning, tool use, RAG)
- Browser automation scripts (Playwright/Puppeteer)
- n8n low-code workflow automation
- Discord/Telegram bots with AI integration

**Recent work:**
- {EXAMPLE_1}: {DESCRIPTION_1}
- {EXAMPLE_2}: {DESCRIPTION_2}
- {EXAMPLE_3}: {DESCRIPTION_3}

**Rates:** ${SIMPLE_RATE} for simple tools, ${MEDIUM_RATE} for complex workflows. Fixed price per project, scoped upfront.

**Contact:** DM me here or Discord: {DISCORD_HANDLE}

📍 Remote | USD payment via Wise/PayPal
```

---

## 模板 2: 跟进 (Follow-Up)

**适用:** 初接触后 3-5 天无回复
**目标:** 轻量提醒，提供额外价值，不给压力
**长度:** 40-80 词

### 英文模板

```
Hey — just following up on my message from {DAYS_AGO} days ago about {BRIEF_TOPIC}. No worries if you found someone or went another direction.

If you're still exploring options, I put together a quick note on how I'd approach {THEIR_NEED} — might be useful even if you go with someone else or build it yourself. Happy to share.

Either way, good luck with {THEIR_PROJECT}!
```

### 中文策略说明

核心策略：**不提钱 + 提供额外价值 + 允许对方无压力不回复。**

- "No worries if you found someone" 释放社交压力
- "might be useful even if you go with someone else" 降低对方回复的心理成本
- 不要重复第一次的全部内容，只提主题
- 如果第二次跟进仍无回复 → 标记 Stale，不再跟

### 红旗警告
- ❌ 不要催（"Did you see my message?"）
- ❌ 不要降价（"I can do it cheaper"）
- ❌ 最多跟 2 次，第 2 次仍无回复 → Stale

---

## 模板 3: 报价 (Proposal)

**适用:** 客户已回复，范围讨论清楚
**目标:** 正式报价，确认范围，推动决策
**长度:** 150-300 词

### 英文模板

```
Great chatting with you about {THEIR_PROJECT}! Based on our conversation, here's what I'm proposing:

**Scope:**
{FEATURE_1}
{FEATURE_2}
{FEATURE_3}

Out of scope (for now): {OUT_OF_SCOPE_ITEMS}

**Technical Approach:**
- {TECH_STACK} — {REASON}
- {ARCHITECTURE_NOTE}

**Timeline:**
- Start: {START_DATE}
- First milestone ({MILESTONE_1}): {DATE_1}
- Delivery: {DATE_2}
- Includes {SUPPORT_DAYS} days of post-delivery support

**Deliverables:**
- Working {TOOL_TYPE} integrated with {PLATFORM}
- Source code with documentation
- Setup/deployment guide
- {ADDITIONAL_DELIVERABLE}

**Price: ${AMOUNT} USD** — fixed price
- 50% upfront (${HALF_AMOUNT}) to start
- 50% on delivery
- Payment via: {PAYMENT_METHOD}

**What I need from you to start:**
1. {REQUIREMENT_1}
2. {REQUIREMENT_2}

Let me know if this works for you, or if you'd like to adjust the scope. Happy to hop on a quick call to discuss.
```

### 中文策略说明

核心策略：**专业感 + 确定性 + 低风险感知。**

- 复述 scope（确认理解一致，避免后续扯皮）
- 明确 out of scope（管理期望）
- 固定价 + 50/50 分期（降低客户风险感知）
- 明确告诉你需要什么（推动对方行动）
- 给一个"修改范围"的出口（不逼单）

### 红旗警告
- ❌ 不要在需求不清楚时报价
- ❌ 不要低估工期（给自己留 buffer）
- ❌ 不要报小时价——固定价对双方都更可预期

---

## 模板 4-A: 谈判 — 客户说太贵 (Scope Adjustment)

**适用:** 客户觉得价格超出预算
**目标:** 保持交易 alive，通过降 scope 而不是降价来匹配预算
**长度:** 80-150 词

### 英文模板

```
Totally understand — budget matters. Here are two options that might work better:

**Option A — Core Scope: ${PRICE_A}**
{FEATURE_SET_A}
This covers the essential functionality you need.

**Option B — Full Scope: ${PRICE_B}** (what we originally discussed)
{FEATURE_SET_B}
Better for longer-term use and includes {EXTRA_VALUE}.

Both include the same {GUARANTEE/SUPPORT}. You can always start with Option A and upgrade later — the work stacks.

If neither fits, what budget range were you hoping for? I might be able to suggest a simpler approach.
```

### 中文策略说明

核心策略：**从不直接降价——降低 scope 而不是降低价格。**

- 给两个选项（不是"要不要"而是"A 还是 B"）
- Option A 要有真实价值（不是阉割版）
- "可以后续升级" 降低当下决策压力
- 最后问真实预算——如果两个选项都不行，了解对方承受范围

### 红旗警告
- ❌ 不要直接说"好吧我便宜点"
- ❌ Option A 不要做成没用的废版
- ❌ 如果对方预算确实远低于你的最低价，礼貌退出

---

## 模板 4-B: 谈判 — 客户说可以找到更便宜的 (Value Differentiation)

**适用:** 客户在比价，觉得别人更便宜
**目标:** 区分价值，不贬低竞争对手，问出真实预算
**长度:** 60-120 词

### 英文模板

```
You probably can find cheaper options out there — totally fair.

What I'd say is: with my work, you get {DIFFERENTIATOR_1} (like {SPECIFIC_EXAMPLE}), {DIFFERENTIATOR_2}, and {DIFFERENTIATOR_3}. If those matter less for your use case, going with a lower-cost option might make total sense.

If you do want to work with me, I'm happy to adjust the scope to match your budget. What price range were you thinking?
```

### 中文策略说明

核心策略：**承认竞争 + 区分价值 + 不让步价格 + 问预算。**

- "You probably can" 开头的承认降低对抗感
- 不贬低竞争对手——"might make total sense" 表示尊重
- 区分价值要具体、可感知（不要空泛说"I'm better"）
- 最后回到"调整范围"而不是"调整价格"

### 红旗警告
- ❌ 不要说"他们质量差"、"便宜没好货"
- ❌ 不要降价匹配竞争对手
- ❌ 不要在不确定差异点时使用此模板

---

## 模板 5: 成交 (Closing)

**适用:** 客户接受报价
**目标:** 降低付款摩擦，立刻推动行动，给第一个里程碑
**长度:** 80-120 词

### 英文模板

```
Awesome — excited to build this for you! Here's how we kick off:

**Step 1 — Payment:**
Send 50% (${AMOUNT}) via {PAYMENT_METHOD} to {PAYMENT_DETAILS}

**Step 2 — Access:**
Please grant me access to {PLATFORM/REPO} — {ACCESS_INSTRUCTIONS}

**Step 3 — Communication:**
Let's use {CHANNEL} for updates. I'll send a progress update by {FIRST_MILESTONE_DATE} covering {MILESTONE_CONTENT}.

Once the payment clears, I'll start work on {START_DATE}. First thing I'll do is {FIRST_ACTION}.

Any questions before we start?
```

### 中文策略说明

核心策略：**立刻行动 + 降低摩擦 + 给确定性。**

- 三个步骤清晰可执行
- 给出具体的第一个里程碑时间（减少对方"钱打过去没动静了"的焦虑）
- 说出你马上要做的第一件事（"First thing I'll do is..."）——增加确定性
- 用 "Any questions before we start?" 而不是 "Let me know if..." —— 前者假设开始，后者被动等待

### 红旗警告
- ❌ 不要在定金到账前开始工作
- ❌ 不要共享银行账号详细信息——用 Wise/PayPal/Crypto 的 handle/链接
- ❌ 不要接受"做完再付"（除非是老客户）

---

## 模板 6: 交付后 (Post-Delivery)

**适用:** 项目完成并交付后 3-7 天
**目标:** 确认满意、提醒维护、求 referral、upsell
**长度:** 60-100 词

### 英文模板

```
Hey! Hope the {TOOL_NAME} is running smoothly. Just checking in — anything needs tweaking? I include {SUPPORT_DAYS} days of post-delivery support, so don't hesitate to reach out.

One thing I noticed while building this: {INSIGHT_1}. Might be worth considering down the line. If you ever want to extend it or add {FEATURE_SUGGESTION}, just let me know.

Also — if you know anyone who needs something similar, feel free to send them my way! Happy to offer a referral discount.

Thanks again for the project — was a fun one to build!
```

### 中文策略说明

核心策略：**售后不消失 + 自然提复购和转介绍。**

- 先问有没有问题（维护承诺）
- 给一个建设性建议（展示持续关注，不是做完就跑）
- 提 referral（轻描淡写，不 push）
- "was a fun one to build" 给正面情绪结尾

### 红旗警告
- ❌ 不要在交付当天发——等 3-7 天
- ❌ 不要硬推销下一个项目
- ❌ 如果项目有小问题，先修好再发这个

---

## 模板速查表

| 场景 | 模板 | 时机 | 关键动作 |
|------|------|------|----------|
| Hot Lead 初次联系 | 1-A (有需求) / 1-B (无工具) | 发现后 24h 内 | 引用帖子、展示案例、问预算 |
| r/forhire 发帖 | 1-C | 发现后 | 遵守格式、列技能和 rate |
| 无回复跟进 | 2 | 3-5天后 | 不提钱、给价值、低压力 |
| 发送正式报价 | 3 | 范围确认后 | 复述 scope、固定价、50/50 |
| 客户说贵 | 4-A | 谈判中 | 降 scope 不降价、两选项 |
| 客户比价 | 4-B | 谈判中 | 区分价值、不贬低、问预算 |
| 客户接受 | 5 | 接受后立刻 | 收定金、给里程碑、降低摩擦 |
| 交付后回访 | 6 | 交付后 3-7天 | 检查满意、referral、insight |

**所有模板都需要根据具体线索个性化——不要直接复制粘贴。** `{VARIABLE}` 占位符是提醒你定制的地方。
