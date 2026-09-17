# Reddit Seed User Report Template

```markdown
# Reddit Seed User Research — [Project Name]

**Generated:** YYYY-MM-DD
**Project directory:** [path]
**Based on:** brand.md, [other files]
**Mode:** manual review only; no automatic posting
**Language note:** Reddit-ready reply drafts stay in English unless the target thread uses another language. Every report item includes Chinese translation or Chinese explanation.

## Executive Summary

- Best opportunities found: [N]
  - 中文：[中文解释：本轮找到多少个值得处理的机会]
- Reply now: [N]
  - 中文：[中文解释：可以现在回复的数量]
- Reply without link: [N]
  - 中文：[中文解释：可以回复但不建议贴链接的数量]
- Ask first: [N]
  - 中文：[中文解释：先询问对方是否需要资源的数量]
- Monitor: [N]
  - 中文：[中文解释：只记录观察、暂不回复的数量]
- Skip: [N]
  - 中文：[中文解释：不建议参与的数量和原因]

**中文速览：** [用中文说明最重要的发现、优先级和整体 Reddit 策略。]

## Search Buckets Used

| Bucket | Keywords / Queries | Why | 中文说明 |
|---|---|---|---|
| Problem | [queries] | [reason] | [这些问题词为什么能找到真实痛点] |
| Solution | [queries] | [reason] | [这些工具/方案词为什么相关] |
| Workflow | [queries] | [reason] | [这些工作流词对应什么用户场景] |
| Audience | [queries] | [reason] | [这些社区/角色为什么值得看] |
| Alternatives | [queries] | [reason] | [这些替代品如何帮助定位项目] |

## Link Readiness Assumptions

- Account readiness: [age/karma/subreddit history if the user provided it; otherwise Unknown]
  - 中文：[账号注册时间、karma、历史参与情况；未知就写未知]
- Product readiness: [repo/site/docs/demo/privacy/license readiness]
  - 中文：[产品链接前的准备情况，比如 README、license、隐私说明、安装方式、demo]
- Open-source status: yes/no/unknown
  - 中文：[是否开源；如果开源，优先评估 repo 分享和开源项目展示路径]
- Manual checks before posting: [subreddit sidebar/rules/showcase thread/account state]
  - 中文：[发之前需要用户手动确认的规则和账号条件]

## Ranked Opportunities

| Rank | Label | Subreddit | Thread | User Question / Need | 用户问题中文翻译 | User Intent | 中文意图 | Fit | Link Policy | 中文链接策略 | Open-source Angle | 开源角度 | Risk | 中文风险 |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Reply now | r/example | [title](https://reddit.com/...) | [original question, concise excerpt, or clearly marked paraphrase] | [用户原问题/需求的中文翻译] | [intent] | [用户到底想解决什么问题] | High | Link after value / Ask first / No link | [为什么可以或不可以带链接] | [repo/resource/showcase angle or none] | [如果是开源项目，该怎么分享] | Low | [为什么风险低/中/高] |

**中文读法：**

- `Reply now`：[中文解释]
- `Reply without link`：[中文解释]
- `Ask first`：[中文解释]
- `Monitor`：[中文解释]
- `Skip`：[中文解释]

**Link policy guide / 链接策略读法：**

- `No link`: [中文：不要放链接，风险或不匹配太高]
- `Ask first`: [中文：先问对方是否需要资源，等回复后再分享]
- `Link after value`: [中文：可以在有帮助回答之后放链接，必须披露 affiliation]
- `Link allowed`: [中文：帖子明确要工具/资源，板块规则和账号条件允许时可以带链接]
- `Open-source share`: [中文：以开源项目/repo/实现参考的角度分享，而不是商业宣传]
- `Dedicated showcase`: [中文：更适合单独发项目展示帖或开源分享帖，而不是在评论里贴]

## Reply Drafts

### 1. [Thread Title]

- **URL:** [link]
- **Subreddit:** r/[name]
- **User question / need statement:** [original question, concise excerpt, or clearly marked paraphrase]
- **中文翻译：** [用户问题/需求的中文翻译]
- **Label:** Reply now / Reply without link / Ask first / Monitor / Skip
- **Why it fits:** [short reason]
- **Risk notes:** [subreddit rule, new account, link risk, tone]
- **Recommended link policy:** no link / ask first / link after value / link allowed / open-source share / dedicated showcase
- **Link readiness audit:** [account readiness, subreddit tolerance, thread intent, product readiness, disclosure requirement, manual checks]
- **Open-source sharing angle:** [if product is open source, say whether repo/resource sharing is appropriate and how]
- **中文判断：** [为什么值得回，适合什么话术]
- **中文风险：** [中文说明风险和边界]
- **中文链接策略：** [中文说明现在是否应该贴链接]
- **开源分享判断：** [中文说明是否适合走开源项目分享角度]

**Draft reply - no link / ask-first version:**

```text
[human reply draft]
```

**中文翻译 / 中文意图说明：**

```text
[逐段中文翻译，或说明每段英文回复想达到什么效果。不要省略。]
```

**Draft reply - link-enabled version, only if allowed:**

```text
[human reply draft with affiliation disclosure and link placed after useful answer; otherwise write "Not recommended for this thread."]
```

**中文翻译 / 中文意图说明：**

```text
[带链接版本的中文翻译或说明；如果不建议带链接，解释为什么。]
```

**Open-source share variant, if relevant:**

```text
[open-source oriented reply or showcase-post angle; otherwise write "Not relevant."]
```

**中文说明：**

```text
[开源分享版本的中文说明；包括为什么适合/不适合。]
```

**Audit:**

- Helps without link: yes/no, why
  - 中文：[为什么不贴链接也有帮助]
- Link now / ask first / avoid link / open-source share: [decision and why]
  - 中文：[现在带链接、先问、避免链接、或走开源分享的判断]
- Account readiness assumptions: [known/unknown]
  - 中文：[账号年龄、karma、参与历史是否已知]
- Subreddit rule assumptions: [known/unknown/manual check needed]
  - 中文：[板块规则是否需要手动确认]
- Affiliation disclosure needed: yes/no
  - 中文：[是否需要披露“我做了这个工具”]
- Needs manual editing before posting: [notes]
  - 中文：[发之前需要怎么改]

## Patterns and Learnings

- [Repeated pain point]
  - 中文：[重复痛点的中文解释]
- [Useful user language]
  - 中文：[值得复用的用户原话/表达]
- [Subreddits to keep monitoring]
  - 中文：[为什么继续关注这些板块]

## Content or Product Ideas

| Idea | 中文想法 | Source Pain | 中文痛点 | Why It Helps | 中文说明 |
|---|---|---|---|---|---|
| [idea] | [中文想法] | [pain] | [中文痛点] | [reason] | [为什么对产品/内容有帮助] |

## Open-source Sharing Opportunities

| Opportunity | 中文机会 | Best Venue | 中文渠道 | Share Angle | 中文角度 | Readiness Checks | 中文准备项 |
|---|---|---|---|---|---|---|---|
| [repo/resource/showcase/comment opportunity] | [中文说明机会] | [subreddit/showcase thread/reply context] | [适合在哪里分享] | [implementation reference, OSS launch, feedback request, contribution invitation] | [开源分享话术角度] | [license, README, install, privacy, demo, issues] | [发之前要补齐什么] |

## Project Inspirations

| Inspiration | 中文启发 | Reddit Signal | 中文信号 | Project Implication | 中文说明 |
|---|---|---|---|---|---|
| [positioning/messaging/product/docs/community insight] | [中文启发点] | [which thread/pain/language triggered this] | [中文说明 Reddit 信号] | [what this means for the current project] | [对本项目意味着什么] |

## Optimization Opportunities

| Priority | Area | Gap / Issue | 中文问题 | Reddit Signal | Recommended Measure | 中文措施 |
|---|---|---|---|---|---|---|
| High / Medium / Low | [product/docs/onboarding/trust/messaging/community] | [what still needs improvement] | [中文说明项目还有哪里需要优化] | [source pain or user question] | [specific action to take] | [可采取的具体措施] |

## Next Actions

1. [highest priority action]
   - 中文：[中文下一步]
2. [second action]
   - 中文：[中文下一步]
3. [monitoring action]
   - 中文：[中文下一步]
```
