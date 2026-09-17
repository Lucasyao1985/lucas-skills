/**
 * X/Twitter Post Analyzer Workflow Script (v2 — optimized)
 *
 * Changes from v1:
 * - Single fetch agent with sequential fallback (was 3 parallel agents)
 * - Priority: fxtwitter API → WebSearch → direct WebFetch
 * - Analyze agent uses no tools (pure text processing)
 * - Total tool calls: 1-3 (was 10+)
 */

export const meta = {
  name: 'x-post-analyzer',
  description: 'Fetch and analyze X/Twitter post content, output structured Chinese report',
  phases: [
    { title: 'Fetch', detail: '获取推文内容' },
    { title: 'Analyze', detail: '综合分析生成中文报告' },
  ],
}

const xUrl = args?.url || args

if (!xUrl) {
  return { error: '未提供 X/Twitter URL', usage: '请提供 X/Twitter 帖子链接' }
}

function parseXUrl(url) {
  const patterns = [
    /(?:x\.com|twitter\.com)\/(\w+)\/status\/(\d+)/,
    /nitter\.net\/(\w+)\/status\/(\d+)/,
  ]
  for (const pattern of patterns) {
    const match = url.match(pattern)
    if (match) return { username: match[1], tweetId: match[2] }
  }
  return null
}

const parsed = parseXUrl(xUrl)
const username = parsed?.username || 'unknown'
const tweetId = parsed?.tweetId || 'unknown'

phase('Fetch')
log(`正在获取推文: @${username}/status/${tweetId}`)

// Single agent with sequential fallback — minimizes tool calls
const fetchResult = await agent(
  `You must fetch the content of this X/Twitter post: ${xUrl}

STEP 1 (try first): Use WebFetch to fetch this URL:
https://api.fxtwitter.com/${username}/status/${tweetId}
This API returns JSON with full post text, media info, engagement data, and user info.
If it returns valid data with post text, use it and STOP. Do not try other sources.

STEP 2 (only if step 1 fails or returns no text): Use WebSearch to search for:
"${username} tweet ${tweetId}" or "site:x.com ${username} status ${tweetId}"
Use whatever text you find. STOP after this.

STEP 3 (only if steps 1+2 both fail): Use WebFetch on the original URL ${xUrl}
This is a last resort — it often gets blocked.

Return ALL retrieved data in this EXACT format:
- POST TEXT: (full original text, verbatim)
- TRANSLATION: (if non-English)
- MEDIA: (type, description of visual content, duration/resolution if video)
- QUOTED TWEET: (full text if any, otherwise "none")
- ENGAGEMENT: (views, likes, retweets, replies if available)
- USER INFO: (username, bio, followers if available)
- SOURCE: (which step succeeded: fxtwitter/search/direct)

Do NOT try multiple sources if the first one succeeds. Minimize tool calls.`,
  { label: 'fetch', phase: 'Fetch' }
)

log('获取完成，开始分析...')

phase('Analyze')

// Analyze agent uses NO tools — pure text processing, zero permission prompts
const report = await agent(
  `Based on this data for the X/Twitter post by @${username}, create a CONCISE Chinese report.

Data:
${fetchResult || '获取失败'}

Output ONLY these 5 sections in Chinese:

## 1. 原文
(Complete original text, verbatim. If no text (video-only), say so.)

## 2. 中文翻译
(Full Chinese translation. If no text, say "无文字内容可翻译".)

## 3. 图片/视频内容
(Type, what it shows — describe actual visual content — duration/resolution if video. If no media, write "无".)

## 4. 引用内容与上下文
(If quotes another post: full text + author + context. If none, write "无引用推文".)

## 5. 这条推文到底在说什么
(Clear explanation: what the tweet says, why it was posted, what point it's making. Include background context if needed. 2-4 paragraphs.)

Rules:
- Only include actually retrieved data. If missing, say so.
- Do NOT fabricate content.
- Do NOT include account info, engagement data, reply analysis, spread analysis, or influence assessment.
- Be specific about media content — describe what you actually see, not generic placeholders.`,
  { label: 'analyze', phase: 'Analyze' }
)

log('分析完成')
return report
