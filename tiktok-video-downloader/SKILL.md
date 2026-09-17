---
name: tiktok-video-downloader
description: Downloads watermark-free TikTok videos as MP4 files by parsing TikTok's embedded playAddr data and bypassing bot detection with curl_cffi browser fingerprint impersonation. Use when the user asks to "download TikTok", "download tiktok video", "save TikTok video", "TikTok 下载", "下载 TikTok", "下载tiktok视频", "无水印tiktok", or provides a tiktok.com/video/ URL and wants the video saved locally.
license: MIT
metadata:
  version: 2.0.0
  author: Lucas
  category: media-downloader
  tags: [tiktok, video, downloader, watermark-free]
  requires_python: "3.8+"
  requires_pip:
    - curl_cffi
  os:
    - win32
    - darwin
    - linux
---

# TikTok Video Downloader

Downloads TikTok videos as **watermark-free MP4** files by extracting the
`playAddr` from TikTok's page-embedded JSON data, then downloading it with the
same browser session (preserving `tt_chain_token` etc.).

## Core Principle

TikTok stores multiple versions of each video:

| Field | Purpose | Watermark |
|-------|---------|-----------|
| `playAddr` | In-app playback / third-party embed | ❌ No |
| `downloadAddr` | Official download button | ✅ Yes |
| `bitrateInfo[].PlayAddr.UrlList` | Multi-bitrate playback | ❌ No |

Always prefer `playAddr` / `bitrateInfo` over `downloadAddr`.

## Environment Requirements

- Python 3.8+
- `pip install curl_cffi`
- A working proxy is **required in restricted network regions** (e.g. mainland China).
  Default proxy used: `http://127.0.0.1:7890` (override with `--proxy` or env `HTTPS_PROXY`).

## Why curl_cffi

TikTok's CDN (Akamai) performs TLS fingerprint detection. Ordinary `requests`
or yt-dlp can be served a fake "Site Maintenance" page. `curl_cffi` simulates
real browser TLS fingerprints.

**Important fingerprint note:**
- `impersonate="safari"` and `"firefox"` are known to work.
- `impersonate="chrome"` / `"chrome120"` may be blocked by Akamai.
- Test with different fingerprints if one is blocked.

## Workflow

### Step 1: Fetch the TikTok page

Use a `curl_cffi.requests.Session` (not a fresh request) so cookies are kept
for the later video download:

```python
import curl_cffi.requests as requests

session = requests.Session()
session.impersonate = "safari"
session.proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

page = session.get(video_url, timeout=30)
```

The response must contain `__UNIVERSAL_DATA_FOR_REHYDRATION__`. If it is a
small "Site Maintenance" page (~500 bytes), switch the impersonation target.

### Step 2: Parse the embedded JSON

TikTok embeds the video metadata in a `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`
tag:

```python
import re, json

m = re.search(
    r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    page.text, re.DOTALL,
)
data = json.loads(m.group(1))
item = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
video = item["video"]
```

### Step 3: Select the watermark-free URL

```python
# Preferred: direct playAddr (usually H.264 720p, no watermark)
stream_url = video["playAddr"]
```

If `playAddr` is missing or fails, choose a compatible H.264 stream from
`bitrateInfo`:

```python
# Prefer H.264 over bytevc1 (H.265/VVC) for broad compatibility
for br in video.get("bitrateInfo", []):
    key = br.get("PlayAddr", {}).get("UrlKey", "")
    if "_h264_" in key:
        stream_url = br["PlayAddr"]["UrlList"][0]
        break
```

### Step 4: Download using the same session

The CDN requires cookies (especially `tt_chain_token`) and a `Referer` header.
Using a new request without cookies yields HTTP 403.

```python
headers = {"Referer": video_url}
r = session.get(stream_url, headers=headers, timeout=60, stream=True)
r.raise_for_status()
```

### Step 5: Save and verify

```python
with open(output_path, "wb") as f:
    for chunk in r.iter_content(chunk_size=1024 * 256):
        f.write(chunk)
```

Verify:
- File size > 10 KB
- Content starts with MP4 header (`ftyp`)
- Optionally run `ffprobe` to confirm resolution/duration

## Output Format

Report to the user:

```
✅ TikTok 下载完成
- 文件：{output_path}
- 大小：{size_mb:.1f} MB
- 分辨率：{width}×{height}
- 时长：{duration:.1f} 秒
- 格式：MP4（无水印）
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Site Maintenance page (~500B) | TLS fingerprint blocked | Change `impersonate` to `safari` / `firefox` |
| `__UNIVERSAL_DATA_FOR_REHYDRATION__` not found | Page structure changed or bot page returned | Save HTML for debugging; fall back to `SIGI_STATE` |
| 403 on video download | Missing cookies or expired URL | Use same session; re-fetch page to refresh URL; add `Referer` |
| Connection timeout | Network/proxy issue | Check proxy `127.0.0.1:7890`; increase timeout; retry |
| Video not available / statusCode != 0 | Private, removed, or geo-blocked | Report status code to user |

## Examples

### Example 1: Download a TikTok video

User: "下载这个 TikTok https://www.tiktok.com/@gllit.y811/video/7671647438117293332"

1. Fetch page with `impersonate="safari"` via proxy.
2. Parse `__UNIVERSAL_DATA_FOR_REHYDRATION__`.
3. Extract `video.playAddr`.
4. Download with same session + `Referer`.
5. Save as `D:/裁切图片为9比16/tiktok_7671647438117293332_nwm.mp4`.
6. Verify with `ffprobe`.

### Example 2: Watermark-free download request

User: "帮我下载无水印的tiktok视频"

1. Ask for the TikTok URL if not provided.
2. Follow the workflow above.
3. Always report whether the saved file is the no-watermark `playAddr` version.

## References

- `references/tiktok-extraction.md` — TikTok page structure, JSON paths, and extraction patterns
- `scripts/download_tiktok.py` — Ready-to-use CLI downloader
