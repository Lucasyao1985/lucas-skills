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

// Cookie-Editor / EditThisCookie 导出的 JSON 含 sameSite:null、expirationDate、storeId 等字段，
// Playwright addCookies 会抛 "cookies[0].sameSite: expected one of (Strict|Lax|None)" 直接崩。
// 必须先清洗。
function normalizeCookies(raw) {
  const out = [];
  for (const c of raw) {
    if (!c || !c.name || typeof c.value !== 'string') continue;
    const item = { name: c.name, value: c.value, path: c.path || '/' };
    if (c.domain) item.domain = c.domain; else item.url = 'https://www.zhipin.com';
    const exp = c.expirationDate ?? c.expires;
    if (typeof exp === 'number' && exp > 0) item.expires = exp;
    if (typeof c.httpOnly === 'boolean') item.httpOnly = c.httpOnly;
    if (typeof c.secure === 'boolean') item.secure = c.secure;
    if (['Strict', 'Lax', 'None'].includes(c.sameSite)) item.sameSite = c.sameSite;
    out.push(item);
  }
  return out;
}

(async () => {
  console.log('🔍 验证 BOSS直聘 Cookie 有效性...\n');

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome',
    args: ['--no-sandbox'],
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
    console.log(`📦 从 cookies.json 加载了 ${cookies.length} 个 cookie`);
  }
  if (cookies.length === 0 && fs.existsSync(COOKIES_FILE)) {
    cookies = parseCookies(fs.readFileSync(COOKIES_FILE, 'utf8').trim());
    console.log(`📦 从 cookies.txt 加载了 ${cookies.length} 个 cookie`);
  }

  if (cookies.length === 0) {
    console.log('❌ 没有找到任何 cookie！需要先登录。');
    await browser.close();
    process.exit(1);
  }

  // 清洗后再注入（见文件顶部 normalizeCookies 说明）
  const rawCount = cookies.length;
  cookies = normalizeCookies(cookies);
  if (cookies.length !== rawCount) {
    console.log(`🧹 cookie 清洗: ${rawCount} -> ${cookies.length}`);
  }

  // Check cookie expiry
  const now = Date.now() / 1000;
  let expiredCount = 0;
  let validCookies = [];
  for (const c of cookies) {
    if (c.expires && c.expires < now) {
      expiredCount++;
    } else {
      validCookies.push(c);
    }
  }
  console.log(`⏰ 有效 cookie: ${validCookies.length} 个, 已过期: ${expiredCount} 个\n`);

  if (validCookies.length === 0) {
    console.log('❌ 所有 cookie 都已过期！需要重新登录。');
    await browser.close();
    process.exit(1);
  }

  await context.addCookies(cookies);

  // Test 1: Visit homepage
  console.log('📍 测试 1: 访问首页...');
  const page = await context.newPage();
  await page.goto('https://www.zhipin.com/web/geek/job?query=AI&city=101020100', {
    waitUntil: 'domcontentloaded',
    timeout: 20000
  });
  await page.waitForTimeout(3000);

  const url1 = page.url();
  console.log(`   当前URL: ${url1.substring(0, 80)}...`);

  if (url1.includes('verify') || url1.includes('passport')) {
    console.log('   ❌ 被重定向到验证/登录页 — Cookie 失效！');
  } else {
    console.log('   ✅ 正常访问搜索页');
  }

  // Test 2: Visit a specific job detail page
  console.log('\n📍 测试 2: 访问职位详情页...');
  await page.goto('https://www.zhipin.com/job_detail/6e564fb451284c870nV62NW0FVdV.html', {
    waitUntil: 'domcontentloaded',
    timeout: 20000
  });
  await page.waitForTimeout(3000);

  const url2 = page.url();
  console.log(`   当前URL: ${url2.substring(0, 80)}...`);

  if (url2.includes('verify') || url2.includes('passport')) {
    console.log('   ❌ 被重定向到验证/登录页 — Cookie 失效！');
  } else {
    // Try to find job title
    const title = await page.title();
    console.log(`   页面标题: ${title}`);

    // Check for key elements
    const hasJobName = await page.$('.job-name, .name, [class*="job-name"]');
    const hasChatBtn = await page.$('text=立即沟通');
    const hasApplyBtn = await page.$('text=投递简历');

    if (hasJobName) {
      console.log('   ✅ 找到职位名称元素');
    }
    if (hasChatBtn) {
      console.log('   ✅ 找到"立即沟通"按钮');
    }
    if (hasApplyBtn) {
      console.log('   ✅ 找到"投递简历"按钮');
    }

    if (!url2.includes('passport') && !url2.includes('login')) {
      console.log('   ✅ 职位详情页可正常访问');
    }
  }

  // Test 3: Check API
  console.log('\n📍 测试 3: 测试搜索 API...');
  try {
    const apiResult = await page.evaluate(async () => {
      const r = await fetch('https://www.zhipin.com/wapi/zpgeek/search/joblist.json?query=AI&city=101020100&page=1&pageSize=5', {
        credentials: 'include'
      });
      return await r.json();
    });
    if (apiResult.code === 0) {
      console.log(`   ✅ API 正常，返回 ${apiResult.zpData?.resCount || '?'} 个结果`);
    } else {
      console.log(`   ⚠️ API 返回: code=${apiResult.code}, message=${apiResult.message}`);
    }
  } catch (e) {
    console.log(`   ❌ API 调用失败: ${e.message.substring(0, 100)}`);
  }

  // Summary
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const allPass = !url1.includes('passport') && !url2.includes('passport') && !url1.includes('verify') && !url2.includes('verify');
  if (allPass) {
    console.log('✅ Cookie 有效！可以正常使用 BOSS直聘');
  } else {
    console.log('❌ Cookie 已失效，需要重新登录');
    console.log('   操作方法:');
    console.log('   1. 在弹出的 Chrome 窗口中登录 zhipin.com');
    console.log('   2. 登录后关闭浏览器，cookie 会自动保存');
    console.log('   3. 或者手动导出 cookie 到 cookies.txt');
  }

  // Save updated cookies
  const newCookies = await context.cookies();
  fs.writeFileSync(COOKIE_JSON_FILE, JSON.stringify(newCookies, null, 2));
  console.log('\n💾 已更新 cookie 到 cookies.json');

  await page.waitForTimeout(2000);
  await browser.close();
})();
