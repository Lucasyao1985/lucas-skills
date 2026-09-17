#!/usr/bin/env python3
"""Extract verbatim prompt templates from OpenArt (openart.ai) pages.

OpenArt is a Next.js App Router site. Prompts are not in the DOM - they live in
the RSC "flight" payload streamed via self.__next_f.push([1,"..."]) calls, and
the template object only holds a *reference* (e.g. "$2c") to a length-prefixed
text row (e.g. "2c:T1dc4,<prompt>") elsewhere in the stream.

Usage:
    python extract_openart_prompt.py <url> [--out DIR] [--json] [--debug] [--media]
    python extract_openart_prompt.py <url> --list [--limit N] [--out DIR] [--media]
    python extract_openart_prompt.py --html page.html [--out DIR]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import urljoin

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FETCH_PS1 = os.path.join(SCRIPT_DIR, "fetch_page.ps1")
DOWNLOAD_PS1 = os.path.join(SCRIPT_DIR, "download_file.ps1")

TEMPLATE_KEYS = ('"template":', '"templateData":', '"viralTemplate":')
PROMPT_KEYS = ("promptTemplate", "promptText", "prompt", "positivePrompt")


def log(msg):
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------
# Step 1: fetch
# --------------------------------------------------------------------------
def fetch(url, timeout=90):
    """Try urllib, fall back to PowerShell Invoke-WebRequest."""
    import urllib.request
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            log(f"[fetch] urllib ok, {len(body)} chars")
            return body
    except Exception as e:
        log(f"[fetch] urllib failed: {e} -> trying PowerShell")

    if not os.path.exists(FETCH_PS1):
        raise RuntimeError(f"fetch helper missing: {FETCH_PS1}")

    tmpdir = tempfile.mkdtemp(prefix="openart_")
    out_html = os.path.join(tmpdir, "page.html")
    out_log = os.path.join(tmpdir, "fetch.log")
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", FETCH_PS1, "-Url", url, "-OutFile", out_html, "-LogFile", out_log,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    if p.returncode != 0 or not os.path.exists(out_html):
        raise RuntimeError(
            f"fetch failed (rc={p.returncode}): {p.stdout.strip()} {p.stderr.strip()}")

    with open(out_log, encoding="utf-8", errors="replace") as f:
        log(f"[fetch] powershell: {f.read().strip()}")
    with open(out_html, encoding="utf-8", errors="replace") as f:
        body = f.read()
    log(f"[fetch] powershell ok, {len(body)} chars")
    return body


FORCE = False  # flipped by --force; when False, existing files are left alone


def download_file(url, dest, timeout=300):
    """Binary-safe download. Returns dest on success, None on failure."""
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    if not FORCE and os.path.exists(dest) and os.path.getsize(dest) > 0:
        log(f"[media] skip existing {os.path.getsize(dest)} bytes -> {dest}")
        return dest
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://openart.ai/"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            f.write(r.read())
        log(f"[media] urllib ok {os.path.getsize(dest)} bytes -> {dest}")
        return dest
    except Exception as e:
        log(f"[media] urllib failed: {e} -> trying PowerShell")

    if not os.path.exists(DOWNLOAD_PS1):
        return None
    log_path = dest + ".log"
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
           "-File", DOWNLOAD_PS1, "-Url", url, "-OutFile", dest, "-LogFile", log_path]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    if p.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
        log(f"[media] powershell ok {os.path.getsize(dest)} bytes -> {dest}")
        if os.path.exists(log_path):
            os.remove(log_path)
        return dest
    log(f"[media] FAILED {url}")
    return None


EXT_BY_KIND = {"image": ".jpg", "video": ".mp4", "audio": ".mp3"}


def guess_ext(url, kind=None):
    """Best-effort extension: probe Content-Type, then fall back to kind."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        mapping = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                   "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm",
                   "audio/mpeg": ".mp3", "audio/wav": ".wav"}
        if ctype in mapping:
            return mapping[ctype]
    except Exception:
        pass
    return EXT_BY_KIND.get(kind or "", ".bin")


MAGIC = [
    (b"RIFF", ".webp"), (b"\xff\xd8\xff", ".jpg"), (b"\x89PNG", ".png"),
    (b"GIF8", ".gif"), (b"ID3", ".mp3"), (b"\x1aE\xdf\xa3", ".webm"),
]


def sniff_ext(path):
    """Detect the real extension from file magic bytes. Returns '' if unknown."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except Exception:
        return ""
    for sig, ext in MAGIC:
        if head.startswith(sig):
            if ext == ".webp" and head[8:12] != b"WEBP":
                continue
            return ext
    if head[4:8] == b"ftyp":
        return ".mp4"
    return ""


def save_asset(url, dest, kind=None):
    """Download to dest, then correct the extension using magic bytes."""
    p = download_file(url, dest)
    if not p:
        return None
    real = sniff_ext(p)
    if real and not p.lower().endswith(real):
        newp = os.path.splitext(p)[0] + real
        if not os.path.exists(newp):
            os.replace(p, newp)
        p = newp
    return p


def download_media(tmpl, folder):
    """Save preview video, thumbnail and source reference assets."""
    if not tmpl:
        return []
    saved = []
    pv = tmpl.get("previewVideo") or {}
    if pv.get("url"):
        ext = os.path.splitext(pv["url"].split("?")[0])[1] or ".mp4"
        p = save_asset(pv["url"], os.path.join(folder, f"preview{ext}"))
        if p:
            saved.append(p)
    th = tmpl.get("thumbnail") or {}
    if th.get("url"):
        ext = os.path.splitext(th["url"].split("?")[0])[1] or ".webp"
        p = save_asset(th["url"], os.path.join(folder, f"thumbnail{ext}"))
        if p:
            saved.append(p)
    # Source reference assets (image1 / video1 / ...) used as template inputs
    for i, ref in enumerate(tmpl.get("sourceReferences") or [], 1):
        url = ref.get("url")
        if not url:
            continue
        label = ref.get("label") or f"input{i}"
        ext = os.path.splitext(url.split("?")[0])[1] or guess_ext(url, ref.get("kind"))
        p = save_asset(url, os.path.join(folder, "inputs", f"{label}{ext}"))
        if p:
            saved.append(p)
    return saved


# --------------------------------------------------------------------------
# Step 2: flight payload
# --------------------------------------------------------------------------
def extract_flight(page):
    """Reassemble the RSC flight stream from all self.__next_f.push chunks."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', page)
    parts = []
    for c in chunks:
        try:
            parts.append(json.loads(c))
        except Exception:
            continue
    flight = "".join(parts)
    if not flight:
        # Older builds: payload may be inside a script tag without the [1, ..] wrapper
        alt = re.findall(r'self\.__next_f\.push\(\[1,(\"(?:[^\"\\\\]|\\\\.)*\")\]\)', page)
        for c in alt:
            try:
                parts.append(json.loads(c))
            except Exception:
                pass
        flight = "".join(parts)
    return flight


# --------------------------------------------------------------------------
# Step 3: resolve prompt
# --------------------------------------------------------------------------
TMPL_MARKERS = ("promptTemplate", "handoff", "sourceLabel", "sourceReferences",
                "primitives", "detailHref", "title")


def find_template_obj(flight):
    """Return (template_dict, end_index) or (None, -1).

    The same key can appear many times in a flight stream (layout placeholders
    like {"template":["$","$L1e",null,{}]} come first), so every occurrence is
    tried until one decodes to a dict that actually looks like a template.
    """
    dec = json.JSONDecoder()
    for key in TEMPLATE_KEYS:
        for m in re.finditer(re.escape(key), flight):
            try:
                obj, end = dec.raw_decode(flight, m.end())
            except Exception:
                continue
            if isinstance(obj, dict) and any(k in obj for k in TMPL_MARKERS):
                if "promptTemplate" in obj or "handoff" in obj or "sourceReferences" in obj:
                    return obj, end
    return None, -1


def fallback_title(flight):
    """Best-effort title when no template object is available."""
    m = re.search(r'"property":"og:title","content":"((?:[^"\\]|\\.)*)"', flight)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')
        except Exception:
            return m.group(1)
    m = re.search(r'<title>([^<]+)</title>', flight)
    return m.group(1).strip() if m else None


def resolve_ref(flight_bytes, ref):
    """Resolve a flight text reference like '2c' -> ('text', declared_len, ok)."""
    ref_b = ref.encode()
    for m in re.finditer(rb"(?:^|\n)" + re.escape(ref_b) + rb":T([0-9a-fA-F]+),", flight_bytes):
        declared = int(m.group(1), 16)
        start = m.end()
        raw = flight_bytes[start:start + declared]
        try:
            text = raw.decode("utf-8")
            ok = len(text.encode("utf-8")) == declared
        except Exception:
            text, ok = raw.decode("utf-8", "replace"), False
        return text, declared, ok
    return None, 0, False


def json_string_at(flight, key):
    """Extract a plain JSON string value for `key` (no reference)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r'"' + re.escape(key) + r'":\s*"', flight):
        try:
            val, _ = dec.raw_decode(flight, m.end() - 1)
        except Exception:
            continue
        if isinstance(val, str) and len(val) > 80:
            return val
    return None


def longest_text_row(flight_bytes, min_len=500):
    best = ""
    for m in re.finditer(rb"(?:^|\n)[0-9a-zA-Z]+:T([0-9a-fA-F]+),", flight_bytes):
        declared = int(m.group(1), 16)
        raw = flight_bytes[m.end():m.end() + declared]
        try:
            text = raw.decode("utf-8")
        except Exception:
            continue
        if len(text.encode("utf-8")) == declared and len(text) > len(best):
            best = text
    return best if len(best) >= min_len else None


def extract_prompt(flight):
    """Return dict(prompt, source, declared_len, verified)."""
    fb = flight.encode("utf-8")
    tmpl, _ = find_template_obj(flight)

    if tmpl:
        for key in PROMPT_KEYS:
            val = tmpl.get(key)
            if not isinstance(val, str):
                continue
            if val.startswith("$"):
                text, declared, ok = resolve_ref(fb, val[1:])
                if text:
                    return {"prompt": text, "source": f"template.{key} -> ref {val}",
                            "declared_len": declared, "verified": ok}
            text, declared, ok = val, len(val.encode("utf-8")), True
            if len(text) > 80:
                return {"prompt": text, "source": f"template.{key}",
                        "declared_len": declared, "verified": ok}

    for key in PROMPT_KEYS:
        val = json_string_at(flight, key)
        if val:
            return {"prompt": val, "source": f"flight key {key}",
                    "declared_len": len(val.encode("utf-8")), "verified": True}

    val = longest_text_row(fb)
    if val:
        return {"prompt": val, "source": "fallback: longest T row",
                "declared_len": len(val.encode("utf-8")), "verified": False}
    return None


# --------------------------------------------------------------------------
# listing mode
# --------------------------------------------------------------------------
def build_url(base_url, tid):
    """Build a template detail URL from an id, preserving the /suite prefix."""
    href = f"/home/templates/{tid}"
    if "/suite/" in base_url:
        href = href.replace("/home/", "/suite/home/", 1)
    return urljoin(base_url, href)


def list_templates(flight, base_url):
    """Best-effort: collect template ids/titles embedded in an SSR flight payload.

    NOTE: /suite/home renders its grid client-side (skeletons in HTML), so this
    usually returns nothing for the home feed. Supply --ids or --file in that
    case; see references/rsc-payload-anatomy.md for how to harvest ids.
    """
    seen, out = set(), []
    for m in re.finditer(r'"id":"([A-Za-z0-9]{18,24})","title":"((?:[^"\\]|\\.)*)"', flight):
        tid, title = m.group(1), m.group(2)
        if tid in seen:
            continue
        seen.add(tid)
        out.append({"id": tid, "title": title, "url": build_url(base_url, tid)})
    return out


def parse_targets(text, base_url):
    """Parse a comma/newline separated list of template ids or URLs."""
    items = []
    for raw in re.split(r"[,\s]+", text or ""):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("http"):
            items.append({"id": None, "title": raw.rsplit("/", 1)[-1], "url": raw})
        else:
            items.append({"id": raw, "title": raw, "url": build_url(base_url, raw)})
    return items


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def slugify(text, fallback="template"):
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text or "").strip("-").lower()
    return s or fallback


def describe_settings(tmpl):
    if not tmpl:
        return {}
    h = tmpl.get("handoff") or {}
    s = h.get("sourceSettings") or {}
    return {
        "model": tmpl.get("sourceLabel") or tmpl.get("sourceKind"),
        "formId": h.get("formId"),
        "settings": s,
        "inputs": tmpl.get("sourceReferences") or [],
        "primitives": tmpl.get("primitives") or [],
    }


def write_md(path, tmpl, res, url, title_fallback=None):
    info = describe_settings(tmpl)
    title = (tmpl or {}).get("title") or title_fallback or "OpenArt Template"
    s = info.get("settings") or {}
    bits = []
    if s.get("duration"):
        bits.append(f"{s['duration']} 秒")
    if s.get("aspectRatio"):
        bits.append(s["aspectRatio"])
    if s.get("resolution"):
        bits.append(s["resolution"])
    if "generateAudio" in s:
        bits.append("生成音频开" if s["generateAudio"] else "生成音频关")
    if s.get("videoCount"):
        bits.append(f"{s['videoCount']} 条")
    if s.get("seed") is not None:
        bits.append(f"seed {s['seed']}")

    ins = []
    for p in info.get("primitives") or []:
        ins.append(f"{p.get('title') or p.get('type')}"
                   f"{'（必填）' if p.get('required') else ''}")
    for r in info.get("inputs") or []:
        ins.append(f"{r.get('label') or r.get('id')}（{r.get('kind')}）")

    lines = [
        f"# OpenArt 模板提示词：{title}",
        "",
        f"- 来源：{url}",
        f"- 模板 ID：`{(tmpl or {}).get('id', 'n/a')}`",
        f"- 生成模型：{info.get('model') or 'n/a'}（{info.get('formId') or 'n/a'}）",
        f"- 生成参数：{' / '.join(bits) if bits else 'n/a'}",
        f"- 输入：{'；'.join(ins) if ins else '无'}",
        f"- 提取方式：{res['source']}，声明长度 {res['declared_len']} 字节，"
        f"校验 {'通过' if res['verified'] else '未通过'}",
        "",
        "---",
        "",
        "## 完整提示词（逐字提取）",
        "",
        res["prompt"].strip(),
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# --------------------------------------------------------------------------
def process(url, outdir, debug=False, media=False):
    page = fetch(url)
    flight = extract_flight(page)
    if not flight:
        return {"url": url, "error": "flight payload empty"}

    tmpl, _ = find_template_obj(flight)
    res = extract_prompt(flight)
    if not res:
        return {"url": url, "error": "prompt not found"}

    title = (tmpl or {}).get("title") or fallback_title(flight) or "template"
    slug = slugify(title, (tmpl or {}).get("id") or "template")
    folder = os.path.join(outdir, slug) if media else outdir
    os.makedirs(folder, exist_ok=True)
    if debug:
        with open(os.path.join(folder, "_page.html"), "w", encoding="utf-8") as f:
            f.write(page)
        with open(os.path.join(folder, "_flight.txt"), "w", encoding="utf-8") as f:
            f.write(flight)

    path = write_md(os.path.join(folder, f"{slug}-prompt.md"),
                    tmpl, res, url, title_fallback=fallback_title(flight))
    out = {
        "url": url,
        "id": (tmpl or {}).get("id"),
        "title": title,
        "chars": len(res["prompt"]),
        "bytes": res["declared_len"],
        "verified": res["verified"],
        "source": res["source"],
        "file": path,
        **describe_settings(tmpl),
    }
    if media:
        out["media"] = download_media(tmpl, folder)
    return out


def main():
    ap = argparse.ArgumentParser(description="Extract OpenArt template prompts verbatim.")
    ap.add_argument("url", nargs="?", help="openart.ai template URL or home feed URL")
    ap.add_argument("--html", help="parse a locally saved page instead of fetching")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--list", action="store_true", help="batch mode: many templates at once")
    ap.add_argument("--ids", help="comma-separated template ids (use with --list)")
    ap.add_argument("--file", help="file with one template id or URL per line (use with --list)")
    ap.add_argument("--limit", type=int, default=0, help="max templates in --list mode (0 = all)")
    ap.add_argument("--json", action="store_true", help="print JSON summary to stdout")
    ap.add_argument("--debug", action="store_true", help="dump page.html and flight.txt")
    ap.add_argument("--media", action="store_true",
                    help="also download preview video, thumbnail and input assets "
                         "into a per-template folder")
    ap.add_argument("--force", action="store_true",
                    help="re-download media even if the file already exists")
    args = ap.parse_args()

    if not args.url and not args.html:
        ap.error("provide a URL or --html")

    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)

    global FORCE
    FORCE = args.force

    # offline single page
    if args.html:
        with open(args.html, encoding="utf-8", errors="replace") as f:
            page = f.read()
        flight = extract_flight(page)
        if args.debug:
            with open(os.path.join(outdir, "_flight.txt"), "w", encoding="utf-8") as f:
                f.write(flight)
        tmpl, _ = find_template_obj(flight)
        res = extract_prompt(flight)
        if not res:
            print(json.dumps({"error": "prompt not found"}, ensure_ascii=False))
            sys.exit(2)
        fbt = fallback_title(flight)
        title = (tmpl or {}).get("title") or fbt or "template"
        path = write_md(os.path.join(outdir, f"{slugify(title, 'template')}-prompt.md"),
                        tmpl, res, args.html, title_fallback=fbt)
        print(json.dumps({"file": path, "title": title, "chars": len(res["prompt"]),
                          "bytes": res["declared_len"], "verified": res["verified"]},
                         ensure_ascii=False, indent=2))
        return

    # listing / batch mode
    if args.list:
        if args.ids:
            items = parse_targets(args.ids, args.url)
        elif args.file:
            with open(args.file, encoding="utf-8") as f:
                items = parse_targets(f.read(), args.url)
        else:
            page = fetch(args.url)
            if args.debug:
                with open(os.path.join(outdir, "_page.html"), "w", encoding="utf-8") as f:
                    f.write(page)
            flight = extract_flight(page)
            if args.debug:
                with open(os.path.join(outdir, "_flight.txt"), "w", encoding="utf-8") as f:
                    f.write(flight)
            items = list_templates(flight, args.url)
        if not items:
            log("[list] no template ids found. /suite/home renders its grid client-side - "
                "pass --ids id1,id2 or --file urls.txt (harvest ids from the browser).")
        if args.limit:
            items = items[:args.limit]
        log(f"[list] found {len(items)} templates")
        results = []
        for i, it in enumerate(items, 1):
            log(f"[list] {i}/{len(items)} {it['title']}")
            try:
                results.append(process(it["url"], outdir, args.debug, args.media))
            except Exception as e:
                results.append({"url": it["url"], "title": it["title"], "error": str(e)})
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # single url
    res = process(args.url, outdir, args.debug, args.media)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if "error" in res:
            log(f"ERROR: {res['error']}")
            sys.exit(2)
        log(f"OK  {res['title']}  {res['chars']} chars / {res['bytes']} bytes "
            f"verified={res['verified']}\n -> {res['file']}")


if __name__ == "__main__":
    main()
