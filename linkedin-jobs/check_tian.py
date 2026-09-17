import requests, re
from pathlib import Path
cookies = {}
with open(r'C:/Users/Lucas/.claude/skills/linkedin-jobs/cookies.txt', 'r', encoding='utf-8') as f:
    for l in f:
        p = l.strip().split('\t')
        if len(p) >= 2: cookies[p[0].strip()] = p[1].strip()
s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html',
    'Cookie': '; '.join(f'{k}={v}' for k,v in cookies.items()),
})

# Try Zengyi Qin patterns
patterns = [
    'zengyi-qin', 'qin-zengyi', 'zengyiqin', 'zengyi',
    'qinzengyi', 'zengyi-qin-mit', 'zengyi-qin-phd',
    'zqin', 'zengyi-q', 'qinzy', 'zengyiqin-mit',
    'zengyi-qin-myshell', 'charles-zengyi-qin',
]

for slug in patterns:
    url = f'https://www.linkedin.com/in/{slug}/'
    try:
        r = s.get(url, timeout=8, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 30000:
            t = re.search(r'<title>(.*?)</title>', r.text)
            print(f'FOUND: {url} -> {t.group(1) if t else "?"}')
        else:
            print(f'  {slug}: {r.status_code}')
    except Exception as e:
        print(f'  {slug}: ERR')
