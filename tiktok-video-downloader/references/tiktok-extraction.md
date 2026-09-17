# TikTok Extraction Reference

## Key Concept

TikTok keeps separate addresses for playback and download:

- `playAddr` → **no watermark** (used by in-app player and third-party embeds)
- `downloadAddr` → **watermarked** (used by official download button)
- `bitrateInfo[].PlayAddr.UrlList` → **no watermark**, multiple codecs/resolutions

## Page Data Locations

The video page may embed metadata in one of these script tags:

1. `__UNIVERSAL_DATA_FOR_REHYDRATION__` (current, recommended)
2. `SIGI_STATE` / `sigi-persisted-data` (older/fallback)

### Universal Data JSON path

```
__DEFAULT_SCOPE__
└── webapp.video-detail
    ├── statusCode          # 0 = OK
    ├── statusMsg
    └── itemInfo
        └── itemStruct
            ├── id
            ├── desc
            ├── author
            ├── stats
            └── video
                ├── playAddr        # no watermark
                ├── downloadAddr    # watermark
                ├── bitrateInfo[]   # multi-bitrate play addresses
                └── cover / originCover / dynamicCover
```

## Extraction Code

```python
import re
import json
import curl_cffi.requests as requests

session = requests.Session()
session.impersonate = "safari"  # safari/firefox usually pass Akamai
session.proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

page = session.get(tiktok_url, timeout=30)
match = re.search(
    r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    page.text, re.DOTALL,
)
if not match:
    raise RuntimeError("Universal data not found - possible bot page or structure change")

data = json.loads(match.group(1))
item = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
video = item["video"]
stream_url = video["playAddr"]
```

## Fingerprint Selection

Tested fingerprints against TikTok Akamai:

| Fingerprint | Result |
|-------------|--------|
| `safari` | ✅ Full page with video data |
| `firefox` | ✅ Full page with video data |
| `chrome110` | ⚠️ Page shell only (~43KB, no video data) |
| `chrome` / `chrome120` | ❌ Site Maintenance (~500B) |

If a small maintenance page is returned, switch `impersonate` and retry.

## Download Requirements

- **Must reuse the same session** so cookies (`tt_chain_token`, `ttwid`, `msToken`) are sent.
- **Must include `Referer`** equal to the TikTok video page.
- Without these, TikTok CDN returns `403 Forbidden`.

```python
headers = {"Referer": tiktok_url}
r = session.get(stream_url, headers=headers, timeout=60, stream=True)
```

## Common Issues

| Symptom | Cause / Fix |
|---------|-------------|
| `Site Maintenance` page | TLS fingerprint blocked → use `safari` / `firefox` |
| `playAddr` missing | Look for `bitrateInfo` or fallback to `SIGI_STATE` |
| `403` on download | Session cookies lost or URL expired → re-fetch page |
| `statusCode != 0` | Private/removed/geo-blocked; report code |
| Network timeout | Proxy unavailable; verify `127.0.0.1:7890` |
