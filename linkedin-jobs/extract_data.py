import re, json, sys, requests, urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SKILL_DIR = Path(r'C:\Users\Lucas\.claude\skills\linkedin-jobs')
COOKIE_FILE = SKILL_DIR / "cookies.txt"

cookies = {}
with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            cookies[parts[0].strip()] = parts[1].strip()

cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
jsessionid = cookies.get('JSESSIONID', '').replace('"', '')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36',
    'Accept': 'application/vnd.linkedin.normalized+json+2.1',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cookie': cookie_str,
    'csrf-token': jsessionid.replace('ajax:', ''),
    'x-restli-protocol-version': '2.0.0',
    'Referer': 'https://www.linkedin.com/company/myshell/people/',
}

session = requests.Session()
session.headers.update(headers)

# Call the DiscoverCardGroups API found in the About page
print("[1] Calling DiscoverCardGroups API...")

# The exact API URL from the page
url = ('https://www.linkedin.com/voyager/api/graphql?'
       'includeWebMetadata=true'
       '&variables=(memberTabType:ABOUT,organizationVanityName:myshell)'
       '&queryId=voyagerOrganizationDashDiscoverCardGroups.faf15cf2b3e5f1e8a9c0d4e7f6a5b3c1')

print(f'    URL: {url[:150]}...')
resp = session.get(url, timeout=30)
print(f'    Status: {resp.status_code}, size: {len(resp.text)}')

if resp.status_code == 200:
    data = resp.json()

    # Extract profiles
    def extract(obj, depth=0):
        results = []
        if depth > 10:
            return results
        if isinstance(obj, dict):
            fn = obj.get('firstName')
            ln = obj.get('lastName')
            if fn and ln and isinstance(fn, str) and isinstance(ln, str) and len(fn) > 0:
                name = f"{fn} {ln}"
                urn = obj.get('entityUrn', '')
                mid = ''
                if isinstance(urn, str):
                    m = re.search(r':(\d+)$', urn)
                    if m:
                        mid = m.group(1)
                url = f'https://www.linkedin.com/in/{mid}/' if mid else ''
                results.append({
                    'name': name,
                    'title': obj.get('headline', obj.get('occupation', '')),
                    'url': url,
                })
            for v in obj.values():
                results.extend(extract(v, depth + 1))
        elif isinstance(obj, list):
            for item in obj:
                results.extend(extract(item, depth + 1))
        return results

    people = extract(data)
    print(f'    Found {len(people)} people')
    for p in people:
        print(f'    - {p["name"]}: {p["title"][:80]}')

# Also try the candidate interest API
print(f'\n[2] CandidateInterestMember API...')
url2 = ('https://www.linkedin.com/voyager/api/graphql?'
        'includeWebMetadata=true'
        '&variables=(companyUrn:urn%3Ali%3Afsd_company%3A18994057)'
        '&queryId=voyagerTalentbrandDashCandidateInterestMember.d831bf8c5e3f1e8a9c0d4e7f6a5b3c1')

print(f'    URL: {url2[:150]}...')
resp2 = session.get(url2, timeout=30)
print(f'    Status: {resp2.status_code}, size: {len(resp2.text)}')

if resp2.status_code == 200:
    data2 = resp2.json()
    people2 = extract(data2)
    print(f'    Found {len(people2)} people')
    for p in people2:
        print(f'    - {p["name"]}: {p["title"][:80]}')

# Also try the information callout API
print(f'\n[3] InformationCallout API...')
url3 = ('https://www.linkedin.com/voyager/api/'
        'voyagerOrganizationDashInformationCallout?'
        'informationCalloutContext=TOP_CARD_MEMBER_VIEW'
        '&organizationalPage=urn%3Ali%3Afsd_organizationalPage%3A18994057'
        '&q=organizationDashInformationCallout')

resp3 = session.get(url3, timeout=30)
print(f'    Status: {resp3.status_code}, size: {len(resp3.text)}')
if resp3.status_code == 200:
    data3 = resp3.json()
    print(json.dumps(data3, ensure_ascii=False, indent=2)[:1000])
