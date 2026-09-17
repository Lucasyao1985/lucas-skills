/**
 * reddit-deal-closer — Reddit Lead Search Script
 *
 * Usage:
 *   node search.js <search_url_or_subreddit> [--limit N]
 *
 * Examples:
 *   node search.js "r/forhire" --limit 15
 *   node search.js "https://www.reddit.com/r/forhire/search/?q=bot+OR+automation&sort=new&restrict_sr=on"
 *   node search.js "all" --limit 20  (scans all target subreddits)
 *
 * Prerequisites:
 *   - cookies.txt in same directory (Netscape cookie format: name=value\tdomain\tpath)
 *   - npm install playwright
 *
 * Output: JSON array of posts to stdout
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────────
const COOKIES_FILE = path.join(__dirname, 'cookies.txt');
const OUTPUT_LIMIT = parseInt(process.argv.find(a => a.startsWith('--limit='))?.split('=')[1] || '15');
const MIN_SCORE = parseInt(process.argv.find(a => a.startsWith('--min-score='))?.split('=')[1] || '0');

// ── Relevance Scoring: is this post hiring a DEVELOPER? ─────
function relevanceScore(post) {
  const title = (post.title || '').toLowerCase();
  const text = (post.text || '').toLowerCase();
  const flair = (post.flair || '').toLowerCase();
  const combined = title + ' ' + text + ' ' + flair;

  let score = 0;

  // === STRONG signals (developer/automation work) ===
  const strong = [
    'developer', 'engineer', 'programmer', 'coder', 'full stack', 'full-stack',
    'python', 'javascript', 'typescript', 'react', 'next.js', 'node.js', 'nodejs',
    'automation', 'bot', 'script', 'scraper', 'scraping', 'web scraping',
    'claude', 'openai', 'llm', 'ai agent', 'ai integration', 'langchain',
    'api', 'backend', 'frontend', 'devops', 'n8n', 'playwright', 'puppeteer',
    'prompt automation', 'workflow', 'ai tool', 'ai assistant', 'custom tool',
    'code', 'coding', 'software engineer', 'software developer',
    'technical cofounder', 'technical co-founder', 'build mvp',
  ];
  for (const kw of strong) {
    if (combined.includes(kw)) { score += 25; break; } // one strong hit is enough
  }

  // === MEDIUM signals (tech-adjacent) ===
  const medium = [
    'software', 'web app', 'web application', 'saas', 'startup',
    'technical', 'tech', 'data engineer', 'data pipeline',
    'integration', 'nocode', 'low-code', 'low code',
    'machine learning', 'ml engineer', 'ai', 'artificial intelligence',
    'cloud', 'aws', 'gcp', 'docker', 'kubernetes',
    'database', 'sql', 'nosql', 'firebase', 'supabase',
    'testing', 'qa automation', 'cypress', 'selenium',
    'mobile app', 'ios developer', 'android developer',
  ];
  let mediumHits = 0;
  for (const kw of medium) {
    if (combined.includes(kw)) mediumHits++;
    if (mediumHits >= 2) { score += 15; break; }
  }
  if (mediumHits === 1) score += 8;

  // === WEAK signals (only count if already tech-related) ===
  if (score >= 8) { // only award weak points if already confirmed as tech
    const weak = [
      'remote', 'freelance', 'contract', 'project',
      'build', 'create', 'develop',
    ];
    let weakHits = 0;
    for (const kw of weak) {
      if (combined.includes(kw)) weakHits++;
    }
    if (weakHits >= 3) score += 8;
    else if (weakHits >= 1) score += 3;
  }

  // === NEGATIVE signals (definitely NOT dev work) ===
  const negative = [
    'designer', 'graphic design', 'illustrator', 'video editor', 'video producer',
    'video presenter', 'voice actor', 'voice over', 'voiceover', 'videographer',
    'content writer', 'copywriter', 'blog writer', 'article writer', 'script writer',
    'virtual assistant', 'admin assistant', 'executive assistant', 'personal assistant',
    'accountant', 'bookkeeper', 'finance', 'payroll', 'accounting',
    'attorney', 'lawyer', 'legal', 'litigation', 'paralegal',
    'marketing', 'social media manager', 'seo specialist', 'growth marketer',
    'sales', 'customer support', 'customer service', 'call center',
    'recruiter', 'hr', 'human resources', 'talent acquisition',
    'photographer', 'photography', 'photo editor',
    'translator', 'interpreter', 'tutor', 'teacher', 'instructor',
    'fitness', 'coach', 'therapist', 'counselor', 'life coach',
    'presenter', 'host', 'actor', 'actress', 'model',
    'data entry', 'transcription', 'transcriber',
  ];

  // Context check: "script" in title with video/audio context = NOT programming
  if ((title.includes('script') || text.includes('script')) &&
      /\b(video|voice|actor|presenter|recording|record|speak|spoken|read|narrat)\b/i.test(combined)) {
    score -= 30; // penalize "script" when it means video/audio script, not programming
  }
  for (const kw of negative) {
    if (title.includes(kw)) { score -= 50; break; } // title-level negative = hard skip
  }
  // Check text for negative too (weaker penalty)
  let negHits = 0;
  for (const kw of negative) {
    if (combined.includes(kw)) negHits++;
  }
  if (negHits >= 2) score -= 30;

  // === BUDGET signals (strong positive) ===
  if (/\$\d+/.test(combined)) score += 15;
  if (/budget|rate|pay|salary|compensation/i.test(combined)) score += 8;
  if (/willing to pay|paid opportunity/i.test(combined)) score += 15;

  return score;
}

// Target subreddits and their search queries
// Tier 1 = hiring/freelance marketplaces (highest intent)
// Tier 2 = tech communities with hiring undercurrent
// Tier 3 = bot/automation specific
// Tier 4 = SaaS/startup/entrepreneur
const TARGETS = {
  // ── Tier 1: Hiring & Freelance Marketplaces ──
  'r/forhire': [
    'bot OR automation OR Claude OR AI OR script OR scraper OR developer',
    'n8n OR workflow OR integration OR "custom tool" OR Python OR automation',
  ],
  'r/hiring': [
    'developer OR programmer OR engineer OR automation OR bot OR AI OR scraper',
  ],
  'r/remotejs': [
    'react OR node OR typescript OR fullstack OR backend OR frontend OR automation',
  ],
  'r/remotepython': [
    'automation OR scraper OR bot OR API OR integration OR AI OR Claude',
  ],
  'r/freelance_forhire': [
    'developer OR programmer OR bot OR automation OR AI OR scraper OR script',
  ],
  'r/jobbit': [
    'developer OR automation OR bot OR AI OR scraper OR Python OR JavaScript',
  ],
  'r/hireaprogrammer': [
    'bot OR automation OR scraper OR AI OR Claude OR skill OR tool',
  ],
  'r/Jobs4Bitcoins': [
    'developer OR bot OR script OR automation OR scraper OR tool',
  ],

  // ── Tier 2: Tech Communities ──
  'r/ClaudeAI': [
    'custom OR skill OR build OR tool OR automate OR hire OR "how do I" workflow',
  ],
  'r/ClaudeCode': [
    'skill OR custom OR build OR tool OR workflow OR help OR looking',
  ],
  'r/Anthropic': [
    'Claude OR skill OR custom OR build OR tool OR hire OR develop',
  ],
  'r/aipromptprogramming': [
    'build OR tool OR custom OR automate OR hire OR skill',
  ],
  'r/webdev': [
    '"looking for" OR hire OR freelance developer OR "need developer" OR "custom"',
  ],
  'r/reactjs': [
    'hire OR "looking for" OR freelance OR developer OR "need help" build',
  ],
  'r/Python': [
    '"looking for developer" OR hire OR freelance OR "need script" OR automation',
  ],
  'r/node': [
    'hire OR "looking for" OR freelance OR developer OR "need" bot OR tool',
  ],
  'r/Programming': [
    '"looking for developer" OR "hire" automation OR bot OR "freelance"',
  ],

  // ── Tier 3: Bot & Automation Specific ──
  'r/Discord_Bots': [
    'commission OR hire OR paid OR custom OR "looking for" OR "need developer"',
  ],
  'r/automation': [
    'custom OR tool OR hire OR need OR "looking for" OR "build" automaton',
  ],
  'r/n8n': [
    'custom OR help OR workflow OR hire OR build OR "looking for"',
  ],
  'r/RedditDev': [
    'hire OR "looking for" OR "need" bot OR script OR tool OR automation',
  ],
  'r/TelegramBots': [
    'commission OR hire OR paid OR custom OR "looking for"',
  ],

  // ── Tier 4: SaaS / Startup / Entrepreneur ──
  'r/SaaS': [
    '"build MVP" OR outsource OR "hire developer" OR "technical cofounder" OR "need developer"',
  ],
  'r/startups': [
    '"technical cofounder" OR "build MVP" OR "developer needed" OR outsource OR "hire"',
  ],
  'r/Entrepreneur': [
    'automate OR "custom tool" OR "hire developer" OR outsource OR "need" build',
  ],
  'r/indiehackers': [
    'hire OR "looking for developer" OR outsource OR "need help" build OR automate',
  ],
  'r/SideProject': [
    '"looking for developer" OR "need help" build OR collaborate paid OR commission',
  ],

  // ── Tier 5: Niche / Long-tail ──
  'r/slavelabour': [
    'bot OR script OR automation OR Claude OR AI OR developer',
  ],
  'r/AI_Agents': [
    'build OR custom OR hire OR "looking for" OR developer OR tool',
  ],
  'r/LangChain': [
    'build OR custom OR hire OR "looking for" OR tool OR agent OR automation',
  ],
  'r/OpenAI': [
    'build OR custom OR hire OR developer OR tool OR automation OR agent',
  ],
};

// ── Cookie Loading ──────────────────────────────────────────
function loadCookies() {
  if (!fs.existsSync(COOKIES_FILE)) {
    console.error('[warn] cookies.txt not found — browsing without login');
    return [];
  }
  const raw = fs.readFileSync(COOKIES_FILE, 'utf-8').trim();
  const cookies = [];
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    // Try Netscape format (tab-separated)
    const parts = trimmed.split('\t');
    if (parts.length >= 7) {
      cookies.push({
        name: parts[5],
        value: parts[6],
        domain: parts[0].startsWith('.') ? parts[0] : `.${parts[0]}`,
        path: parts[2],
        httpOnly: parts[3] === 'TRUE',
        secure: parts[4] === 'TRUE',
      });
      continue;
    }

    // Try simple name=value format
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx > 0) {
      cookies.push({
        name: trimmed.substring(0, eqIdx),
        value: trimmed.substring(eqIdx + 1),
        domain: '.reddit.com',
        path: '/',
      });
    }
  }
  return cookies;
}

// ── Skip Filters ────────────────────────────────────────────
function shouldSkip(post) {
  const title = (post.title || '').toLowerCase();
  const flair = (post.flair || '').toLowerCase();
  const text = (post.text || '').toLowerCase();
  const combined = title + ' ' + flair + ' ' + text;

  // KEY: Skip [For Hire] / [Offer] — these are developers selling, NOT clients hiring
  if (title.startsWith('[for hire]') || flair.includes('for hire') || flair.includes('fh-forhire')) return true;
  if (title.startsWith('[offer]') || flair.includes('offer')) return true;
  // Generic "for hire" in title where OP is the developer selling services
  if (/for hire|offering|i (can|will) build|i (can|will) (create|develop|code|automate)/i.test(title)) return true;

  // KEEP: [HIRING] posts — these ARE your potential clients (checked later by relevance)

  // Skip free requests
  if (/free\b.*\bplease|anyone (willing|do this).*free|no budget|\bhelp me\b.*free/i.test(combined)) return true;

  // Skip posts that explicitly REJECT AI-generated code / AI tools
  // "No gen AI please", "no AI generated code", "no AI-assisted", etc.
  if (/\bno\b.*\b(ai|gen ai|generative ai|ai code|ai generat|ai-assist)\b/i.test(combined)) return true;
  if (/\bdon'?t\b.*\b(use|want)\b.*\b(ai|gen ai)\b/i.test(combined)) return true;
  if (/\bwithout\b.*\b(ai|gen ai)\b/i.test(combined)) return true;

  return false;
}

// ── Trust / Authenticity Scoring ────────────────────────────
function trustScore(post) {
  const title = (post.title || '').toLowerCase();
  const text = (post.text || '').toLowerCase();
  const combined = title + ' ' + text;

  let score = 50; // neutral start
  const flags = [];

  // === RED FLAGS (subtract) ===

  // Google Forms / Typeform / external form links = likely phishing/data harvesting
  if (/docs\.google\.com\/forms|typeform\.com|bit\.ly\/|tinyurl\.com|forms\.gle/i.test(text)) {
    score -= 40;
    flags.push('FORM_LINK: Google Form/Typeform — 大概率钓鱼收集个人信息');
  }

  // "DM me" without any company info
  if (/\bdm\b.*\b(me|for|if|pls|please)\b/i.test(combined) && !text.match(/https?:\/\//)) {
    score -= 10;
    flags.push('DM_ONLY: 仅私信联系，无公司网站或外部验证渠道');
  }

  // Telegram/WhatsApp-only contact (common in scam posts)
  if (/telegram|whatsapp/i.test(text) && !text.match(/https?:\/\//)) {
    score -= 15;
    flags.push('TELEGRAM_WHATSAPP: 仅第三方聊天工具联系');
  }

  // Gmail/hotmail/yahoo email (personal email, not company)
  if (/@gmail\.com|@yahoo\.com|@hotmail\.com|@outlook\.com/i.test(text)) {
    score -= 8;
    flags.push('PERSONAL_EMAIL: 个人邮箱而非企业邮箱');
  }

  // "paid trial" / "unpaid test" / "free sample"
  if (/unpaid|free (trial|test|sample)|work for exposure/i.test(combined)) {
    score -= 30;
    flags.push('UNPAID_WORK: 无偿试做/暴露换取工作');
  }

  // Too good to be true rate
  if (/\$\d{3,}\/hr/.test(text) && /no experience|entry level|beginner|no skill/i.test(combined)) {
    score -= 20;
    flags.push('TOO_GOOD: 高薪低门槛 — 可能是钓鱼');
  }

  // Short post with just "DM me" or link, no real description
  if (text.length < 100 && /\bdm\b|contact me|message me/i.test(combined)) {
    score -= 15;
    flags.push('THIN_POST: 帖子极短无实质内容 — 可能是批量钓鱼');
  }

  // New account signal (low karma / new user) — can't check without API, flag author
  // We'll check this later via WebFetch

  // === GREEN FLAGS (add) ===

  // Company name mentioned
  if (/we (are|at)\s+[A-Z][a-z]+|company|startup|firm|agency|studio|ventures/i.test(combined)) {
    score += 15;
    flags.push('COMPANY: 提及公司/团队名');
  }

  // Has external website/linkedin
  const urlMatch = text.match(/https?:\/\/[^\s]+/g);
  const hasWebsite = urlMatch && urlMatch.some(u =>
    /\.(com|io|ai|co|dev|org)\b/i.test(u) &&
    !/docs\.google\.com|typeform\.com|bit\.ly|forms\.gle/i.test(u)
  );

  if (hasWebsite) {
    // Check if the domain is a free hosting platform (impersonation risk)
    const suspectDomain = urlMatch.some(u =>
      /\.pages\.dev|\.netlify\.app|\.vercel\.app|\.github\.io|\.web\.app/i.test(u)
    );
    if (suspectDomain) {
      score -= 25;
      flags.push('SUSPECT_DOMAIN: 免费托管域名(.pages.dev/.netlify.app等) — 可能是仿冒钓鱼');
    } else {
      score += 15;
      flags.push('WEBSITE: 包含外部网站链接');
    }
  }

  // Detailed requirements
  if (text.length > 500) {
    score += 10;
    flags.push('DETAILED: 需求描述详细');
  }

  // Specific tech stack mentioned
  if (/react|python|javascript|typescript|node|next\.?js|api|docker|aws|postgres/i.test(combined)) {
    score += 10;
    flags.push('TECH_STACK: 明确了技术栈');
  }

  // Clear budget stated
  if (/\$\d+[\d,]*|€\d+|budget|rate|salary/i.test(combined)) {
    score += 10;
    flags.push('BUDGET: 明确提到薪资/预算');
  }

  // Multiple comments (community engagement = more likely real)
  if ((post.comments || 0) > 5) {
    score += 5;
    flags.push('ENGAGED: 社区有互动');
  }

  post._trust = Math.max(0, Math.min(100, score));
  post._trustFlags = flags;
  return post._trust;
}

// ── Combined filter: skip + relevance + trust ───────────────
function filterPost(post) {
  if (shouldSkip(post)) return false;
  const score = relevanceScore(post);
  post._relevance = score;
  if (MIN_SCORE > 0 && score < MIN_SCORE) return false;
  trustScore(post);
  return true;
}

// ── Extract Posts from Old Reddit Search Page ─────────────────
async function extractPosts(page) {
  return await page.evaluate(() => {
    const posts = [];
    // old.reddit.com search results use .search-result-link elements
    const results = document.querySelectorAll('.search-result-link');

    for (const el of results) {
      try {
        // Title: .search-title
        const titleEl = el.querySelector('.search-title');
        const title = titleEl?.textContent?.trim() || '';
        if (!title || title.length < 5) continue;

        const url = titleEl?.href || '';

        // Flair: .linkflairlabel
        const flairEl = el.querySelector('.linkflairlabel');
        const flair = flairEl?.textContent?.trim() || '';

        // Author: .author
        const authorEl = el.querySelector('.author');
        const author = authorEl?.textContent?.trim() || '';

        // Time: time element
        const timeEl = el.querySelector('time');
        const date = timeEl?.getAttribute('datetime') || timeEl?.textContent?.trim() || '';

        // Post body: .search-result-body
        const textEl = el.querySelector('.search-result-body');
        const text = textEl?.textContent?.trim().substring(0, 500) || '';

        // Score: .search-score
        const scoreEl = el.querySelector('.search-score');
        const scoreText = scoreEl?.textContent?.trim() || '0';
        const upvotes = parseInt(scoreText) || 0;

        // Comments: .search-comments
        const commentsEl = el.querySelector('.search-comments');
        const commentsText = commentsEl?.textContent?.trim() || '';
        const commentsMatch = commentsText.match(/(\d+)/);
        const comments = commentsMatch ? parseInt(commentsMatch[1]) : 0;

        posts.push({ title, url, flair, author, date, text, upvotes, comments });
      } catch (e) {
        // Skip malformed post
      }
    }
    // Normalize old.reddit.com → www.reddit.com
    return posts.filter(p => p.title.length > 5).map(p => ({
      ...p,
      url: p.url.replace('old.reddit.com', 'www.reddit.com')
    }));
  });
}

// ── Search a Single Subreddit ───────────────────────────────
async function searchSubreddit(browser, subreddit, query) {
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
  });

  const cookies = loadCookies();
  if (cookies.length > 0) {
    await context.addCookies(cookies);
  }

  const page = await context.newPage();
  // old.reddit.com has simple DOM (no shadow DOM), much more reliable for scraping
  const searchUrl = `https://old.reddit.com/${subreddit}/search?q=${encodeURIComponent(query)}&sort=new&restrict_sr=on`;

  console.error(`[search] ${searchUrl}`);

  try {
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000); // Let dynamic content load

    const posts = await extractPosts(page);
    const filtered = posts.filter(p => filterPost(p));

    console.error(`[found] ${filtered.length} posts (${posts.length} raw, ${posts.length - filtered.length} filtered)`);
    return filtered;
  } catch (e) {
    console.error(`[error] ${subreddit}: ${e.message}`);
    return [];
  } finally {
    await context.close();
  }
}

// ── Main ────────────────────────────────────────────────────
(async () => {
  const arg = process.argv[2] || 'all';

  // Build search list
  let searches = [];
  if (arg === 'all') {
    for (const [sub, queries] of Object.entries(TARGETS)) {
      for (const q of queries) {
        searches.push({ subreddit: sub, query: q });
      }
    }
  } else if (arg.startsWith('r/')) {
    const sub = arg;
    const queries = TARGETS[sub] || [process.argv[3] || 'bot OR automation OR hire OR custom'];
    for (const q of queries) {
      searches.push({ subreddit: sub, query: q });
    }
  } else if (arg.startsWith('http')) {
    // Direct URL — extract subreddit and query from URL
    const url = new URL(arg);
    const sub = url.pathname.split('/')[1]; // /r/subreddit/...
    const q = url.searchParams.get('q') || '';
    searches.push({ subreddit: `r/${sub}`, query: q });
  } else {
    console.error('Usage: node search.js <r/subreddit|all|url> [query] [--limit N]');
    process.exit(1);
  }

  console.error(`[scan] ${searches.length} searches across ${new Set(searches.map(s => s.subreddit)).size} subreddits`);
  console.error('');

  const browser = await chromium.launch({ headless: true });
  const allPosts = [];

  for (const { subreddit, query } of searches) {
    const posts = await searchSubreddit(browser, subreddit, query);
    for (const post of posts) {
      post._subreddit = subreddit;
      post._query = query;
    }
    allPosts.push(...posts);
  }

  await browser.close();

  // Deduplicate by URL
  const seen = new Set();
  const unique = allPosts.filter(p => {
    if (seen.has(p.url)) return false;
    seen.add(p.url);
    return true;
  });

  // Sort by relevance score descending
  unique.sort((a, b) => (b._relevance || 0) - (a._relevance || 0));

  const results = unique.slice(0, OUTPUT_LIMIT);

  console.error(`\n[done] ${results.length} leads | top scores: ${results.slice(0, 5).map(p => p._relevance).join(', ')}`);
  console.log(JSON.stringify(results, null, 2));
})();
