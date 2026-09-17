---
name: reddit-seed-user-research
description: "Find Reddit seed-user opportunities for a specific project and draft helpful, human replies. Use when the user wants to promote a named project on Reddit, find target users for a known product, or run Reddit outreach from a project directory that has brand.md or README. Triggers include \"Reddit seed users for [project]\", \"find Reddit users for [tool]\", \"Reddit promotion for [product]\", \"帮我在 Reddit 找 [项目名] 的用户\", \"给 [项目] 做 Reddit 推荐\". IMPORTANT: If the user says \"帮我在 Reddit 找用户\" or \"find Reddit users\" WITHOUT naming a project AND the current directory has no brand.md or README, STOP and ask 4 clarifying questions (project name, problem solved, target users, open-source status). Do NOT search Reddit without project context."
metadata:
  author: adapted-for-claude-code
  version: 1.0.0
---

# Reddit Seed User Research

## Purpose

Use this skill to turn a project directory into a repeatable Reddit seed-user research workflow:

1. Confirm the project identity — from `brand.md`, local files, or by asking the user 4 clarifying questions.
2. Search Reddit for real user needs and repeated pain points.
3. Score which threads are worth replying to.
4. Draft value-first, human replies.
5. Produce a report with clickable source links and a follow-up tracking document.

Do not post automatically. The user should review and publish replies manually.

## Tools Used

This skill uses Claude Code's built-in tools:

- **WebSearch**: Primary tool for searching Reddit. Use `site:reddit.com` queries to find relevant threads. Can also search specific subreddits with `site:reddit.com/r/<subreddit>`.
- **WebFetch**: Read full thread content from Reddit URLs to extract user questions, body text, and comment context.
- **Bash**: Create project files (`brand.md`, report files), manage directories.
- **Edit/Write**: Create and update `brand.md`, reports, and tracking documents.

No external MCP servers or API keys are required. Everything works through web search and fetch.

## Required Inputs

Work from the current project directory by default.

First look for, in order:

1. `brand.md`
2. `brand_dna.md`
3. `docs/brand.md`
4. `README.md`, `README.*`, package/app metadata, landing copy, screenshots, or repo files

`brand.md` is a local research artifact, not a repository artifact.

If `brand.md` is missing or stale, create or update a draft `brand.md` in the project root before doing Reddit research. Use [references/brand-template.md](references/brand-template.md). Mark assumptions clearly when local evidence is thin.

Before creating or updating project-root `brand.md` in a Git repository:

- Make sure `brand.md` is ignored through the repository-local Git exclude file: `.git/info/exclude`.
- Do not write `brand.md` into `.gitignore`.
- Do not stage, commit, or otherwise place `brand.md` under Git tracking.
- If `.git/info/exclude` does not contain a `brand.md` entry, append one there. This is local-only and should not change the shared repository.
- If `brand.md` is already tracked by Git, do not silently untrack or delete it. Tell the user it is already tracked and ask before changing Git history or index state. For the current run, prefer reading it without modifying it, or create/update a clearly local alternative such as `brand.local.md` and add that filename to `.git/info/exclude`.
- If the directory is not a Git repository, create `brand.md` normally and note that no Git ignore step was needed.

## Project Discovery — Read Before Proceeding

**This is the first decision the skill must make.** Before any search, confirm the project is understood. Follow this decision tree:

### Decision Tree

1. **brand.md exists and is not stale** — proceed to "Build Search Buckets".
2. **README.md or other project files exist with clear project info** — extract what you can, create `brand.md` using [references/brand-template.md](references/brand-template.md), mark any assumptions clearly, then proceed.
3. **No project files exist, OR files exist but contain no clear project description** — **STOP. Do NOT search Reddit.** The skill cannot find the right users without knowing what project to find them for. Ask the user:

> 在开始 Reddit 搜索之前，我需要先了解你的项目。请回答这 4 个问题：
>
> **1. 项目是什么？**
> 叫什么名字？用一句话描述它做什么。
> （例："PhotoMagic，一个 AI 批量图片处理工具，支持背景移除和无损放大"）
>
> **2. 解决什么痛点？**
> 用户会用什么关键词搜索这类工具？他们遇到这个问题时会怎么描述？
> （例："how do I batch remove background from product photos"、"best free alternative to remove.bg"）
>
> **3. 谁会用它？**
> 目标用户的具体画像。
> （例：跨境电商运营、独立设计师、内容创作者、小企业主...）
>
> **4. 开源还是闭源？**
> 有没有 GitHub 链接、官网、或 demo 地址？如果是开源项目，用什么协议？
> （例："开源 MIT，github.com/example/photomagic，官网 photomagic.example.com"）

After the user answers all 4 questions, immediately create `brand.md` from their answers using [references/brand-template.md](references/brand-template.md), then proceed to "Build Search Buckets".

**Do NOT** skip the questions and guess. **Do NOT** search Reddit without project context. A vague search without project context produces useless results.

### Why This Matters

| Without project context | With project context |
|---|---|
| Searches "best tool Reddit" — noise | Searches "batch remove background product photos" — signal |
| Can't score relevance — every post looks possible | Knows exactly which posts match the project |
| Reply drafts are generic and useless | Reply drafts reference the actual product and use case |
| Report has no actionable insights | Report ties Reddit signals to specific product improvements |

## Brand Profile Requirements

`brand.md` must summarize:

- What the project is and which platforms it runs on
- The killer feature or sharpest differentiator
- Who it helps
- The short project summary, evaluation, and market positioning
- Use cases and jobs-to-be-done
- Relevant keywords users would naturally say
- Competitors, alternatives, and adjacent workflows
- Trust boundaries such as open source, local-only, no backend, bring-your-own-key, privacy, or cost constraints

Keep this file useful for future runs. Update it when research reveals better user language, while preserving its local-only/untracked status.

## Research Workflow

### 1. Build Search Buckets

Create search buckets from `brand.md`:

- Problem searches: what users complain about or ask how to do
- Solution searches: tool/category/recommendation terms
- Workflow searches: platform-specific tasks and end-to-end jobs
- Competitor/alternative searches: tools users already mention
- Audience searches: communities and hobbies where the project is naturally useful

Prefer user language over marketing language. Search for phrases like "how do I", "looking for", "best way to", "any tool for", "recommend", "transparent png", "printable stickers", not just product-category keywords.

### 2. Search Reddit

Use Claude Code's WebSearch tool with `site:reddit.com` as the primary method:

1. **Discovery search**: Use WebSearch with queries like `site:reddit.com "how do I" <problem-keyword>` or `site:reddit.com "looking for" <tool-type>`. Run multiple searches per bucket, trying different phrasings.
2. **Subreddit-specific search**: Narrow to promising subreddits with `site:reddit.com/r/<subreddit> <query>`.
3. **Time-filtered search**: Add `after:YYYY-MM-DD` to focus on recent threads (e.g., past 3-6 months).
4. **Read full threads**: Use WebFetch on promising Reddit URLs to extract the full post body, comments, and context.

Run at least 3-5 searches per bucket to surface different types of threads. Vary between problem-language and solution-language queries.

For each candidate thread, capture:

- Post URL
- Subreddit
- Title
- Date if available
- Score/comments if available
- The user's original question or need statement
- A Chinese translation of the user's original question or need statement
- User intent
- Exact wording that signals demand

When WebFetch provides the body text, include a concise excerpt of the user's actual question. If only the title/search snippet is available, clearly mark the question as "title/snippet only" or "paraphrased from available source." Do not invent missing details.

### 3. Filter and Score

Do not recommend every mention. Score each candidate:

- Need fit: is the user actually asking for a problem this project solves?
- Timing: is the thread recent enough or still active?
- Community fit: does the subreddit tolerate helpful tool mentions?
- Reply risk: would mentioning the project feel spammy?
- Product fit: does the project solve the issue today, without overclaiming?
- Human fit: can the reply help even if the user never clicks anything?
- Link readiness: would it be acceptable to include a project link after considering the user's account readiness, subreddit rules/culture, thread intent, product readiness, and disclosure?

Labels:

- `Reply now`: strong fit, current thread, low spam risk
- `Reply without link`: useful answer, but link would feel too promotional
- `Ask first`: ask if they want a tool/resource before sharing
- `Monitor`: relevant pattern but not an immediate reply
- `Skip`: weak fit, old/dead thread, rule risk, or forced mention

### 3.1 Link Readiness and Promotion Assessment

Do not blindly remove all product links. Evaluate whether a link is appropriate.

Classify link policy with one of:

- `No link`: link would be spammy, off-topic, unsafe, or against rules.
- `Ask first`: good fit, but the thread is old, the user did not explicitly ask for tools, or the community is sensitive.
- `Link after value`: link can appear after a genuinely useful answer and clear affiliation disclosure.
- `Link allowed`: the thread explicitly asks for tools/resources, the subreddit allows relevant links, and the user/project are prepared.
- `Open-source share`: the product is open source and the best angle is repository/resource sharing, not commercial promotion.
- `Dedicated showcase`: the subreddit allows project/showcase posts, open-source launches, or specific showoff threads; use this for a new post, not a reply.

Assess these factors:

- Account readiness: account age, karma, prior non-promotional participation, subreddit-specific history, and whether the user says these are sufficient. If unknown, mark as `Unknown` and be conservative.
- Subreddit tolerance: rules, wiki/sidebar, self-promotion policies, showcase threads, open-source friendliness, and recent similar posts.
- Thread intent: explicit tool request, comparison request, open-source request, "what do you use" thread, pain-point complaint, or general discussion.
- Product readiness: public repo/site, README, license, privacy/security docs, install instructions, demo/screenshots, and whether the linked page answers likely objections.
- Disclosure: any link to the user's own project must clearly disclose affiliation.
- Value-first quality: the reply must help even if the user never clicks.

If the product is open source, always evaluate an open-source sharing path:

- Consider whether a GitHub/repo link is more appropriate than a marketing site.
- Look for communities and formats that welcome open-source project sharing, such as open-source subreddits, project showcase threads, builder communities, or technical implementation discussions.
- Frame the project as a useful reference, implementation, or contribution opportunity when that is more natural than a product pitch.
- Check whether the repo has a license, README, privacy/security notes, issue templates or contribution guidance, and clear install/run instructions before recommending an open-source link.
- If the open-source path is promising but repo readiness is weak, recommend preparation steps before posting.

### 4. Draft Replies

Draft replies with these rules:

- Answer the user's question first.
- Use a plain, human tone. Avoid launch language, sales claims, and polished ad copy.
- Mention affiliation if recommending the user's project: "i made a small tool for this" or "i built something for this use case".
- Do not drop links by default, but do include a link-enabled variant when the link readiness assessment says `Link after value`, `Link allowed`, `Open-source share`, or `Dedicated showcase`.
- Prefer "happy to share if useful" when link readiness is `Ask first`.
- When a link is allowed, put it after the useful answer, not as the first sentence. Disclose affiliation before or next to the link.
- Never pretend to be a random unaffiliated user.
- Do not mention the project in low-fit threads.
- Keep comments short enough for Reddit. Most should be 60-160 words.
- Avoid spammy words like "ultimate", "revolutionary", "best", "optimize", "streamline", "growth hack", "try my product".
- For open-source products, include an open-source oriented variant when relevant. The variant should mention that it is open source, link to the repo/resource only if link policy allows it, and invite feedback/issues rather than sounding like an ad.

### 5. Review Before Reporting

For every drafted reply, include an audit:

- Why this reply is useful even without the project link
- Whether to include a link now, wait for a reply, use an open-source share angle, or avoid linking
- Account readiness assumptions: account age/karma/participation if known; otherwise mark unknown
- Subreddit/link rule assumptions and whether they need manual verification before posting
- Any subreddit rule or tone risk
- Whether the user should disclose affiliation

Remove any draft that would feel like a pitch pasted into someone else's thread.

## Outputs

Create or update:

1. Local-only `brand.md` in the project root when missing or stale, ignored via `.git/info/exclude` in Git repositories
2. `reddit-seed-users/report-YYYY-MM-DD.md`
3. `reddit-seed-users/tracking.md`

Use [references/report-template.md](references/report-template.md) for the report format.

The report must include:

- Executive summary
- Search buckets and keywords used
- Ranked Reddit opportunities with clickable links
- The user's original question or need statement for every opportunity
- Chinese translation of every user question or need statement
- Reply recommendation label for each opportunity
- Draft reply
- Link policy: no link / ask first / link after value / link allowed / open-source share / dedicated showcase
- Link readiness assessment: account readiness, subreddit tolerance, thread intent, product readiness, disclosure requirement, and manual checks needed
- Open-source sharing assessment when the product is open source
- Risk notes
- Project inspirations: what this Reddit research suggests for the current project
- Optimization opportunities: what the project should improve, why, and concrete measures to take
- Next actions

The report must be bilingual by default:

- Keep Reddit-ready reply drafts in English unless the target subreddit/post is in another language.
- Add Chinese translation or Chinese explanation for every report item.
- "Every item" includes executive-summary bullets, table rows, search buckets, user questions, ranked opportunities, reply recommendations, risk notes, link policy, audits, patterns/learnings, content ideas, project inspirations, optimization opportunities, and next actions.
- For tables, include a Chinese column such as `中文说明`, or add a Chinese note directly below each row/group.
- For every opportunity, include `User question / need statement` and `中文翻译` near the top of the entry so the user can understand the original Reddit context without opening the link.
- For every opportunity, include a link readiness audit. If account readiness or subreddit rules are unknown, say so and do not assume links are allowed.
- When link policy allows a link, include both a no-link draft and a link-enabled draft, plus Chinese translations/intent notes for both.
- When the project is open source, include at least one open-source sharing recommendation: where to share, what angle to use, and what repo/docs readiness checks should pass first.
- For each reply draft, include both the English draft and a Chinese translation or Chinese intent note so the user can review the strategy without parsing English.
- Do not let Chinese annotations replace the English Reddit draft; the user should still be able to copy the English reply directly.
- In `Project Inspirations`, tie Reddit observations back to positioning, messaging, trust model, onboarding, docs, product surface, or community strategy.
- In `Optimization Opportunities`, list concrete project gaps and measures. Each item should include the observed Reddit signal, why it matters, priority, and recommended action.

The tracking document must preserve:

- Candidate threads
- Drafted replies
- Status: not posted / posted / replied / skipped
- Follow-up dates
- Notes on what worked and what did not

## Quality Bar

A good result should let the user:

- Understand which Reddit threads are worth acting on first
- Click directly into the original post
- Copy a reply draft with minimal editing
- Avoid obvious self-promotion mistakes
- Re-run the workflow later without rebuilding project context

Prefer 5 high-quality opportunities over 30 weak ones.

## Safety and Reputation Rules

- Do not automate posting, voting, mass commenting, or multi-account behavior.
- Do not suggest hiding affiliation.
- Do not recommend posting the same reply across many threads.
- Respect subreddit rules and removal/filter history.
- If the user's account is new or recently filtered, prefer comment-first and no-link replies.
- If relevance is weak, recommend monitoring instead of replying.

## Re-running

This skill is designed for repeatable use. To re-run later:

1. The `brand.md` file preserves project context
2. `tracking.md` records past actions and outcomes
3. New searches surface fresh threads
4. Previous reports provide a historical record

Simply invoke the skill again in the same project directory. It will pick up existing artifacts and focus on new opportunities.
