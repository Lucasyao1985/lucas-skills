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
const pageSize = parseInt(args[2]) || 30;
const pageNum = parseInt(args[3]) || 1;
const experience = args[4] || '';  // 经验: 103=应届,104=1-3年,105=3-5年,106=5-10年,107=10年以上
const degree = args[5] || '';     // 学历: 203=大专,204=本科,205=硕士,206=博士
const salary = args[6] || '';     // 薪资: 403=3-5K,404=5-10K,405=10-20K,406=20-50K,407=50K+

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

  // Set up response listener before navigating
  let apiResult = null;
  const apiPromise = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('API timeout after 30s')), 30000);
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/wapi/zpgeek/search/joblist.json')) {
        try {
          const json = await response.json();
          if (json.code === 0) {
            clearTimeout(timeout);
            resolve(json);
          }
        } catch (e) {}
      }
    });
  });

  // Navigate to search page
  let searchUrl = `https://www.zhipin.com/web/geek/job?query=${encodeURIComponent(keyword)}&city=${cityCode}`;
  if (experience) searchUrl += `&experience=${experience}`;
  if (degree) searchUrl += `&degree=${degree}`;
  if (salary) searchUrl += `&salary=${salary}`;
  await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

  // Check for verify page
  await page.waitForTimeout(2000);
  const currentUrl = page.url();
  if (currentUrl.includes('verify') || currentUrl.includes('passport')) {
    console.error(JSON.stringify({ error: 'NEED_VERIFY', message: '需要在浏览器中完成验证。请在弹出的浏览器窗口中完成验证。' }));
    // Wait for user to complete verification (up to 2 minutes)
    try {
      await page.waitForURL(url => !url.toString().includes('verify') && !url.toString().includes('passport'), { timeout: 120000 });
      await page.waitForTimeout(2000);
      // Retry navigation after verification
      await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch (e) {
      await browser.close();
      process.exit(1);
    }
  }

  try {
    apiResult = await apiPromise;
  } catch (e) {
    // Fallback: try fetch from page context
    await page.waitForTimeout(3000);
    try {
      apiResult = await page.evaluate(async ({ keyword, cityCode, pageNum, pageSize, experience, degree, salary }) => {
        let apiUrl = `https://www.zhipin.com/wapi/zpgeek/search/joblist.json?query=${encodeURIComponent(keyword)}&city=${cityCode}&page=${pageNum}&pageSize=${pageSize}`;
        if (experience) apiUrl += `&experience=${experience}`;
        if (degree) apiUrl += `&degree=${degree}`;
        if (salary) apiUrl += `&salary=${salary}`;
        const r = await fetch(apiUrl, { credentials: 'include' });
        return await r.json();
      }, { keyword, cityCode, pageNum, pageSize, experience, degree, salary });
    } catch (e2) {
      console.error(JSON.stringify({ error: 'Both methods failed', details: e2.message }));
      await browser.close();
      process.exit(1);
    }
  }

  // Save updated cookies
  const newCookies = await context.cookies();
  fs.writeFileSync(COOKIE_JSON_FILE, JSON.stringify(newCookies, null, 2));

  await browser.close();
  console.log(JSON.stringify(apiResult, null, 2));
})();
