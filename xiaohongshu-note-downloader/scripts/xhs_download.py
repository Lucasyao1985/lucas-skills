#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Xiaohongshu note downloader: images (watermark-free originals) + video (up to 4K) + note metadata.

The web front end requires a logged-in session AND the URL's xsec_token AND a full browser
header set. This script handles all three, auto-discovering the session from local browser
profiles so no manual cookie handling is needed.

Examples
--------
    python xhs_download.py --url "<explore url>" --out "F:/小红书/AI表情包_LINE风贴纸"
    python xhs_download.py --links links.txt --out-root "F:/小红书"
    python xhs_download.py --url "<url>" --out "<dir>" --no-video --dump-json

Dependencies: python3, curl. Pillow (image check) and ffmpeg/ffprobe (video check) optional.
"""
import argparse
import base64
import ctypes
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Full header set. Dropping the Sec-Fetch-* / sec-ch-ua entries makes Xiaohongshu return
# 302 -> /login even with a perfectly valid session cookie. Verified by A/B test.
BROWSER_HEADERS = [
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
    'sec-ch-ua: "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile: ?0",
    'sec-ch-ua-platform: "Windows"',
    "Sec-Fetch-Dest: document",
    "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: none",
    "Sec-Fetch-User: ?1",
    "Upgrade-Insecure-Requests: 1",
    "Referer: https://www.xiaohongshu.com/",
]

IMG_HOSTS = ["https://sns-img-qc.xhscdn.com/", "https://sns-img-bd.xhscdn.com/"]
VIDEO_HOSTS = ["https://sns-video-qc.xhscdn.com/", "https://sns-bak-v6.xhscdn.com/"]
EXT_BY_CTYPE = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}

HOME = os.path.expanduser("~")
LOCAL = os.path.join(HOME, "AppData", "Local")
ROAM = os.path.join(HOME, "AppData", "Roaming")

# (label, path, kind) — kind: chromium | chromium-profiles | chromium-glob | firefox
COOKIE_SOURCES = [
    ("pw-mcp", os.path.join(LOCAL, r"ms-playwright-mcp"), "chromium-glob"),
    ("pw", os.path.join(LOCAL, r"ms-playwright"), "chromium-glob"),
    ("opera", os.path.join(ROAM, r"Opera Software\Opera Stable"), "chromium"),
    ("chrome", os.path.join(LOCAL, r"Google\Chrome\User Data"), "chromium-profiles"),
    ("edge", os.path.join(LOCAL, r"Microsoft\Edge\User Data"), "chromium-profiles"),
    ("brave", os.path.join(LOCAL, r"BraveSoftware\Brave-Browser\User Data"), "chromium-profiles"),
    ("vivaldi", os.path.join(LOCAL, r"Vivaldi\User Data"), "chromium-profiles"),
    ("firefox", os.path.join(ROAM, r"Mozilla\Firefox\Profiles"), "firefox"),
]


# --------------------------------------------------------------------------- DPAPI
class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_unprotect(data):
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def aes_gcm_decrypt(key, nonce, ct):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key).decrypt(nonce, ct, None)


def chromium_master_key(local_state_path):
    if not os.path.exists(local_state_path):
        return None
    try:
        ek = base64.b64decode(json.load(open(local_state_path, encoding="utf-8"))
                              ["os_crypt"]["encrypted_key"])
    except Exception:
        return None
    if ek[:5] != b"DPAPI":
        return None
    try:
        return dpapi_unprotect(ek[5:])          # strip the b"DPAPI" literal
    except Exception:
        return None


def decrypt_cookie(key, host, enc):
    if enc[:3] == b"v20":
        raise RuntimeError("v20 = App-Bound Encryption, unsupported")
    plain = aes_gcm_decrypt(key, enc[3:15], enc[15:])
    # newer Chromium prepends sha256(host_key) as a 32-byte binding
    if len(plain) > 32 and plain[:32] == hashlib.sha256(host.encode()).digest():
        plain = plain[32:]
    return plain.decode("utf-8", "replace")


def _tmp(suffix):
    return os.path.join(tempfile.gettempdir(), "xhs_%d%s" % (int(time.time() * 1e6 % 1e9), suffix))


def read_chromium(cookies_db, local_state):
    if not os.path.exists(cookies_db):
        return None
    key = chromium_master_key(local_state)
    if key is None:
        return None
    tmp = _tmp(".db")
    shutil.copy2(cookies_db, tmp)
    out, exp = {}, {}
    try:
        con = sqlite3.connect(tmp)
        for host, name, val, enc, e in con.execute(
                "select host_key,name,value,encrypted_value,expires_utc "
                "from cookies where host_key like '%xiaohongshu%'"):
            try:
                out[name] = decrypt_cookie(key, host, enc) if enc else val
            except Exception:
                continue
            exp[name] = e
        con.close()
    except Exception:
        return None
    finally:
        _rm(tmp)
    return (out, exp) if out else None


def read_firefox(root):
    if not os.path.isdir(root):
        return None
    best = None
    for d in os.listdir(root):
        db = os.path.join(root, d, "cookies.sqlite")
        if os.path.exists(db) and (best is None or os.path.getmtime(db) > best[0]):
            best = (os.path.getmtime(db), db)
    if not best:
        return None
    tmp = _tmp(".db")
    shutil.copy2(best[1], tmp)
    out, exp = {}, {}
    try:
        con = sqlite3.connect(tmp)
        for name, val, e in con.execute(
                "select name,value,expiry from moz_cookies where host like '%xiaohongshu%'"):
            out[name] = val
            exp[name] = e                      # Firefox expiry is in milliseconds
        con.close()
    except Exception:
        return None
    finally:
        _rm(tmp)
    return (out, exp) if out else None


def _rm(p):
    try:
        os.remove(p)
    except OSError:
        pass


def expand(label, path, kind):
    """Yield (label, cookies_db_path, local_state_path)."""
    if kind == "chromium":
        return [(label, os.path.join(path, "Default", "Network", "Cookies"),
                 os.path.join(path, "Local State"))]
    if kind == "chromium-profiles":
        res = []
        if os.path.isdir(path):
            for d in os.listdir(path):
                if d == "Default" or d.startswith("Profile "):
                    res.append((label + "/" + d,
                                os.path.join(path, d, "Network", "Cookies"),
                                os.path.join(path, "Local State")))
        return res
    if kind == "chromium-glob":
        # layouts vary: <root>/<user>/Default/Network/Cookies with <root>/<user>/Local State
        res = []
        if os.path.isdir(path):
            for dp, dn, fn in os.walk(path):
                if os.path.basename(dp) == "Network" and "Cookies" in fn:
                    user_dir = os.path.dirname(os.path.dirname(dp))   # strip Default/Network
                    ls = os.path.join(user_dir, "Local State")
                    res.append((label + ":" + os.path.basename(user_dir),
                                os.path.join(dp, "Cookies"), ls))
        return res
    if kind == "firefox":
        return [(label, path, None)]
    return []


def find_session(only=None, verbose=True):
    """Return (label, cookie_dict) for a profile holding a non-expired web_session."""
    now_ms = time.time() * 1000
    notes = []
    for label, path, kind in COOKIE_SOURCES:
        if only and only not in label:
            continue
        for lab, db, ls in expand(label, path, kind):
            got = read_firefox(db) if ls is None else read_chromium(db, ls)
            if not got:
                continue
            ck, exp = got
            if "web_session" not in ck:
                notes.append((lab, "no web_session (guest session)"))
                continue
            try:
                fresh = int(exp.get("web_session") or 0) > now_ms
            except (TypeError, ValueError):
                fresh = False
            if not fresh:
                notes.append((lab, "web_session expired"))
                continue
            if verbose:
                print("      session: %s (%d cookies)" % (lab, len(ck)))
            return lab, ck
    if verbose:
        print("[!] no usable session found. Checked:")
        for a, b in notes:
            print("      %-34s %s" % (a, b))
    return None, None


# --------------------------------------------------------------------------- HTTP
def curl(url, out=None, cookie=None, timeout=60):
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA]
    for h in BROWSER_HEADERS:
        cmd += ["-H", h]
    if cookie:
        cmd += ["-H", "Cookie: " + cookie]
    if out:
        cmd += ["-o", out, "-w", "%{http_code} %{content_type}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def fetch_note(url, cookie):
    out = _tmp(".html")
    res = curl(url, out=out, cookie=cookie)
    code = res.split()[0] if res else "?"
    if not os.path.exists(out):
        raise SystemExit("fetch failed: curl produced no output (%s)" % res)
    html = open(out, encoding="utf-8", errors="replace").read()
    size = len(html)
    if code != "200" or "__INITIAL_STATE__" not in html:
        hint = ""
        if "error_code=300031" in html or "300031" in res:
            hint = "\n  error_code=300031 -> xsec_token missing or expired. Use the user's full URL."
        elif code == "302" or "login" in html[:400]:
            hint = "\n  302 -> /login. Either no valid session, or the Sec-Fetch-* headers were dropped."
        _rm(out)
        raise SystemExit("fetch failed: HTTP %s, %d bytes.%s" % (code, size, hint))
    _rm(out)
    return html


def parse_note(html):
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if not m:
        raise SystemExit("no window.__INITIAL_STATE__ in page")
    raw = re.sub(r"\bundefined\b", "null", m.group(1))   # XHS emits bare `undefined`
    st = json.loads(raw)
    detail = st.get("note", {}).get("noteDetailMap", {})
    if not detail:
        raise SystemExit("noteDetailMap is empty - note not accessible")
    nid = list(detail.keys())[0]
    return nid, detail[nid]["note"], st


# --------------------------------------------------------------------------- naming
def safe_name(s, limit=80):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", (s or "").strip())
    s = re.sub(r"\s+", " ", s)
    return s[:limit].rstrip(" .")


def title_of(note):
    return safe_name(note.get("title") or note.get("desc", "")[:24] or "无标题", 40)


def author_of(note):
    return safe_name((note.get("user") or {}).get("nickname") or "未知作者", 30)


# --------------------------------------------------------------------------- video
def stream_entries(note):
    """Flatten note.video.media.stream into [(codec, entry), ...]"""
    video = note.get("video") or {}
    stream = ((video.get("media") or {}).get("stream") or {})
    out = []
    for codec in ("h264", "h265", "h266", "av1"):
        for e in (stream.get(codec) or []):
            if e.get("masterUrl") or e.get("backupUrls"):
                out.append((codec, e))
    return out


def pick_video(note, quality="best"):
    entries = stream_entries(note)
    if not entries:
        return None
    def size(e):
        return e.get("size") or 0
    if quality == "compat":
        pool = [e for c, e in entries if c == "h264"] or entries
    elif quality in ("h264", "h265"):
        pool = [e for c, e in entries if c == quality] or entries
    else:
        pool = [e for c, e in entries]
    return max(pool, key=size)


def video_urls(entry):
    """backupUrls first: unsigned and stable. masterUrl carries a time-limited sign."""
    urls = list(entry.get("backupUrls") or []) + ([entry["masterUrl"]] if entry.get("masterUrl") else [])
    return urls


# --------------------------------------------------------------------------- download
def download_first_ok(urls, dest_noext, timeout=180):
    """Try each URL until one returns 200 with a plausible body. Returns (path, ctype)."""
    for i, url in enumerate(urls):
        tmp = dest_noext + ".part"
        res = curl(url, out=tmp, timeout=timeout)
        parts = res.split()
        code = parts[0] if parts else "?"
        ctype = parts[1] if len(parts) > 1 else ""
        if code == "200" and os.path.exists(tmp) and os.path.getsize(tmp) > 1024:
            return tmp, ctype
        _rm(tmp)
    return None, None


def download_images(note, folder, with_cover=True):
    title, author = title_of(note), author_of(note)
    imgs = note.get("imageList") or []
    ok = 0
    for i, im in enumerate(imgs, 1):
        fid = im.get("fileId")
        if not fid:
            continue
        # for video notes imageList[0] is the cover frame
        tag = "封面" if (note.get("type") == "video" and i == 1) else str(i)
        if note.get("type") == "video" and i == 1 and not with_cover:
            continue
        base = "%s_%s_%s_来自小红书网页版" % (title, tag, author)
        tmp, ctype = download_first_ok([h + fid for h in IMG_HOSTS],
                                       os.path.join(folder, base))
        if not tmp:
            print("  img %-6s FAIL" % tag)
            continue
        dst = tmp[:-5] + EXT_BY_CTYPE.get(ctype, ".png")
        os.replace(tmp, dst)
        ok += 1
        print("  img %-6s OK  %8.1f KB  %s" % (tag, os.path.getsize(dst) / 1024, os.path.basename(dst)[-40:]))
    return ok, len(imgs)


def download_video(note, folder, quality):
    entry = pick_video(note, quality)
    if entry is None:
        return None
    title, author = title_of(note), author_of(note)
    base = "%s_%s_来自小红书网页版" % (title, author)
    tmp, ctype = download_first_ok(video_urls(entry), os.path.join(folder, base), timeout=600)
    if not tmp:
        print("  video FAIL (all urls)")
        return None
    dst = os.path.join(folder, base + ".mp4")
    os.replace(tmp, dst)
    mb = os.path.getsize(dst) / 1048576
    print("  video OK  %8.1f MB  %sx%s  %s  %s" % (
        mb, entry.get("width"), entry.get("height"), entry.get("videoCodec"), entry.get("streamDesc")))
    return dst


# --------------------------------------------------------------------------- verify
def verify_images(folder):
    try:
        from PIL import Image
    except ImportError:
        print("  (Pillow not installed - skipped image verification)")
        return
    bad = 0
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        p = os.path.join(folder, f)
        try:
            Image.open(p).verify()
            kb = os.path.getsize(p) / 1024
            if kb < 200:
                print("  [warn] %s only %.0f KB - probably a watermarked thumbnail" % (f[-34:], kb))
        except Exception as e:
            print("  [BAD] %s: %s" % (f, e))
            bad += 1
    print("  images verified, %d corrupt" % bad)


def verify_video(path):
    if not path:
        print("  (no video in this note)")
        return
    if not shutil.which("ffprobe"):
        print("  (ffprobe not found - skipped video verification)")
        return
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_name,codec_type,width,height,duration",
                        "-of", "default=noprint_wrappers=1", path],
                       capture_output=True, text=True)
    info = [l for l in r.stdout.splitlines() if l.strip()]
    print("  ffprobe: " + "; ".join(info))
    if shutil.which("ffmpeg"):
        d = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", path, "-f", "null", "-"],
                           capture_output=True, text=True)
        print("  full decode: %s" % ("clean" if d.returncode == 0 and not d.stderr.strip()
                                     else "ERRORS -> " + d.stderr.strip()[:200]))


# --------------------------------------------------------------------------- meta
def fmt_time(ms):
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ms) / 1000))
    except (TypeError, ValueError):
        return "-"


def write_meta(folder, nid, note, url):
    title = (note.get("title") or "").strip()
    author = (note.get("user") or {}).get("nickname", "")
    ii = note.get("interactInfo") or {}
    tags = " ".join("#%s" % t.get("name") for t in (note.get("tagList") or []))
    lines = [
        "# %s" % (title or "(无标题)"), "",
        "- **笔记 ID**: %s" % nid,
        "- **作者**: %s（%s）" % (author, (note.get("user") or {}).get("userId", "")),
        "- **类型**: %s" % ("视频" if note.get("type") == "video" else "图文"),
        "- **链接**: %s" % url,
        "- **互动**: 点赞 %s / 收藏 %s / 评论 %s" % (
            ii.get("likedCount"), ii.get("collectedCount"), ii.get("commentCount")),
        "- **发布时间**: %s" % fmt_time(note.get("time")),
        "- **抓取时间**: %s" % time.strftime("%Y-%m-%d %H:%M"),
        "- **标签**: %s" % tags, "",
        "## 正文", "", (note.get("desc") or "").strip(), "",
        "## 媒体清单", "",
    ]
    if note.get("type") == "video":
        e = pick_video(note, "best")
        if e:
            lines += ["| 类型 | 规格 | 说明 |", "|---|---|---|",
                      "| 视频 | %sx%s, %s, %.1f MB | %s |" % (
                          e.get("width"), e.get("height"), e.get("videoCodec"),
                          (e.get("size") or 0) / 1048576, e.get("streamDesc")),
                      "| 封面 | - | imageList[0] |", ""]
    else:
        lines += ["| # | 尺寸 | 文件 |", "|---|---|---|"]
        for i, im in enumerate(note.get("imageList") or [], 1):
            lines.append("| %d | %sx%s | %s_%d_%s_来自小红书网页版 |" % (
                i, im.get("width"), im.get("height"), title_of(note), i, author_of(note)))
        lines.append("")
    open(os.path.join(folder, "笔记信息.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("  wrote 笔记信息.md")


# --------------------------------------------------------------------------- driver
def process(url, out, cookie, args):
    print("[1/4] fetching note ...")
    html = fetch_note(url, cookie)
    nid, note, state = parse_note(html)
    print("      %s | %s | %s | %d image(s)" % (
        nid, note.get("type"), (note.get("title") or "")[:34], len(note.get("imageList") or [])))
    os.makedirs(out, exist_ok=True)

    if args.dump_json:
        json.dump(note, open(os.path.join(out, "note_raw.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("      wrote note_raw.json")

    print("[2/4] downloading media ...")
    download_images(note, out)
    video_path = None
    if note.get("type") == "video" and not args.no_video:
        video_path = download_video(note, out, args.video_quality)
    elif note.get("type") == "video":
        print("  (video skipped by --no-video)")

    print("[3/4] verifying ...")
    verify_images(out)
    verify_video(video_path)

    print("[4/4] writing metadata ...")
    if not args.no_meta:
        write_meta(out, nid, note, url)

    total = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print("\ndone: %s  (%.1f MB, %d files)" % (out, total / 1048576, len(os.listdir(out))))
    return True


def main():
    ap = argparse.ArgumentParser(description="Download Xiaohongshu notes (images + video + info).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="single note URL (must contain xsec_token)")
    src.add_argument("--links", help="file with one note URL per line")
    ap.add_argument("--out", help="output folder (single-note mode)")
    ap.add_argument("--out-root", help="parent folder; one subfolder per note (batch mode)")
    ap.add_argument("--cookie", help="explicit cookie string (skips profile discovery)")
    ap.add_argument("--cookie-source", help="restrict discovery to sources matching this keyword")
    ap.add_argument("--video-quality", default="best", choices=["best", "compat", "h264", "h265"])
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--no-meta", action="store_true")
    ap.add_argument("--dump-json", action="store_true", help="also save the raw note JSON")
    args = ap.parse_args()

    if args.cookie:
        cookie, label = args.cookie, "explicit"
    else:
        print("[0/4] discovering browser session ...")
        label, ck = find_session(args.cookie_source)
        if not ck:
            raise SystemExit("No usable session. Log in to xiaohongshu.com in any browser, then retry.")
        cookie = "; ".join("%s=%s" % (k, v) for k, v in ck.items())

    if args.url:
        if "xsec_token" not in args.url:
            print("[!] warning: URL has no xsec_token - expect error_code=300031")
        if not args.out:
            raise SystemExit("--out is required with --url")
        process(args.url.strip(), args.out, cookie, args)
        return

    # batch
    urls = []
    for line in open(args.links, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    root = args.out_root or "."
    print("batch: %d links -> %s" % (len(urls), root))
    fails = []
    for i, u in enumerate(urls, 1):
        print("\n=== [%d/%d] %s" % (i, len(urls), u[:70]))
        try:
            html = fetch_note(u, cookie)
            nid, note, _ = parse_note(html)
            out = os.path.join(root, args.out or title_of(note))
            process(u, out, cookie, args)
        except SystemExit as e:
            print("  SKIP: %s" % e)
            fails.append((u, str(e)))
    if fails:
        print("\n%d failed:" % len(fails))
        for u, e in fails:
            print("  %s\n    %s" % (u[:70], e.splitlines()[0]))


if __name__ == "__main__":
    main()
