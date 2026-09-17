#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download a WeChat Official Account (微信公众号) article as Markdown + HTML, with all images saved locally.

Usage:
    python -X utf8 download_article.py <article_url> [--output DIR] [--format md|html|both] [--no-images]

Outputs (under --output, default ./<article-title>/):
    index.md      Markdown with metadata header and local image links
    index.html    Standalone HTML preserving the original WeChat styling
    images/       All article images, named 001.jpg, 002.png, ...
"""
import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

INLINE_TAGS = {"span", "strong", "b", "em", "i", "u", "s", "code", "a", "img",
               "font", "small", "sub", "sup", "mark", "br", "nobr"}

DELETED_MARKERS = ("该内容已被发布者删除", "此内容因违规无法查看", "此帐号已自主注销",
                   "内容不存在", "参数错误")


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def sanitize(name, maxlen=80):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", str(name))
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name[:maxlen].strip() or "wechat-article"


def fetch_html(url):
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if attempt == 2:
                die(f"无法抓取页面: {e}")
            time.sleep(2 * (attempt + 1))


def extract_meta(soup, html):
    el = soup.find(id="activity-name")
    title = el.get_text(strip=True) if el else ""
    if not title:
        t = soup.find("title")
        title = t.get_text(strip=True) if t else ""

    el = soup.find(id="js_name")
    account = el.get_text(strip=True) if el else ""

    author = ""
    el = soup.find("meta", attrs={"name": "author"})
    if el and el.get("content"):
        author = el["content"].strip()

    publish = ""
    m = re.search(r"var\s+(?:ct|oriCreateTime)\s*=\s*['\"]?(\d{9,11})['\"]?", html)
    if m:
        publish = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d %H:%M")

    digest = ""
    el = soup.find("meta", attrs={"property": "og:description"})
    if el and el.get("content"):
        digest = el["content"].strip()

    return {"title": title, "account": account, "author": author,
            "publish": publish, "digest": digest}


def guess_ext(url, tag):
    fmt = ""
    if tag and tag.get("data-type"):
        fmt = tag["data-type"]
    if not fmt:
        fmt = parse_qs(urlsplit(url).query).get("wx_fmt", [""])[0]
    fmt = fmt.lower().strip()
    if fmt in ("jpg", "jpeg"):
        return "jpg"
    if fmt in ("png", "gif", "webp", "svg", "bmp"):
        return fmt
    return "jpg"


def download_images(content, img_dir, session):
    img_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0
    for i, img in enumerate(content.find_all("img"), 1):
        url = img.get("data-src") or img.get("src") or ""
        if not url.startswith("http"):
            img.decompose()
            continue
        ext = guess_ext(url, img)
        fname = f"{i:03d}.{ext}"
        rel = f"images/{fname}"
        saved = False
        for attempt in range(2):
            try:
                r = session.get(url, headers={"User-Agent": UA,
                                              "Referer": "https://mp.weixin.qq.com/"},
                                timeout=30)
                if r.status_code == 200 and r.content:
                    (img_dir / fname).write_bytes(r.content)
                    saved = True
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        if saved:
            ok += 1
            img["src"] = rel
        else:
            failed += 1
            img["src"] = url  # keep remote URL as fallback
        # drop lazy-load attrs so the HTML renders correctly
        for attr in ("data-src", "data-type", "data-ratio", "data-w"):
            if attr in img.attrs:
                del img[attr]
    return ok, failed


def norm_ws(text):
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u00a0]+", " ", line).strip()
        lines.append(line)
    return "\n".join(lines)


def wrap_marked(text, marker):
    lead = re.match(r"^\s*", text).group(0)
    tail = re.search(r"\s*$", text).group(0)
    core = text[len(lead):len(text) - len(tail)]
    if not core:
        return text
    inner = core.replace(f"{marker}{marker}", marker)
    return f"{lead}{marker}{core}{marker}{tail}"


def render_node(child):
    """Render a single inline-level node itself (tag marker included)."""
    if isinstance(child, NavigableString):
        return str(child)
    name = child.name
    if name == "br":
        return "\n"
    if name == "img":
        src = child.get("src") or child.get("data-src") or ""
        if src:
            return f"![{child.get('alt', '').strip()}]({src})"
        return ""
    if name in ("strong", "b"):
        return wrap_marked(inline_md(child), "**")
    if name in ("em", "i", "cite"):
        return wrap_marked(inline_md(child), "*")
    if name == "code":
        txt = child.get_text().replace("`", "'")
        return f"`{txt}`"
    if name == "a":
        href = (child.get("href") or "").strip()
        inner = inline_md(child).strip()
        if href and inner and not href.startswith("javascript"):
            return f"[{inner}]({href})"
        return inline_md(child)
    return inline_md(child)


def inline_md(node):
    return "".join(render_node(child) for child in node.children)


def blocks_md(element, depth=0):
    blocks = []
    buf = []

    def flush():
        text = norm_ws("".join(buf))
        for line in text.split("\n"):
            if line.strip():
                blocks.append(line)
        buf.clear()

    for child in element.children:
        if isinstance(child, NavigableString):
            buf.append(str(child))
            continue
        name = child.name
        if name in ("script", "style"):
            continue
        if name in INLINE_TAGS:
            buf.append(render_node(child))
            continue
        flush()
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = norm_ws(inline_md(child)).replace("\n", " ").strip()
            if text:
                blocks.append("#" * int(name[1]) + " " + text)
        elif name == "hr":
            blocks.append("---")
        elif name == "pre":
            code = child.get_text().rstrip("\n")
            lang = ""
            code_tag = child.find("code")
            if code_tag and code_tag.get("class"):
                m = re.search(r"language-([\w+-]+)", " ".join(code_tag["class"]))
                if m:
                    lang = m.group(1)
            blocks.append(f"```{lang}\n{code}\n```")
        elif name == "blockquote":
            inner = "\n\n".join(blocks_md(child, depth))
            if inner.strip():
                blocks.append("\n".join("> " + ln if ln else ">"
                                        for ln in inner.split("\n")))
        elif name in ("ul", "ol"):
            blocks.extend(list_md(child, depth))
        elif name == "table":
            tbl = table_md(child)
            if tbl:
                blocks.append(tbl)
        elif name == "iframe":
            src = child.get("data-src") or child.get("src") or ""
            if src:
                blocks.append(f"[视频] {src}")
        elif name in ("mpvoice", "mp-common-mpvoice"):
            blocks.append("[语音消息]")
        elif name == "mp-common-profile":
            nick = child.get("nickname", "")
            blocks.append(f"[公众号卡片] {nick}".rstrip())
        else:  # p, div, section, figure, figcaption, ...
            sub = blocks_md(child, depth)
            only_img = (len(sub) == 1 and re.fullmatch(r"!\[.*\]\(.*\)", sub[0].strip())
                        and name in ("figure", "section", "p", "div"))
            if only_img:
                blocks.append(sub[0].strip())
            else:
                blocks.extend(sub)
    flush()
    return blocks


def list_md(node, depth=0):
    out = []
    ordered = node.name == "ol"
    idx = 1
    for li in node.find_all("li", recursive=False):
        marker = f"{idx}. " if ordered else "- "
        if ordered:
            idx += 1
        pad = "  " * depth
        # split nested lists from this li's own content
        nested, content = [], []
        for ch in li.children:
            if isinstance(ch, Tag) and ch.name in ("ul", "ol"):
                nested.append(ch)
            else:
                content.append(ch)
        holder = BeautifulSoup(f"<li></li>", "html.parser").li
        for ch in content:
            holder.append(ch.extract() if isinstance(ch, Tag) else ch)
        lines = blocks_md(holder, depth)
        if not lines:
            continue
        out.append(pad + marker + lines[0])
        for extra in lines[1:]:
            out.append(pad + "  " + extra)
        for nl in nested:
            out.extend(list_md(nl, depth + 1))
    return out


def table_md(table):
    rows = table.find_all("tr")
    if not rows:
        return ""
    grid = []
    for tr in rows:
        cells = tr.find_all(["td", "th"], recursive=False) or tr.find_all(["td", "th"])
        row = [norm_ws(inline_md(c)).replace("\n", " ").strip() or " "
               for c in cells]
        grid.append(row)
    if not grid or all(len(r) == 0 for r in grid):
        return ""
    width = max(len(r) for r in grid)
    for r in grid:
        r.extend([" "] * (width - len(r)))
    lines = ["| " + " | ".join(grid[0]) + " |",
             "|" + "|".join([" --- "] * width) + "|"]
    for r in grid[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def build_markdown(meta, url, content):
    head = [f"# {meta['title']}", ""]
    meta_line = " · ".join(x for x in (
        f"公众号: {meta['account']}" if meta["account"] else "",
        f"作者: {meta['author']}" if meta["author"] else "",
        f"发布时间: {meta['publish']}" if meta["publish"] else "") if x)
    if meta_line:
        head += [f"> {meta_line}  ", f"> 原文: {url}", ""]
    if meta["digest"]:
        head += [f"> 摘要: {meta['digest']}", ""]
    body_blocks = blocks_md(content)
    # collapse consecutive duplicate blank produced by layout sections
    md = "\n\n".join(head + body_blocks) + "\n"
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ max-width: 677px; margin: 0 auto; padding: 24px 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue",
  "PingFang SC", "Microsoft YaHei", sans-serif; color: #333;
  font-size: 17px; line-height: 1.75; }}
h1 {{ font-size: 22px; line-height: 1.4; margin: 0 0 8px; }}
.meta {{ color: #888; font-size: 14px; margin-bottom: 24px;
  border-bottom: 1px solid #eee; padding-bottom: 12px; }}
.meta a {{ color: #576b95; text-decoration: none; word-break: break-all; }}
img {{ max-width: 100%; height: auto; }}
blockquote {{ border-left: 4px solid #ddd; margin: 0; padding: 0 16px;
  color: #666; }}
pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px;
  overflow-x: auto; }}
code {{ font-family: Consolas, Monaco, monospace; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">{meta_html}<br>原文: <a href="{url}">{url}</a></div>
{content_html}
</body>
</html>
"""


def build_html(meta, url, content_tag):
    import html as html_mod
    meta_bits = []
    if meta["account"]:
        meta_bits.append(html_mod.escape(f"公众号: {meta['account']}"))
    if meta["author"]:
        meta_bits.append(html_mod.escape(f"作者: {meta['author']}"))
    if meta["publish"]:
        meta_bits.append(html_mod.escape(f"发布时间: {meta['publish']}"))
    # re-enable visibility (WeChat ships js_content with visibility:hidden)
    if content_tag.has_attr("style"):
        content_tag["style"] = re.sub(r"visibility\s*:\s*hidden\s*;?", "",
                                      content_tag.get("style", ""))
    meta_bits = [html_mod.escape(x) for x in meta_bits]
    return HTML_TEMPLATE.format(
        title=html_mod.escape(meta["title"]),
        meta_html=" · ".join(meta_bits),
        url=html_mod.escape(url, quote=True),
        content_html=str(content_tag))


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="下载微信公众号文章为 Markdown/HTML")
    ap.add_argument("url", help="文章链接，如 https://mp.weixin.qq.com/s/xxxx")
    ap.add_argument("--output", "-o", help="输出目录，默认为 ./<文章标题>/")
    ap.add_argument("--format", "-f", choices=["md", "html", "both"],
                    default="both", help="输出格式，默认 both")
    ap.add_argument("--no-images", action="store_true", help="不下载图片，保留远程链接")
    args = ap.parse_args()

    if "mp.weixin.qq.com" not in args.url:
        die(f"不是微信公众号文章链接: {args.url}")

    html = fetch_html(args.url)
    for marker in DELETED_MARKERS:
        if marker in html:
            die(f"文章不可用（{marker}），可能已被删除或需要验证")

    soup = BeautifulSoup(html, "html.parser")
    meta = extract_meta(soup, html)
    content = soup.find(id="js_content")
    if content is None:
        die("页面中没有找到正文（#js_content）。可能需要验证、或是非图文类型页面。"
            "可尝试用浏览器打开该链接确认。")

    for tag in content.find_all(["script", "style"]):
        tag.decompose()

    out_dir = Path(args.output) if args.output else Path.cwd() / sanitize(meta["title"])
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    img_ok = img_failed = 0
    if args.no_images:
        for img in content.find_all("img"):
            img["src"] = img.get("data-src") or img.get("src") or ""
    else:
        img_ok, img_failed = download_images(content, out_dir / "images", session)

    result = {"title": meta["title"], "account": meta["account"],
              "publish": meta["publish"], "output_dir": str(out_dir),
              "images_ok": img_ok, "images_failed": img_failed}

    if args.format in ("md", "both"):
        md_path = out_dir / "index.md"
        md_path.write_text(build_markdown(meta, args.url, content), encoding="utf-8")
        result["markdown"] = str(md_path)
    if args.format in ("html", "both"):
        html_path = out_dir / "index.html"
        html_path.write_text(build_html(meta, args.url, content), encoding="utf-8")
        result["html"] = str(html_path)

    print("SUCCESS " + __import__("json").dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
