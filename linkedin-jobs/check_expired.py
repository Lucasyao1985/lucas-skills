#!/usr/bin/env python3
"""
Check all job URLs for expired listings ('no longer accepting applications').
Uses requests + li_at cookie — raw HTML detection, not Playwright.
Playwright's inner_text() cannot detect expired text embedded in JSON payloads.
"""
import json, time, sys, re, requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SKILL_DIR = Path(__file__).parent
COOKIE_FILE = SKILL_DIR / "cookies.txt"
MATCHED_JSON = SKILL_DIR / "matched_jobs.json"
EXPIRED_JSON = SKILL_DIR / "expired_ids.json"  # now stores job IDs, not URLs

# ── Parse li_at cookie ──
li_at = ''
with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip() and 'li_at' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                li_at = parts[1].strip()
                break

if not li_at:
    print("ERROR: li_at cookie not found")
    sys.exit(1)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cookie': f'li_at={li_at}',
}

# ── Load jobs ──
if not MATCHED_JSON.exists():
    print(f"ERROR: {MATCHED_JSON} not found")
    sys.exit(1)

with open(MATCHED_JSON, 'r', encoding='utf-8') as f:
    jobs = json.load(f)

print(f"Loaded {len(jobs)} jobs from {MATCHED_JSON.name}")

# ── Helper: extract LinkedIn job ID from URL ──
def extract_job_id(url):
    m = re.search(r'(\d{8,12})(?:\?|/|$)', url)
    return m.group(1) if m else None

# ── Load previously known expired job IDs ──
known_expired_ids = set()
if EXPIRED_JSON.exists():
    with open(EXPIRED_JSON, 'r', encoding='utf-8') as f:
        known_expired_ids = set(json.load(f))
    print(f"Known expired IDs: {len(known_expired_ids)}")

# ── Check each URL ──
EXPIRED_PHRASES = [
    'no longer accepting applications',
    'this job has expired',
    'this job is no longer accepting',
]
# NOTE: removed 'this job is no longer' — it matches LinkedIn toast
# "this job is no longer saved" (false positive).
# Also removed bare 'job expired' — matches UI elements.

new_expired_ids = set()
checked = 0

for idx, job in enumerate(jobs, 1):
    url = job.get('url', '')
    if not url:
        continue
    jid = extract_job_id(url)
    if not jid:
        continue
    if jid in known_expired_ids or jid in new_expired_ids:
        continue

    # Normalize to www.linkedin.com — localized subdomains (es, jp, cn, etc.)
    # may serve cached content that doesn't show expired status.
    url = re.sub(r'https?://[a-z]{2,3}\.linkedin\.com', 'https://www.linkedin.com', url)

    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        body = resp.text.lower()

        if any(p in body for p in EXPIRED_PHRASES):
            new_expired_ids.add(jid)
            print(f'[{idx}] EXPIRED: {job["title"][:70]} | {job.get("company","?")}')

        checked += 1
        if checked % 50 == 0:
            print(f'  {checked} checked, {len(new_expired_ids)} new expired')

        time.sleep(0.3)

    except Exception as e:
        print(f'[{idx}] Error: {str(e)[:60]}')
        continue

# ── Merge and save (store job IDs, not URLs) ──
all_expired_ids = known_expired_ids | new_expired_ids
with open(EXPIRED_JSON, 'w', encoding='utf-8') as f:
    json.dump(sorted(all_expired_ids), f, ensure_ascii=False, indent=2)

print(f'\nChecked: {checked}')
print(f'New expired: {len(new_expired_ids)}')
print(f'Total expired IDs: {len(all_expired_ids)}')
print(f'Clean jobs: {len(jobs) - len(all_expired_ids)}')
print(f'Saved: {EXPIRED_JSON.name}')
