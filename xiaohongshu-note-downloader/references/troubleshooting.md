# Troubleshooting

## Decision table — read the HTTP status first

| Symptom | Meaning | Fix |
|---|---|---|
| `302` to `/login?redirectPath=...` | No valid session, **or** the `Sec-Fetch-*` headers were dropped | Check the header matrix below, then check the cookie's `web_session` expiry |
| `302` to `/404/...?error_code=300031` | `xsec_token` missing, wrong, or expired | Use the user's **complete** URL, including `xsec_token` and `xsec_source` |
| `200` but `noteDetailMap` is empty | Note not accessible to this account | Deleted, private, or region-locked — report it, do not retry |
| `406` + `{"code":-1}` on `edith.xiaohongshu.com` | API signature missing (`X-Kong-Sign: 1`) | Expected — do not use the JSON API, scrape the HTML page instead |
| `403` on `sns-webpic-qc.xhscdn.com/<fileId>` | Wrong image host | Use `sns-img-qc.xhscdn.com/<fileId>` |
| `200` but the image is ~376 KB | You got the watermarked thumbnail | Use `fileId`, not `urlDefault` |

## The header matrix — this is the big one

Measured on the same URL with the same valid cookie, changing only the headers:

| Headers sent | Result |
|---|---|
| `Accept-Language` + `Referer` only | **`302` → `/login`** |
| `Accept`, `Accept-Language`, `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `Sec-Fetch-Dest/Mode/Site/User`, `Upgrade-Insecure-Requests`, `Referer` | **`200`, ~126 KB, has `__INITIAL_STATE__`** |

So a "valid cookie but still redirected to login" almost always means the request looked like a
bare script rather than a browser navigation. Always send the full set. The exact list is in
`BROWSER_HEADERS` in `scripts/xhs_download.py`.

## Session problems

**Symptom:** discovery reports "no web_session (guest session)".
The profile has `a1`, `gid`, `webId` — those are guest identifiers, not a login. A guest session
still redirects to `/login`.

**Symptom:** discovery reports "web_session expired".
`web_session` is the real login cookie. Its lifetime is roughly 30 days, and it can be revoked
server-side earlier. Nothing can be done locally — **the user must log in to xiaohongshu.com
again in any browser**, then re-run. Do not ask for their password; the script reads the cookie
the browser stores afterwards.

**Symptom:** Chromium decryption raises `(13, '数据无效。')` from `CryptUnprotectData`.
You forgot to strip the 5-byte `b"DPAPI"` prefix from the base64-decoded `encrypted_key`.

**Symptom:** decryption succeeds but the value is not valid UTF-8.
Newer Chromium prepends 32 bytes of host binding. Check
`plain[:32] == hashlib.sha256(host_key.encode()).digest()` and drop those 32 bytes.
Length sanity check: `len(encrypted_value) - 3 - 12 - 16 == 32 + len(value)`.

**Symptom:** the cookie value starts with `v20`.
App-Bound Encryption (Chrome 127+ with the feature enabled). Not supported by this script —
switch to another profile, or use Firefox, whose cookies are plaintext.

## Rate limiting and risk control

- Old `xsec_token` values from browser history mostly fail with `300031`; tokens are
  short-lived. Always prefer a URL the user just copied.
- Do not hammer the same note. One page fetch per note is enough — all media URLs come from
  that single response.
- Media downloads go to `xhscdn.com` CDNs and are not rate-limited the way the page endpoint is.

## Verifying a download

- **Images:** `PIL.Image.open(p).verify()`. Also flag anything under ~200 KB as a probable
  watermarked thumbnail.
- **Video:** `ffprobe` for the stream list, then a full decode pass —
  `ffmpeg -v error -xerror -i f.mp4 -f null -`. Zero output and exit code 0 means clean.
  A truncated download will fail here even though the file size looks plausible.
- **Always open one file and look at it.** Confirm the content matches the note body. Filenames
  and byte counts are not evidence.

## Windows / Git Bash gotchas

- `curl -o` needs Windows-style paths: `C:/dir/file`, `F:/dir/file`. `/tmp/...` fails with
  "No such file or directory".
- Git Bash rewrites backslashes in `python -c "..."` arguments, so `\s` silently becomes `/s`
  and regexes fail without raising. **Write scripts to a file instead of using `-c`.**

## When the old Playwright approach is the right call

The previous version of this skill drove a real browser and scraped `img.src`. That only ever
yields watermarked thumbnails, because the DOM never exposes the original `fileId`. Prefer this
script. Fall back to a browser only if you need to *see* the page — for example to confirm a
login wall is what is blocking you.
