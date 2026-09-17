import requests, re
from pathlib import Path

SKILL_DIR = Path(r'C:\Users\Lucas\.claude\skills\linkedin-jobs')
cookies = {}
with open(SKILL_DIR / 'cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            cookies[parts[0].strip()] = parts[1].strip()
cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cookie': cookie_str,
})

# Search for these terms in ai-myshell company page + about page
for page in ['/about/', '/people/', '']:
    resp = s.get(f'https://www.linkedin.com/company/ai-myshell{page}', timeout=30)
    print(f'\n=== Page: {page} (status={resp.status_code}, size={len(resp.text)}) ===')

    # Look for all /in/ links
    in_links = re.findall(r'/in/([a-z0-9_-]+)', resp.text, re.IGNORECASE)
    in_links = list(set(in_links))
    print(f'  /in/ links: {in_links[:20]}')

    # Look for specific terms
    for term in ['Developer Growth', 'developer growth', 'Passionate', 'DevRel',
                 'Developer Relations', 'Developer Advocate', 'Coding']:
        if term.lower() in resp.text.lower():
            idx = resp.text.lower().find(term.lower())
            snippet = resp.text[max(0,idx-200):idx+300]
            snippet = re.sub(r'<[^>]+>', ' ', snippet)
            snippet = re.sub(r'\\s+', ' ', snippet)
            print(f'  TERM \"{term}\" at pos {idx}: ...{snippet[:250]}...')
            near = re.findall(r'/in/([a-z0-9_-]+)', snippet, re.IGNORECASE)
            if near:
                print(f'    Near links: {near}')

print('\nDone.')
