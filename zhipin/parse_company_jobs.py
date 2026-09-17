# -*- coding: utf-8 -*-
import io, re, json

P = r"C:\Users\Lucas\.claude\skills\zhipin\_company.html"
s = io.open(P, encoding="utf-8", errors="replace").read()

# ---------- 1. 按 job-card-box 切块（避免被嵌套 <li> 截断） ----------
parts = s.split('class="job-card-box')
cards = []
for seg in parts[1:]:
    seg = seg[:3000]
    a = re.search(r'<a href="(/job_detail/[^"]+\.html)"[^>]*class="job-name"[^>]*>([^<]+)</a>', seg)
    if not a:
        a = re.search(r'class="job-name"[^>]*>([^<]+)</a>', seg)
        if not a:
            continue
        href, title = '', a.group(1)
    else:
        href, title = a.group(1), a.group(2)

    tags_ul = re.search(r'<ul class="tag-list"[^>]*>(.*?)</ul>', seg, re.S)
    tags = [t.strip() for t in re.findall(r'<li[^>]*>([^<]+)</li>', tags_ul.group(1))] if tags_ul else []
    loc = re.search(r'class="company-location"[^>]*>\s*<a[^>]*>([^<]+)</a>', seg)
    boss = re.search(r'class="boss-name"[^>]*>([^<]+)<', seg)
    sal = re.search(r'class="job-salary"[^>]*>([^<]*)<', seg)

    cards.append({
        'title': title.replace('招聘', '').strip(),
        'href': href,
        'tags': tags,
        'city': loc.group(1).strip() if loc else '',
        'boss': boss.group(1).strip() if boss else '',
        'salary_dom': (sal.group(1).strip() if sal else ''),
    })

# ---------- 2. 压缩对象里的 salaryDesc 变量 ----------
pairs = re.findall(r'encryptJobId:"([^"]+)",expectId:[^,]*,jobName:"([^"]*)"', s)
sal_var = {}
for m in re.finditer(r'encryptJobId:"([^"]+)"', s):
    jid = m.group(1)
    seg = s[m.start():m.start() + 1500]
    dm = re.search(r'salaryDesc:("(?:[^"\\]|\\.)*"|[A-Za-z_$][A-Za-z0-9_$]{0,3})', seg)
    if dm and dm.group(1).startswith('"'):
        sal_var[jid] = dm.group(1)[1:-1]
    elif dm:
        sal_var[jid] = '<var:%s>' % dm.group(1)

# ---------- 3. 找 IIFE 的参数值（用于解 var 引用） ----------
iife_args = {}
try:
    tail = s[s.rfind('})('):]
    raw = tail[3:tail.index(')', 3)] if ')' in tail[3:] else ''
    vals, buf, in_str, esc = [], '', None, False
    for ch in raw:
        if esc: buf += ch; esc = False; continue
        if ch == '\\': buf += ch; esc = True; continue
        if in_str:
            buf += ch
            if ch == in_str: in_str = None
            continue
        if ch in '"\'`': in_str = ch; buf += ch; continue
        if ch == ',': vals.append(buf.strip()); buf = ''; continue
        buf += ch
    if buf.strip(): vals.append(buf.strip())
    print('IIFE 参数个数:', len(vals))
    print('前 40 个:', vals[:40])
except Exception as e:
    print('IIFE 解析失败:', e)

for c in cards:
    jid = c['href'].rsplit('/', 1)[-1].replace('.html', '') if c['href'] else ''
    c['salary'] = sal_var.get(jid, '') or c['salary_dom']

json.dump(cards, io.open(r"C:\Users\Lucas\.claude\skills\zhipin\_jobs.json", 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

print(f"\n共 {len(cards)} 个职位\n" + "=" * 112)
for c in cards:
    print(f"{c['title']:<28} | {' / '.join(c['tags']):<16} | {c['city']:<6} | {c['salary']:<12} | {c['boss']}")
print("\n已保存 _jobs.json")
