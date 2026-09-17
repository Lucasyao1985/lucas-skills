---
name: xiaohongshu-note-downloader
description: Downloads Xiaohongshu (小红书 / Little Red Book) notes to local disk — full-resolution watermark-free images, the original MP4 video (up to 4K), and the note's text metadata (title, author, body, tags, interaction counts). Use when the user pastes a xiaohongshu.com/explore or xiaohongshu.com/discovery/item link (with or without xsec_token) and asks to download it, save the images, grab the video, archive the note, or batch-download several notes into folders. Trigger phrases include 下载小红书, 保存小红书图片, 小红书视频下载, 保存小红书笔记, download xiaohongshu images/video, save xiaohongshu note.
license: MIT
metadata:
  author: Lucas
  version: 2.0.0
  category: media
  tags: [xiaohongshu, rednote, downloader, images, video, scraper]
compatibility: Needs python3 plus curl on PATH. Video verification needs ffmpeg/ffprobe. Image verification needs Pillow. No browser or Playwright required.
---

# Xiaohongshu Note Downloader

Downloads a Xiaohongshu note's **images**, **video**, and **text metadata** to a local folder.

## Critical facts — read before touching anything

1. **Login is mandatory.** Xiaohongshu's web front end requires an authenticated session for
   every note page and even for the home page. Without a session you get a `302` to `/login`.
2. **`xsec_token` is mandatory too.** It lives in the URL the user pasted. A note fetched
   *without* it returns `302` to `/404/...?error_code=300031` ("当前笔记暂时无法浏览") —
   **even with a perfectly valid session.** Always keep the user's full URL.
3. **The full browser header set is mandatory.** This is the number one cause of mysterious
   failures. With a valid cookie but no `Sec-Fetch-*` / `sec-ch-ua` headers you get a `302` to
   `/login`; add them back and the same request returns `200`. Verified by A/B test — see
   `references/troubleshooting.md`.
4. **The session comes from the user's own browser profile.** Never try to log in yourself and
   never ask the user for a password. The script auto-discovers the session.
5. **Do not use the URLs shown on the page.** They are watermarked ~376 KB webp thumbnails
   (`!nd_dft_wlteh_webp_3`). The original image is a different host — see "Media URLs" below.

## Media URLs

| Asset | Source field | URL |
|---|---|---|
| Original image | `note.imageList[i].fileId` | `https://sns-img-qc.xhscdn.com/<fileId>` |
| Video cover | `note.imageList[0].fileId` | same as above |
| Video (all tiers) | `note.video.media.stream.<codec>[*]` | entry `masterUrl` or `backupUrls[0]` |

- `sns-img-qc.xhscdn.com/<fileId>` returns the **original PNG/JPEG** (measured 2.4 MB).
  `sns-img-bd.xhscdn.com` and `ci.xiaohongshu.com` are working mirrors.
  `sns-webpic-qc.xhscdn.com/<fileId>` (no timestamp prefix) returns **403** — that is why the
  older Playwright-based approach could only ever get watermarked thumbnails.
- Video `masterUrl` carries `?sign=...&t=<hex unix ts>` and is **time-limited**.
  `backupUrls[0]` is **unsigned and stable** — prefer it.
- Video audio (AAC) is **muxed into the same MP4**. Do not look for a separate audio stream.

## Workflow

1. **Take the full URL from the user**, including `xsec_token` and `xsec_source`. If the token
   is missing, say so up front — the fetch will fail with `error_code=300031`.
2. **Get a session.** Run the script with no `--cookie-source` and it scans local browser
   profiles for a non-expired `web_session`, preferring the most recently written one.
3. **Fetch and parse.** Success is `HTTP 200`, about 120 KB, containing
   `window.__INITIAL_STATE__`. The script parses it into `noteDetailMap`.
4. **Download media** per the table above.
5. **Write `笔记信息.md`** with title, author, note id, source URL, interaction counts, full
   body text, tags, and a media manifest.
6. **Verify.** Images via `PIL.Image.verify()`; video via `ffprobe` plus a full decode pass
   (`ffmpeg -v error -xerror -i f.mp4 -f null -`, expect zero output and exit 0).
7. **Open one downloaded file and look at it.** Confirm it matches the note body. Filenames and
   byte counts are not evidence.

## Getting a session

The script auto-discovers it. To do it by hand, scan these newest-`mtime`-first and require a
**non-expired `web_session`** — a profile with only `a1` / `gid` / `webId` is a guest session
and still redirects to `/login`:

| Source | Path | Encryption |
|---|---|---|
| Firefox | `%APPDATA%\Mozilla\Firefox\Profiles\*\cookies.sqlite`, table `moz_cookies` | plaintext |
| Chromium family (Chrome / Edge / Opera / Brave) | `<Profile>\Default\Network\Cookies`, table `cookies` | DPAPI + AES-GCM |
| Playwright profiles | `%LOCALAPPDATA%\ms-playwright-mcp\*\Default\Network\Cookies` | same |

Chromium decryption, in order:

1. `key = DPAPI_unprotect(base64decode(Local State["os_crypt"]["encrypted_key"])[5:])`
   — **strip the 5-byte `b"DPAPI"` prefix**, or DPAPI returns `(13, '数据无效。')`.
2. `plain = AESGCM(key).decrypt(enc[3:15], enc[15:], None)` — `enc` starts with `b"v10"`.
3. **Newer Chromium prepends 32 bytes of host binding.** If
   `plain[:32] == sha256(host_key).digest()`, the real value is `plain[32:]`. Skipping this
   gives "decrypted but not valid UTF-8" — the GCM tag passes, but the value carries a
   32-byte prefix. Length check: `len(enc) - 31 == 32 + len(value)`.
4. A `b"v20"` prefix means App-Bound Encryption — unsupported here, pick another profile.

Chromium timestamps: `unix = expires_utc / 1e6 - 11644473600`. Firefox `expiry` is milliseconds.

## Usage

```bash
# single note — best quality video
python scripts/xhs_download.py --url "<full explore url>" --out "F:/小红书/<topic name>"

# batch from a links file (one URL per line, # comments allowed)
python scripts/xhs_download.py --links links.txt --out-root "F:/小红书"

# images only
python scripts/xhs_download.py --url "<url>" --out "<dir>" --no-video

# universally playable h264 720p instead of the best quality
python scripts/xhs_download.py --url "<url>" --out "<dir>" --video-quality compat

# no session scan: pass cookies explicitly
python scripts/xhs_download.py --url "<url>" --out "<dir>" --cookie "a1=...; web_session=..."
```

### Video quality tiers

`h264` carries a **single 720p entry** — it is the compatibility tier. The full resolution
ladder lives under `h265` (hevc), which on a real note reached **2160x3840 (4K)**.

| `--video-quality` | Picks |
|---|---|
| `best` (default) | largest entry across all codecs — usually h265 4K |
| `compat` | largest h264 entry — 720p, plays anywhere |
| `h264` / `h265` | largest entry of that codec |

## Naming convention

- Folder: a short **topic name** chosen by the caller (e.g. `AI表情包_LINE风贴纸`), never the note id.
- Files: `{标题}_{序号}_{作者昵称}_来自小红书网页版.{ext}`; video uses `.mp4`.
- Companion file: `笔记信息.md`.

## Reference

- `references/xhs-data-model.md` — every field path in `__INITIAL_STATE__`, with real samples.
- `references/troubleshooting.md` — HTTP status / error-code decision table and the header matrix.
