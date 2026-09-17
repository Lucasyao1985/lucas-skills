# -*- coding: utf-8 -*-
"""Download YouTube video descriptions (full, with URLs) without login.

Why this exists
---------------
`yt-dlp --dump-json` no longer works for YouTube watch pages from most
datacenter / VPN IPs: the InnerTube `player` endpoint returns
`LOGIN_REQUIRED: Sign in to confirm you're not a bot`.

But the `next` endpoint (which powers the watch page's sidebar + description
panel) is NOT gated. It returns:

    contents.twoColumnWatchNextResults.results.results.contents[]
      .videoPrimaryInfoRenderer.title                      -> real title
      .videoSecondaryInfoRenderer
        .attributedDescriptionBodyText.attributedDescription
            .content        -> description text, URLs TRUNCATED to ~40 chars
            .commandRuns[]  -> {startIndex, length, onTap.innertubeCommand
                                .urlEndpoint.url = /redirect?...&q=REAL_URL}

So we rebuild the description by splicing each commandRun's real URL back in
(iterate in reverse so indices stay valid). Verified byte-identical against
previously saved files.

Usage
-----
    python fetch_descriptions.py <url> [options]

    <url>   channel URL (https://www.youtube.com/@handle/videos) or a single
            video URL / 11-char video id

Options
    --out DIR        output directory (default: current dir)
    --limit N        for channels: inspect the latest N uploads (default 60)
    --month YYYY-MM  only keep videos whose title contains 【AI 早报 YYYY-MM-DD】
                     (or a plain YYYY-MM-DD) inside that month
    --prefix-fmt     move the trailing 【AI 早报 YYYY-MM-DD】 marker to the front
                     of the filename (default on; --no-prefix-fmt to disable)
    --proxy URL      HTTP proxy, e.g. http://127.0.0.1:7890
    --no-proxy       ignore HTTP(S)_PROXY env vars

Filename rule: `【AI 早报 YYYY-MM-DD】<title with the marker stripped>.txt`
File format:
    Title: <original title>
    URL: https://www.youtube.com/watch?v=<id>
    ---

    <full description>
"""
import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from urllib.parse import parse_qs, unquote, urlparse

sys.stdout.reconfigure(encoding='utf-8')

KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
CLIENT_VERSION = '2.20260801.00.00'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
DATE_RE = re.compile(r'【AI 早报\s*(\d{4})-(\d{2})-(\d{2})】')
DATE_RE_SHORT = re.compile(r'【AI 早报\s*(\d{2})(\d{2})】')
YEAR_RE = re.compile(r'(19|20)\d{2}')


def episode_date(title, date_text=''):
    """Resolve the episode date from the title marker.

    Handles two formats seen on 橘鸦Juya:
      【AI 早报 2026-08-27】  -> 2026-08-27
      【AI 早报0909】          -> year taken from the page's dateText (or current year)
    Returns 'YYYY-MM-DD' or None.
    """
    m = DATE_RE.search(title or '')
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = DATE_RE_SHORT.search(title or '')
    if m:
        year = None
        y = YEAR_RE.search(date_text or '')
        if y:
            year = y.group(0)
        if not year:
            year = time.strftime('%Y')
        return f'{year}-{m.group(1)}-{m.group(2)}'
    return None


def strip_date_marker(title):
    return DATE_RE.sub('', DATE_RE_SHORT.sub('', title or '')).strip()


# --------------------------------------------------------------------------- #
# InnerTube helpers
# --------------------------------------------------------------------------- #
def walk(obj, path=''):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, path + '.' + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + f'[{i}]')


def _unwrap(u):
    """Return the real destination of a YouTube /redirect?...&q= URL."""
    if not isinstance(u, str):
        return None
    if 'youtube.com/redirect' in u or u.startswith('/redirect'):
        qs = parse_qs(urlparse(u).query)
        if 'q' in qs:
            return unquote(qs['q'][0])
    return u if u.startswith('http') else None


def _real_url(cmd):
    if not isinstance(cmd, dict):
        return None
    got = _unwrap(cmd.get('url'))
    if got:
        return got
    for key in ('urlEndpoint', 'commandMetadata'):
        v = cmd.get(key)
        if isinstance(v, dict):
            got = _unwrap(v.get('url'))
            if got:
                return got
    return None


def build_description(ad):
    """Rebuild the untruncated description from an attributedDescription dict."""
    out = ad.get('content') or ''
    for run in sorted(ad.get('commandRuns') or [],
                      key=lambda x: x.get('startIndex', 0), reverse=True):
        st, ln = run.get('startIndex'), run.get('length')
        if st is None or ln is None:
            continue
        tap = run.get('onTap') or {}
        url = _real_url(tap.get('innertubeCommand') or tap)
        if url:
            out = out[:st] + url + out[st + ln:]
    return out


def make_opener(proxy):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))
    elif os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
        pass  # default ProxyHandler already reads env vars
    else:
        handlers.append(urllib.request.ProxyHandler({}))  # ignore env
    handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    return urllib.request.build_opener(*handlers)


def fetch_next(opener, vid, tries=4):
    """Return (title, description) for a video id, via the InnerTube next API."""
    body = json.dumps({
        'context': {'client': {'clientName': 'WEB', 'clientVersion': CLIENT_VERSION,
                               'hl': 'zh-CN', 'gl': 'US'}},
        'videoId': vid, 'contentCheckOk': True, 'racyCheckOk': True,
    }).encode('utf-8')
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                f'https://www.youtube.com/youtubei/v1/next?key={KEY}&prettyPrint=false',
                data=body, method='POST',
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': UA,
                    'X-YouTube-Client-Name': '1',
                    'X-YouTube-Client-Version': CLIENT_VERSION,
                    'Origin': 'https://www.youtube.com',
                    'Referer': f'https://www.youtube.com/watch?v={vid}',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                })
            data = json.loads(opener.open(req, timeout=30).read().decode('utf-8'))
            title = None
            date_text = ''
            for path, node in walk(data):
                if path.endswith('.videoPrimaryInfoRenderer.title'):
                    try:
                        title = ''.join(r['text'] for r in node['runs'])
                    except Exception:
                        pass
                    break
            for path, node in walk(data):
                if path.endswith('.videoPrimaryInfoRenderer.dateText'):
                    date_text = (node.get('simpleText')
                                 or ''.join(r.get('text', '') for r in node.get('runs', [])))
                    break
            panel = None
            for path, node in walk(data):
                if path.endswith('.expandableVideoDescriptionBodyRenderer'
                                  '.attributedDescriptionBodyText'):
                    panel = node
                    break
            if panel is None:
                for path, node in walk(data):
                    if (path.endswith('.attributedDescription')
                            and isinstance(node, dict) and node.get('content')):
                        panel = node
                        break
            if title:
                return {'title': title,
                        'description': build_description(panel) if panel else '',
                        'date_text': date_text}
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f'{vid}: {last}')


def channel_video_ids(channel_url, limit, proxy):
    cmd = ['yt-dlp', '--flat-playlist', '--print', '%(id)s',
           channel_url, '--playlist-end', str(limit)]
    if proxy:
        cmd[1:1] = ['--proxy', proxy]
    res = subprocess.run(cmd, capture_output=True)
    return [line.strip() for line in
            res.stdout.decode('utf-8', 'replace').splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
def safe_name(name, limit=120):
    return re.sub(r'[\\/:*?"<>|]', '', name)[:limit].strip()


def video_id_from_url(url):
    m = re.search(r'(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})', url)
    if m:
        return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        return url
    return None


def save(outdir, vid, info, prefix_fmt=True):
    title, desc = info['title'], info['description']
    if prefix_fmt:
        date = episode_date(title, info.get('date_text', ''))
        if date:
            name = f'【AI 早报 {date}】{strip_date_marker(title)}'
        else:
            name = title or vid
    else:
        name = title or vid
    path = os.path.join(outdir, safe_name(name) + '.txt')
    content = (f'Title: {title}\n'
               f'URL: https://www.youtube.com/watch?v={vid}\n'
               f'---\n\n{desc}')
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return path, ('same' if old == content else ('updated' if old else 'new'))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('url')
    ap.add_argument('--out', default='.')
    ap.add_argument('--limit', type=int, default=60)
    ap.add_argument('--month', default=None, help='YYYY-MM filter')
    ap.add_argument('--no-prefix-fmt', dest='prefix_fmt', action='store_false')
    ap.add_argument('--proxy', default=os.environ.get('HTTPS_PROXY')
                    or os.environ.get('HTTP_PROXY'))
    ap.add_argument('--no-proxy', dest='proxy', action='store_const', const=None)
    args = ap.parse_args()

    opener = make_opener(args.proxy)
    os.makedirs(args.out, exist_ok=True)
    print(f'proxy: {args.proxy or "(none / direct)"}')

    single = video_id_from_url(args.url)
    if single:
        info = fetch_next(opener, single)
        path, state = save(args.out, single, info, args.prefix_fmt)
        print(f'{state:7s} {path} ({len(info["description"])} chars)')
        return

    ids = channel_video_ids(args.url, args.limit, args.proxy)
    print(f'channel returned {len(ids)} ids')
    saved = failed = skipped = 0
    for i, vid in enumerate(ids, 1):
        try:
            info = fetch_next(opener, vid)
        except Exception as exc:  # noqa: BLE001
            print(f'  [FAIL] {vid}: {exc}')
            failed += 1
            continue
        if args.month:
            date = episode_date(info['title'], info.get('date_text', ''))
            if not date or not date.startswith(args.month):
                skipped += 1
                continue
        path, state = save(args.out, vid, info, args.prefix_fmt)
        print(f'  [{i}/{len(ids)}] {state:7s} '
              f'{os.path.basename(path)} ({len(info["description"])} chars)')
        saved += 1
    print(f'\nDONE: {saved} saved, {skipped} skipped, {failed} failed')


if __name__ == '__main__':
    main()
