const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const COOKIES_FILE = path.join(__dirname, 'cookies.txt');
const COOKIE_JSON_FILE = path.join(__dirname, 'cookies.json');

function parseCookies(cookieStr) {
  return cookieStr.split('; ').filter(c => c.trim()).map(c => {
    const idx = c.indexOf('=');
    const name = c.substring(0, idx).trim();
    const value = c.substring(idx + 1);
    return { name, value, domain: '.zhipin.com', path: '/' };
  });
}

const args = process.argv.slice(2);
const keyword = args[0] || '';
const cityCode = args[1] || '101020100';
const gender = args[2] || '';  // 性别: 0=不限, 1=男, 2=女

(async () => {
  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome',
    args: [
      '--no-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-infobars',
      '--disable-sync',
      '--disable-extensions',
    ],
    ignoreDefaultArgs: ['--enable-automation'],
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    locale: 'zh-CN',
    viewport: { width: 1920, height: 1080 },
  });

  // Load cookies
  let cookies = [];
  if (fs.existsSync(COOKIE_JSON_FILE)) {
    try { cookies = JSON.parse(fs.readFileSync(COOKIE_JSON_FILE, 'utf8')); } catch (e) {}
  }
  if (cookies.length === 0 && fs.existsSync(COOKIES_FILE)) {
    cookies = parseCookies(fs.readFileSync(COOKIES_FILE, 'utf8').trim());
  }
  if (cookies.length > 0) {
    await context.addCookies(cookies);
  }

  const page = await context.newPage();

  // Stealth patches
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
  });

  // Set up response listener
  let apiResult = null;
  const apiPromise = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('API timeout after 30s')), 30000);
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/wapi/zpgeek/search') || url.includes('/wapi/boss/search') || url.includes('/wapi/zpjob/search') || url.includes('geek/list') || url.includes('talent')) {
        try {
          const text = await response.text();
          try {
            const json = JSON.parse(text);
            if (json.code === 0 || json.zpData) {
              clearTimeout(timeout);
              resolve(json);
            }
          } catch (e) {}
        } catch (e) {}
      }
    });
  });

  // Navigate to boss search page (talent search)
  let searchUrl = `https://www.zhipin.com/web/boss/search?query=${encodeURIComponent(keyword)}&city=${cityCode}`;
  if (gender) searchUrl += `&gender=${gender}`;

  await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Check for verify page
  const currentUrl = page.url();
  if (currentUrl.includes('verify') || currentUrl.includes('passport')) {
    console.error(JSON.stringify({ error: 'NEED_VERIFY', message: '需要在浏览器中完成验证。请在弹出的浏览器窗口中完成验证。' }));
    try {
      await page.waitForURL(url => !url.toString().includes('verify') && !url.toString().includes('passport'), { timeout: 120000 });
      await page.waitForTimeout(2000);
      await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch (e) {
      await browser.close();
      process.exit(1);
    }
  }

  // Check if redirected to job seeker page (means account is not a boss account)
  await page.waitForTimeout(2000);
  const finalUrl = page.url();
  if (finalUrl.includes('/web/geek/')) {
    console.error(JSON.stringify({
      error: 'NOT_BOSS_ACCOUNT',
      message: '当前账号是求职者账号，无法搜索候选人。需要招聘者（Boss）账号才能搜索牛人。',
      redirectUrl: finalUrl
    }));
    await browser.close();
    process.exit(1);
  }

  try {
    apiResult = await apiPromise;
  } catch (e) {
    // Try fetching all responses from the page
    console.error(JSON.stringify({ error: 'No API response captured', pageUrl: page.url() }));
    await browser.close();
    process.exit(1);
  }

  // Save updated cookies
  const newCookies = await context.cookies();
  fs.writeFileSync(COOKIE_JSON_FILE, JSON.stringify(newCookies, null, 2));

  await browser.close();
  console.log(JSON.stringify(apiResult, null, 2));
})();
