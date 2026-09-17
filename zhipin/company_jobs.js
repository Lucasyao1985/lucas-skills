const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const TARGET = process.argv[2] || 'https://www.zhipin.com/gongsi/job/cf035bb8b8e7aba81XJ809y-.html?ka=company-jobs';

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
  const cookies = normalizeCookies(JSON.parse(fs.readFileSync(path.join(DIR, 'cookies.json'), 'utf8')));
  console.log(`Cookie: ${cookies.length} 个`);

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    locale: 'zh-CN',
    viewport: { width: 1920, height: 1080 },
  });
  await context.addCookies(cookies);

  const page = await context.newPage();

  // 完整保存所有 zpgeek / joblist 类接口响应
  const hits = [];
  page.on('response', async (r) => {
    const u = r.url();
    if (/zhipin\.com/.test(u) && /(joblist|joblist\.json|job\/list|company|geek\/search)/i.test(u) && !/\.(png|jpg|gif|css|js|woff)/i.test(u)) {
      try {
        const body = await r.text();
        hits.push({ url: u, body });
      } catch (e) {}
    }
  });

  try {
    await page.goto(TARGET, { waitUntil: 'load', timeout: 60000 });
  } catch (e) {
    console.log('goto 异常:', e.message.substring(0, 120));
  }
  await page.waitForTimeout(6000);

  console.log('URL:', page.url());
  console.log('标题:', await page.title());

  for (let i = 0; i < 10; i++) {
    await page.evaluate(() => window.scrollBy(0, 1400)).catch(() => {});
    await page.waitForTimeout(1000);
  }

  let html = '';
  try { html = await page.content(); } catch (e) { console.log('content 失败:', e.message.substring(0, 80)); }
  fs.writeFileSync(path.join(DIR, '_page_full.html'), html, 'utf8');

  let text = '';
  try { text = await page.evaluate(() => document.body ? document.body.innerText : ''); } catch (e) {}
  fs.writeFileSync(path.join(DIR, '_page_full.txt'), text, 'utf8');

  console.log('HTML 长度:', html.length, '| 正文长度:', text.length);
  console.log('接口命中:', hits.length);
  hits.forEach((h, i) => {
    const f = path.join(DIR, `_hit_${i}.json`);
    fs.writeFileSync(f, h.body, 'utf8');
    console.log(`  [${i}] ${h.url.substring(0, 130)} -> ${h.body.length} 字节`);
  });

  await browser.close();
})();
