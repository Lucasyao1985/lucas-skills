#!/usr/bin/env python3
"""Download TikTok videos as watermark-free MP4.

Usage:
    python download_tiktok.py <video_url> <output_path> [--proxy URL] [--impersonate NAME]

The script:
1. Fetches the TikTok page using curl_cffi with a browser TLS fingerprint.
2. Parses __UNIVERSAL_DATA_FOR_REHYDRATION__ to find video.playAddr.
3. Downloads with the same session (preserves tt_chain_token) and Referer.
"""
import argparse
import json
import os
import re
import sys

import curl_cffi.requests as requests

DEFAULT_PROXY = "http://127.0.0.1:7890"
DEFAULT_IMPERSONATE = "safari"
KNOWN_GOOD_IMPERSONATES = ("safari", "firefox", "chrome", "chrome110", "chrome120")


def fetch_page(session: requests.Session, video_url: str, impersonate: str):
    """Fetch the TikTok page and raise if it is a bot/maintenance page."""
    r = session.get(video_url, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Page returned HTTP {r.status_code}")

    # Akamai block page is very small and has no video data
    if len(r.text) < 1000 or "Site Maintenance" in r.text:
        raise RuntimeError(
            "Received bot/maintenance page. "
            "Try another impersonate fingerprint: "
            + ", ".join(KNOWN_GOOD_IMPERSONATES)
        )
    return r


def extract_video_item(html: str):
    """Return itemStruct dict from __UNIVERSAL_DATA_FOR_REHYDRATION__."""
    match = re.search(
        r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("__UNIVERSAL_DATA_FOR_REHYDRATION__ not found")

    data = json.loads(match.group(1))
    vd = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]
    if vd.get("statusCode") != 0:
        raise RuntimeError(
            f"Video unavailable: statusCode={vd.get('statusCode')} statusMsg={vd.get('statusMsg')}"
        )
    return vd["itemInfo"]["itemStruct"]


def select_stream_url(video: dict) -> str:
    """Prefer playAddr; fallback to best H.264 bitrate."""
    if video.get("playAddr"):
        return video["playAddr"]

    # Prefer H.264 for compatibility; fall back to first available
    fallback = None
    for br in video.get("bitrateInfo", []):
        play_addr = br.get("PlayAddr") or {}
        url_list = play_addr.get("UrlList") or []
        if not url_list:
            continue
        if fallback is None:
            fallback = url_list[0]
        url_key = play_addr.get("UrlKey", "")
        if "_h264_" in url_key:
            return url_list[0]

    if fallback:
        return fallback

    raise RuntimeError("No playable URL found in video data")


def download_tiktok(video_url: str, output_path: str, proxy: str = DEFAULT_PROXY,
                    impersonate: str = DEFAULT_IMPERSONATE) -> dict:
    """Download a TikTok video to output_path.

    Returns:
        dict with keys: success, output_path, file_size, width, height,
                        duration, content_type, error
    """
    session = requests.Session()
    session.impersonate = impersonate
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    # Step 1: Fetch page and retain cookies
    page = fetch_page(session, video_url, impersonate)

    # Step 2: Parse video item
    item = extract_video_item(page.text)
    video = item["video"]

    # Step 3: Pick watermark-free URL
    stream_url = select_stream_url(video)

    # Step 4: Download with same session + Referer
    headers = {"Referer": video_url}
    r = session.get(stream_url, headers=headers, timeout=60, stream=True)
    if r.status_code != 200:
        raise RuntimeError(f"Video download failed: HTTP {r.status_code}")

    content_type = r.headers.get("content-type", "")
    if "video" not in content_type:
        raise RuntimeError(f"Unexpected content-type: {content_type}")

    # Step 5: Save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    total = 0
    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)
                total += len(chunk)

    if total < 10 * 1024:
        raise RuntimeError("Downloaded file is too small; likely an error page")

    return {
        "success": True,
        "output_path": output_path,
        "file_size": total,
        "content_type": content_type,
        "width": video.get("width"),
        "height": video.get("height"),
        "duration": video.get("duration"),
    }


def main():
    parser = argparse.ArgumentParser(description="Download watermark-free TikTok video")
    parser.add_argument("video_url", help="TikTok video URL")
    parser.add_argument("output_path", help="Destination MP4 path")
    parser.add_argument("--proxy", default=DEFAULT_PROXY,
                        help=f"Proxy URL (default: {DEFAULT_PROXY}); empty to disable")
    parser.add_argument("--impersonate", default=DEFAULT_IMPERSONATE,
                        help=f"Browser fingerprint (default: {DEFAULT_IMPERSONATE})")
    args = parser.parse_args()

    try:
        result = download_tiktok(
            args.video_url, args.output_path,
            proxy=args.proxy, impersonate=args.impersonate,
        )
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)

    size_mb = result["file_size"] / 1024 / 1024
    print("✅ TikTok 下载完成")
    print(f"- 文件: {result['output_path']}")
    print(f"- 大小: {size_mb:.1f} MB")
    if result.get("width") and result.get("height"):
        print(f"- 分辨率: {result['width']}×{result['height']}")
    if result.get("duration"):
        print(f"- 时长: {result['duration']} 秒")
    print("- 格式: MP4（无水印）")


if __name__ == "__main__":
    main()
