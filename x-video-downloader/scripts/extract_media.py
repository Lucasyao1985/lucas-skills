#!/usr/bin/env python3
"""X/Twitter media extractor & downloader via fxtwitter API.

Usage:
  python extract_media.py <status_url> [more_urls...] [options]

Options:
  --type photo|video|gif|doc   keep only these types (repeatable/comma separated)
  --out DIR                    output directory (default: current dir)
  --download                   download after listing
  --name FILE                  force filename (single-file case only)
  --flat                       do not create per-post subfolder for multi-file posts

Default prints a manifest: one item per line  TYPE<TAB>URL<TAB>FILENAME
Lines starting with '#' carry post metadata (title, counts).

Coverage:
  - regular posts: media.photos, media.videos (highest bitrate), media.all fallback
  - X long-form articles: article.cover_media + article.media_entities (media is empty on these posts)
  - documents: external links in tweet text that resolve to direct files (pdf/docx/zip/...)
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://api.fxtwitter.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".zip", ".rar", ".7z", ".md", ".txt", ".csv", ".epub"}
DOC_MIMES = ("application/pdf", "application/zip", "application/msword",
             "application/vnd.openxmlformats", "application/epub+zip",
             "text/plain", "text/markdown", "text/csv")
VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_status(url):
    m = re.search(r"(?:x|twitter|fxtwitter|fixupx|vxtwitter)\.com/([A-Za-z0-9_]{1,20})/status(?:es)?/(\d+)", url)
    if not m:
        raise SystemExit("cannot parse status url: %s" % url)
    return m.group(1), m.group(2)


def fetch_json(user, tid):
    req = urllib.request.Request("%s/%s/status/%s" % (API, user, tid), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def ext_of(url, fallback):
    u = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(u.query).get("format", [None])[0]
    if q and re.fullmatch(r"[a-z0-9]{2,5}", q.lower()):
        return "." + q.lower()
    e = os.path.splitext(u.path)[1].lower()
    if e and len(e) <= 6:
        return e
    return fallback


def orig_size(url):
    """pbs.twimg.com media urls: request original size instead of name=large."""
    if "pbs.twimg.com/media" in url and "name=" in url:
        return re.sub(r"name=[a-z0-9]+", "name=orig", url)
    return url


def sanitize(name, limit=40):
    s = re.sub(r'[\\/:*?"<>|\r\n\t#]+', " ", str(name)).strip()
    return s[:limit].strip() or "untitled"


def collect(tweet, user, tid):
    items = []  # (type, url, filename)
    media = tweet.get("media") or {}
    photos = list(media.get("photos") or [])
    videos = list(media.get("videos") or [])
    if not photos and not videos:
        for m in media.get("all") or []:
            (photos if m.get("type") == "photo" else videos).append(m)

    for i, p in enumerate(photos, 1):
        u = p.get("url")
        if u:
            u = orig_size(u)
            items.append(("photo", u, "%s_%s_%02d%s" % (user, tid, i, ext_of(u, ".jpg"))))

    for i, v in enumerate(videos, 1):
        kind = "gif" if v.get("type") == "gif" else "video"
        u = v.get("url")
        if not u:
            fmts = v.get("formats") or []
            mp4s = [f for f in fmts if f.get("container") == "mp4" and f.get("url")]
            if mp4s:
                u = max(mp4s, key=lambda f: f.get("bitrate") or 0)["url"]
        if u:
            items.append((kind, u, "%s_%s_%02d%s" % (user, tid, i, ext_of(u, ".mp4"))))

    art = tweet.get("article") or {}
    cover = (art.get("cover_media") or {}).get("media_info", {}).get("original_img_url")
    if cover:
        items.append(("photo", cover, "%s_%s_cover%s" % (user, tid, ext_of(cover, ".jpg"))))
    aidx = 0
    for me in art.get("media_entities") or []:
        u = (me.get("media_info") or {}).get("original_img_url")
        if u:
            aidx += 1
            items.append(("photo", u, "%s_%s_img%02d%s" % (user, tid, aidx, ext_of(u, ".jpg"))))

    title = art.get("title") or ""
    docs = collect_docs(tweet)
    return items, docs, sanitize(title) if title else ""


def collect_docs(tweet):
    raw = (tweet.get("raw_text") or {}).get("text") or tweet.get("text") or ""
    links = set(re.findall(r"https?://[^\s\u4e00-\u9fff\uff09\u300d\u3011\u3010]+", raw))
    for f in ((tweet.get("raw_text") or {}).get("facets") or []):
        rep = f.get("replacement")
        if rep:
            links.add(rep)
    seen, docs = set(), []
    for link in links:
        host = urllib.parse.urlparse(link).netloc.lower()
        if not host or any(h in host for h in ("t.co", "twitter.com", "x.com")):
            continue
        final, ctype = resolve_redirect(link)
        ext = ext_of(final, "")
        if ext in DOC_EXTS or (ctype and any(m in ctype for m in DOC_MIMES)):
            if final not in seen:
                seen.add(final)
                docs.append(final)
    return docs


def resolve_redirect(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.geturl(), r.headers.get("Content-Type", "")
    except Exception:
        return url, ""


def download(url, path, tries=3):
    last_err = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
            if os.path.getsize(path) > 0:
                return True
        except Exception as e:
            last_err = e
    if last_err:
        sys.stderr.write("download failed %s: %s\n" % (url, last_err))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--type", dest="types", action="append", default=[])
    ap.add_argument("--out", default=".")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--flat", action="store_true")
    args = ap.parse_args()

    wanted = set()
    for t in args.types:
        wanted.update(x.strip() for x in t.split(",") if x.strip())

    def want(kind):
        return not wanted or kind in wanted

    ok, fail = 0, 0
    for url in args.urls:
        user, tid = parse_status(url)
        d = json.loads(json.dumps(fetch_json(user, tid)))
        tweet = d.get("tweet") or {}
        if not tweet:
            print("# ERROR: no tweet data for %s/%s (code=%s)" % (user, tid, d.get("code")))
            fail += 1
            continue
        items, docs, title = collect(tweet, user, tid)
        items = [it for it in items if want(it[0])]
        if docs and want("doc"):
            for i, u in enumerate(docs, 1):
                items.append(("doc", u, "%s_%s_doc%02d%s" % (user, tid, i, ext_of(u, ".bin"))))

        print("# %s/%s title=%s items=%d" % (user, tid, title, len(items)))
        if not items:
            print("# no matching media found")
            continue

        outdir = args.out
        sub = os.path.join(outdir, "%s_%s" % (user, tid)) if (len(items) > 1 and not args.flat) else outdir
        os.makedirs(sub, exist_ok=True)

        for i, (kind, u, fname) in enumerate(items):
            if args.name and len(items) == 1:
                fname = args.name
            print("%s\t%s\t%s" % (kind, u, fname))
            if args.download:
                path = os.path.join(sub, fname)
                if download(u, path):
                    ok += 1
                    print("# saved %s (%d bytes)" % (path, os.path.getsize(path)))
                else:
                    fail += 1
                    print("# FAILED %s" % fname)

    if args.download:
        print("# done ok=%d failed=%d" % (ok, fail))
        sys.exit(1 if fail and not ok else 0)


if __name__ == "__main__":
    main()
