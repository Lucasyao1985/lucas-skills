const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;

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

const sleep = ms => new Promise(r => setTimeout(r, ms));

function extract(html) {
  const clean = t => t.replace(/<br\s*\/?>/g, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').trim();
  let desc = '';
  const m = html.match(/<div class="job-sec-text">([\s\S]*?)<\/div>\s*<\/div>/);
  if (m) desc = clean(m[1]);
  if (!desc) {
    const m2 = html.match(/<div class="text">([\s\S]*?)<\/div>/);
    if (m2) desc = clean(m2[1]);
  }
  const sal = (html.match(/<span class="salary">([^<]+)<\/span>/) || html.match(/"salaryDesc":"([^"]+)"/) || [])[1] || '';
  const blocked = /security\.html|验证|请稍后再试|环境存在异常/.test(html.substring(0, 4000));
  return { desc, sal: sal ? clean(sal) : '', blocked };
}

(async () => {
  const jobs = JSON.parse(fs.readFileSync(path.join(DIR, '_jobs.json'), 'utf8'));
  const cookies = normalizeCookies(JSON.parse(fs.readFileSync(path.join(DIR, 'cookies.json'), 'utf8')));

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    locale: 'zh-CN',
    viewport: { width: 1600, height: 900 },
  });
  await context.addCookies(cookies);

  const results = [];
  for (let i = 0; i < jobs.length; i++) {
    const j = jobs[i];
    if (!j.href) continue;
    const url = 'https://www.zhipin.com' + j.href;
    let best = { desc: '', sal: '', blocked: false };

    for (let attempt = 1; attempt <= 3; attempt++) {
      const page = await context.newPage();
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 45000 });
        await page.waitForTimeout(3500 + attempt * 1500);
        await page.evaluate(() => window.scrollBy(0, 600)).catch(() => {});
        await page.waitForTimeout(1500);
        const html = await page.content();
        const r = extract(html);
        if (r.desc.length > best.desc.length) best = r;
        if (best.desc.length > 100) { await page.close().catch(() => {}); break; }
      } catch (e) {
        // 静默重试
      }
      await page.close().catch(() => {});
      await sleep(2500 * attempt);
    }

    results.push({ ...j, url, salary: best.sal || j.salary, desc: best.desc });
    console.log(`[${i + 1}/${jobs.length}] ${j.title} | 薪资:${best.sal || '?'} | JD:${best.desc.length}字${best.blocked ? ' [拦截]' : ''}`);
    await sleep(2000);
  }

  fs.writeFileSync(path.join(DIR, '_jobs_detail.json'), JSON.stringify(results, null, 2), 'utf8');
  console.log('\n已保存 _jobs_detail.json');
  await browser.close();
})();
