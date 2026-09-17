import re, json
from pathlib import Path

html = Path(r'C:\Users\Lucas\.claude\skills\linkedin-jobs\kevin_post.html').read_text(encoding='utf-8')

print(f"HTML size: {len(html)}")

# Search for "Kevin"
kevin_positions = [m.start() for m in re.finditer(r'Kevin', html)]
print(f"Found 'Kevin' at positions: {kevin_positions}")

for pos in kevin_positions[:5]:
    start = max(0, pos - 200)
    end = min(len(html), pos + 500)
    snippet = html[start:end]
    print(f"\n--- Context around position {pos} ---")
    print(snippet[:700])

# Also search for the activity URN
urn_positions = [m.start() for m in re.finditer(r'7437026617127989250', html)]
print(f"\n\nFound activity URN at positions: {urn_positions}")

# Search for script tags with JSON
scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"\n\nFound {len(scripts)} JSON script tags")
for i, s in enumerate(scripts[:3]):
    print(f"\n[{i}] {len(s)} chars: {s[:300]}")

# Search for any text containing "departure" or "farewell" or "goodbye" or "last day"
for term in ['departure', 'farewell', 'goodbye', 'last day', '离开', '离职', 'new chapter', 'journey']:
    pos_list = [m.start() for m in re.finditer(term, html, re.IGNORECASE)]
    if pos_list:
        print(f"\n'{term}' found at positions: {pos_list}")

# Simple approach: find all visible text
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
# Remove script and style
for tag in soup(['script', 'style', 'code']):
    tag.decompose()
text = soup.get_text()
lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 10]
print(f"\n\n=== Visible text lines ({len(lines)} lines) ===")
for l in lines[:50]:
    print(l[:200])
