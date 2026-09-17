#!/usr/bin/env python3
"""Generate a filterable HTML page from matched_jobs.json"""
import json, sys, re
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent
MATCHED_JSON = SKILL_DIR / "matched_jobs.json"
EXPIRED_JSON = SKILL_DIR / "expired_ids.json"  # job IDs, not URLs

def extract_job_id(url):
    m = re.search(r'(\d{8,12})(?:\?|/|$)', url)
    return m.group(1) if m else None

# Find latest matched_jobs JSON or use default
if not MATCHED_JSON.exists():
    print(f"ERROR: {MATCHED_JSON} not found")
    sys.exit(1)

with open(MATCHED_JSON, 'r', encoding='utf-8') as f:
    jobs = json.load(f)

# Step 0: Filter out garbage URLs (collections, recommended, etc.)
jobs = [j for j in jobs if '/collections/' not in (j.get('url', '') or '')]

# Step 1: Deduplicate by job ID (cross-subdomain)
id_seen = set()
id_unique = []
for j in jobs:
    jid = extract_job_id(j.get('url', '') or '')
    if jid and jid not in id_seen:
        id_seen.add(jid)
        id_unique.append(j)
    elif not jid:
        id_unique.append(j)  # keep jobs without IDs

# Normalize all URLs to www.linkedin.com for consistency
for j in id_unique:
    url = j.get('url', '') or ''
    j['url'] = re.sub(r'https?://[a-z]{2,3}\.linkedin\.com', 'https://www.linkedin.com', url)

# Step 2: Deduplicate by company — keep highest score per normalized company name
def norm_company(name):
    if not name:
        return ''
    n = name.strip().lower()
    # Remove common suffixes that don't help distinguish
    for suffix in [' inc', ' inc.', ' llc', ' llc.', ' ltd', ' ltd.', ' corp', ' corp.',
                   ' limited', ' co.', ' co', ' plc', ' gmbh', ' s.l.', ' s.a.', ' pte']:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
    return n.strip()

company_best = {}
for j in id_unique:
    ckey = norm_company(j.get('company', ''))
    if ckey not in company_best or j['score'] > company_best[ckey]['score']:
        company_best[ckey] = j

# Sort by score descending
unique = sorted(company_best.values(), key=lambda j: j['score'], reverse=True)

removed_dup = len(jobs) - len(id_unique)
removed_company = len(id_unique) - len(unique)

# Step 3: Filter out expired jobs (match by job ID, not URL)
expired_ids = set()
if EXPIRED_JSON.exists():
    with open(EXPIRED_JSON, 'r', encoding='utf-8') as f:
        expired_ids = set(json.load(f))
    pre_expired = len(unique)
    unique = [j for j in unique if extract_job_id(j.get('url','') or '') not in expired_ids]
    removed_expired = pre_expired - len(unique)
    print(f'After expired filter: {len(unique)} jobs (removed {removed_expired} expired)')
else:
    removed_expired = 0

# Step 4: Cross-reference with applied/saved jobs from check_responses.py
RESPONSES_JSON = SKILL_DIR / "responses.json"
applied_norm = set()
saved_norm = set()
applied_urls = {}  # norm_company -> applied job url
saved_urls = {}    # norm_company -> saved job url
if RESPONSES_JSON.exists():
    with open(RESPONSES_JSON, 'r', encoding='utf-8') as f:
        resp_data = json.load(f)
    for a in resp_data.get("applied", []):
        cn = norm_company(a.get("company", ""))
        if cn:
            applied_norm.add(cn)
            applied_urls[cn] = a.get("url", "")
    for s in resp_data.get("saved", []):
        cn = norm_company(s.get("company", ""))
        if cn:
            saved_norm.add(cn)
            saved_urls[cn] = s.get("url", "")
    print(f'Cross-ref: {len(applied_norm)} applied companies, {len(saved_norm)} saved companies')

# Annotate each job with applied/saved status
for j in unique:
    cn = norm_company(j.get("company", ""))
    j["applied"] = cn in applied_norm
    j["saved"] = cn in saved_norm
    if j["applied"]:
        j["applied_url"] = applied_urls.get(cn, "")
    if j["saved"]:
        j["saved_url"] = saved_urls.get(cn, "")

unapplied = [j for j in unique if not j["applied"]]
applied_jobs_list = [j for j in unique if j["applied"]]

# Groups (calculated AFTER all filters)
high = [j for j in unique if j['score'] >= 20]
mid = [j for j in unique if 10 <= j['score'] < 20]
low = [j for j in unique if j['score'] < 10]
builder = [j for j in unique if sum(1 for m in j.get('matched_skills', []) if m.startswith('\U0001f511')) >= 3]

cn_jobs = [j for j in unique if any(w in (j.get('location', '') or '') for w in [
    '上海', '北京', '深圳', '广州', '杭州', '朝阳', '浦东', '徐汇', '中国', 'China'])]
remote_jobs = [j for j in unique if any(w in (j.get('location', '') or '').lower() for w in [
    'remote', '远程', 'worldwide', '全球'])]
us_jobs = [j for j in unique if any(w in (j.get('location', '') or '') for w in [
    '美国', 'United States', 'San Francisco', 'Bay Area', 'CA',
    'New York', 'Seattle', 'Austin', 'Mountain View', 'Palo Alto'])]

date_str = datetime.now().strftime('%Y-%m-%d')
html_path = SKILL_DIR / f'职位投递列表_{date_str}.html'

# Build JSON embedded in HTML
jobs_json = json.dumps(unique, ensure_ascii=False)

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; max-width: 1200px; margin: 0 auto; }
h1 { color: #58a6ff; margin-bottom: 4px; }
.subtitle { color: #8b949e; font-size: 13px; margin-bottom: 20px; }
.stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px 16px; min-width: 70px; text-align: center; cursor: pointer; transition: border-color 0.2s; }
.stat:hover { border-color: #58a6ff; }
.stat-num { font-size: 24px; font-weight: 700; color: #58a6ff; }
.stat-label { font-size: 11px; color: #8b949e; margin-top: 2px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
.filters button { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.filters button:hover { background: #30363d; }
.filters button.active { background: #1f6feb; border-color: #1f6feb; color: #fff; }
.filters input { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 6px; font-size: 13px; width: 220px; }
.filters input:focus { outline: none; border-color: #58a6ff; }
.job-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 8px; transition: border-color 0.2s; }
.job-card:hover { border-color: #58a6ff; }
.job-card.top { border-left: 3px solid #d29922; }
.job-card.builder { border-left: 3px solid #3fb950; }
.job-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.job-title a { color: #58a6ff; text-decoration: none; }
.job-title a:hover { text-decoration: underline; }
.job-meta { font-size: 13px; color: #8b949e; margin-bottom: 8px; display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
.score-badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; }
.score-high { background: #238636; color: #fff; }
.score-mid { background: #9e6a03; color: #fff; }
.score-low { background: #30363d; color: #8b949e; }
.skills { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.skill { font-size: 11px; padding: 3px 8px; border-radius: 10px; background: #21262d; color: #8b949e; border: 1px solid #30363d; }
.skill.key { background: #1b3a1b; color: #3fb950; border-color: #238636; }
.no-results { text-align: center; padding: 60px; color: #8b949e; }
.loc-cn { color: #f85149; }
.loc-remote { color: #3fb950; }
.loc-us { color: #58a6ff; }
.counter { color: #8b949e; font-size: 13px; }
.footer { text-align: center; color: #484f58; font-size: 11px; margin-top: 40px; padding: 20px; }
.applied-row { opacity: 0.5; }
.applied-row .job-title a { color: #8b949e; }
.btn-apply { display: inline-block; background: #238636; color: #fff; padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: none; margin-left: 8px; text-decoration: none; }
.btn-apply:hover { background: #2ea043; }
.badge-applied { display: inline-block; background: #9e6a03; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 6px; }
.badge-saved { display: inline-block; background: #30363d; color: #8b949e; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 6px; }
.job-card.applied { opacity: 0.55; }
.job-card.applied:hover { opacity: 0.85; }
"""

JS = """
function locationTag(loc) {
    if (!loc) return '';
    if (/上海|北京|深圳|广州|杭州|朝阳|浦东|徐汇|中国/.test(loc)) return 'cn';
    if (/San Francisco|Bay Area|Mountain View|Palo Alto|San Jose|Sunnyvale|Santa Clara|Cupertino|CA|United States|Seattle|New York|Austin|美国/.test(loc)) return 'us';
    if (/remote|Remote|远程|Worldwide|全球/.test(loc)) return 'remote';
    return '';
}

function hasBuilder(job) {
    if (!job.matched_skills) return false;
    return job.matched_skills.filter(s => s.startsWith('\U0001f511')).length >= 3;
}

function renderJobCard(job, idx) {
    const score = job.score || 0;
    let scoreClass = score >= 20 ? 'score-high' : (score >= 10 ? 'score-mid' : 'score-low');
    const isBuilder = hasBuilder(job);
    const cardClass = (isBuilder ? 'builder ' : '') + (score >= 20 ? 'top ' : '') + (job.applied ? 'applied ' : '');
    const locTag = locationTag(job.location || '');
    const locClass = locTag === 'cn' ? 'loc-cn' : (locTag === 'remote' ? 'loc-remote' : (locTag === 'us' ? 'loc-us' : ''));

    let skillsHtml = '';
    const skills = job.matched_skills || [];
    const shown = skills.slice(0, 12);
    for (const s of shown) {
        const isKey = s.startsWith('\U0001f511');
        const label = s.replace(/^[^\\w一-鿿]+\\s*/, '');
        skillsHtml += '<span class=\"skill' + (isKey ? ' key' : '') + '\">' + label + '</span>';
    }
    if (skills.length > 12) skillsHtml += '<span class=\"skill\">+' + (skills.length - 12) + ' more</span>';

    const url = job.url || '#';
    const appliedUrl = job.applied_url || job.url || '#';
    let badges = '';
    if (job.applied) badges += '<a href=\"' + appliedUrl + '\" target=\"_blank\" class=\"badge-applied\">已投递</a>';
    if (job.saved) badges += '<a href=\"' + (job.saved_url || job.url || '#') + '\" target=\"_blank\" class=\"badge-saved\">已保存</a>';

    const applyBtn = job.applied
        ? '<a href=\"' + appliedUrl + '\" target=\"_blank\" class=\"btn-apply\" style=\"background:#30363d;\">查看</a>'
        : '<a href=\"' + url + '\" target=\"_blank\" class=\"btn-apply\">投递</a>';

    return '<div class=\"job-card ' + cardClass + '\" data-score=\"' + score + '\" data-location=\"' + locTag + '\" data-builder=\"' + isBuilder + '\" data-applied=\"' + (job.applied ? '1' : '0') + '\" data-search=\"' + ((job.title||'') + ' ' + (job.company||'')).toLowerCase() + '\">'
        + '<div class=\"job-title\"><a href=\"' + url + '\" target=\"_blank\" rel=\"noopener\">' + (job.title || '?') + '</a>'
        + badges
        + applyBtn + '</div>'
        + '<div class=\"job-meta\">'
        + '<span>公司: ' + (job.company || '?') + '</span>'
        + '<span class=\"' + locClass + '\">地点: ' + (job.location || '?') + '</span>'
        + '<span class=\"score-badge ' + scoreClass + '\">' + score + '分</span>'
        + (isBuilder ? '<span class=\"score-badge score-high\">AI Builder</span>' : '')
        + '</div>'
        + '<div class=\"skills\">' + skillsHtml + '</div>'
        + '</div>';
}

function render(jobs) {
    const el = document.getElementById('job-list');
    if (jobs.length === 0) {
        el.innerHTML = '<div class=\"no-results\">没有匹配的职位</div>';
    } else {
        el.innerHTML = jobs.map(renderJobCard).join('');
    }
    document.getElementById('counter').textContent = '显示 ' + jobs.length + ' 个岗位';
}

let currentJobs = JOBS;

function filterAll() {
    currentJobs = JOBS;
    render(currentJobs);
    setActive('btn-all');
}

function filterScore(min, max) {
    currentJobs = JOBS.filter(function(j) { return j.score >= min && j.score <= max; });
    render(currentJobs);
    setActive(min >= 20 ? 'btn-high' : 'btn-mid');
}

function filter(type) {
    if (type === 'builder') {
        currentJobs = JOBS.filter(hasBuilder);
        setActive('btn-builder');
    } else if (type === 'cn') {
        currentJobs = JOBS.filter(function(j) { return locationTag(j.location) === 'cn'; });
        setActive('btn-cn');
    } else if (type === 'remote') {
        currentJobs = JOBS.filter(function(j) { return locationTag(j.location) === 'remote'; });
        setActive('btn-remote');
    } else if (type === 'us') {
        currentJobs = JOBS.filter(function(j) { return locationTag(j.location) === 'us'; });
        setActive('btn-us');
    } else if (type === 'unapplied') {
        currentJobs = JOBS.filter(function(j) { return !j.applied; });
        setActive('btn-unapplied');
    } else if (type === 'applied') {
        currentJobs = JOBS.filter(function(j) { return j.applied; });
        setActive('btn-applied');
    }
    render(currentJobs);
}

function search(query) {
    if (!query.trim()) {
        filterAll();
        return;
    }
    var q = query.toLowerCase();
    currentJobs = JOBS.filter(function(j) {
        return (j.title || '').toLowerCase().indexOf(q) !== -1
            || (j.company || '').toLowerCase().indexOf(q) !== -1
            || (j.matched_skills || []).some(function(s) { return s.toLowerCase().indexOf(q) !== -1; });
    });
    render(currentJobs);
    document.querySelectorAll('.filters button').forEach(function(b) { b.classList.remove('active'); });
}

function setActive(id) {
    document.querySelectorAll('.filters button').forEach(function(b) { b.classList.remove('active'); });
    var btn = document.getElementById(id);
    if (btn) btn.classList.add('active');
}

// Init
render(JOBS);
"""

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>领英职位投递列表 — {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<h1>领英职位投递列表</h1>
<div class="subtitle">{len(unique)} 个岗位 (URL去重{removed_dup} + 公司去重{removed_company} + 过期剔除{removed_expired}) · 更新于 {date_str} · 点击职位在新标签页打开，在已登录 Chrome 中投递</div>

<div class="stats">
<div class="stat" onclick="filterAll()"><div class="stat-num">{len(unique)}</div><div class="stat-label">全部</div></div>
<div class="stat" onclick="filterScore(20,999)"><div class="stat-num">{len(high)}</div><div class="stat-label">高匹配 >=20</div></div>
<div class="stat" onclick="filterScore(10,19)"><div class="stat-num">{len(mid)}</div><div class="stat-label">中匹配</div></div>
<div class="stat" onclick="filter('builder')"><div class="stat-num">{len(builder)}</div><div class="stat-label">AI Builder</div></div>
<div class="stat" onclick="filter('cn')"><div class="stat-num">{len(cn_jobs)}</div><div class="stat-label">国内</div></div>
<div class="stat" onclick="filter('remote')"><div class="stat-num">{len(remote_jobs)}</div><div class="stat-label">远程</div></div>
<div class="stat" onclick="filter('us')"><div class="stat-num">{len(us_jobs)}</div><div class="stat-label">美国</div></div>
<div class="stat" onclick="filter('unapplied')"><div class="stat-num">{len(unapplied)}</div><div class="stat-label">未投递</div></div>
<div class="stat" onclick="filter('applied')"><div class="stat-num">{len(applied_jobs_list)}</div><div class="stat-label">已投递</div></div>
</div>

<div class="filters">
<button onclick="filterAll()" class="active" id="btn-all">全部</button>
<button onclick="filterScore(20,999)" id="btn-high">高匹配 >=20</button>
<button onclick="filterScore(10,19)" id="btn-mid">中匹配 10-19</button>
<button onclick="filter('builder')" id="btn-builder">AI Builder</button>
<button onclick="filter('cn')" id="btn-cn">国内</button>
<button onclick="filter('remote')" id="btn-remote">远程</button>
<button onclick="filter('us')" id="btn-us">美国</button>
<button onclick="filter('unapplied')" id="btn-unapplied">未投递</button>
<button onclick="filter('applied')" id="btn-applied">已投递</button>
<input type="text" placeholder="搜索公司/职位/技能..." oninput="search(this.value)" id="search-input">
<span class="counter" id="counter">显示 {len(unique)} 个岗位</span>
</div>

<div id="job-list"></div>

<div class="footer">点击职位标题或「投递」按钮在新标签页打开 LinkedIn · 确保 Chrome 已登录领英 · 逐个检查 Easy Apply 并提交</div>

<script>
var JOBS = {jobs_json};
{JS}
</script>
</body>
</html>'''

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Saved: {html_path}')
print(f'Raw: {len(jobs)} | URL dedup: {len(id_unique)} (removed {removed_dup}) | Company dedup: {len(unique)} (removed {removed_company})')
print(f'High (>=20): {len(high)} | Mid (10-19): {len(mid)} | Low (<10): {len(low)}')
print(f'AI Builder: {len(builder)} | CN: {len(cn_jobs)} | Remote: {len(remote_jobs)} | US: {len(us_jobs)}')
