#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youvibe_downloader — Download images/files from youvibe.run project pages.

Bypasses three layers of protection:
  1. Proof-of-Work (FNV-1a hash, difficulty prefix '000') -> X-Client-* headers
  2. Anonymous temp login -> Bearer token
  3. Authorized file download via /project_files/{pid}/{asset_path}

Usage:
    python youvibe_download.py <project_id> [--out DIR] [--info]

Only Python standard library is required.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request
import uuid

API_BASE = "https://youvibe.run/vibe_backend"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fnv1a(value: str) -> str:
    """32-bit FNV-1a hash, hex output padded to 8 chars (mirrors site JS)."""
    digest = 2166136261
    for b in value.encode("utf-8"):
        digest ^= b
        digest = (digest * 16777619) & 0xFFFFFFFF
    return format(digest, "08x")


def proof_headers(method: str, path: str) -> dict:
    """Mine a PoW proof whose FNV-1a hex starts with '000' (difficulty 3)."""
    ts = str(int(time.time()))
    n = 0
    while True:
        nonce = f"web-{n}"
        proof = fnv1a(f"{method.upper()}\n{path}\n{ts}\n{nonce}")
        if proof.startswith("000"):
            return {
                "X-Client-Timestamp": ts,
                "X-Client-Nonce": nonce,
                "X-Client-Proof": proof,
            }
        n += 1


def request(method: str, path_qs: str, body=None, token: str = None, binary: bool = False):
    url = API_BASE + path_qs
    path = path_qs.split("?")[0]
    headers = {"User-Agent": "Mozilla/5.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    headers.update(proof_headers(method, path))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=40, context=CTX) as resp:
        raw = resp.read()
    return raw if binary else json.loads(raw.decode("utf-8"))


def temp_login() -> str:
    """Anonymous temp login; returns access_token."""
    body = {"type": "temp", "data": {"device_id": str(uuid.uuid4()), "platform": "web"}}
    data = request("POST", "/user/login", body=body)
    token = data.get("access_token", "")
    if not token:
        raise RuntimeError(f"temp login failed: {json.dumps(data)[:200]}")
    return token


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\|?*\x00-\x1f]', "_", name).strip()
    return name or "file"


def unique_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{i}{ext}")
        i += 1
    return candidate


def main():
    ap = argparse.ArgumentParser(description="Download youvibe.run project media")
    ap.add_argument("project_id", help="project_id from content-viewer URL")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--info", action="store_true", help="print metadata only")
    args = ap.parse_args()

    pid = args.project_id.strip()
    token = temp_login()
    print("[1/3] temp login OK")

    meta = request("GET", f"/project_metadata_by_id/{pid}", token=token)
    print(f"[2/3] metadata OK: {meta.get('project_name', '?')} by {meta.get('author_name', '?')}")

    if args.info:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    images = meta.get("project_images") or []
    if not images:
        print("该项目不含图片 (no project_images)。可用字段:",
              [k for k in meta.keys() if "image" in k or "video" in k or "file" in k])
        sys.exit(2)

    os.makedirs(args.out, exist_ok=True)
    print(f"[3/3] downloading {len(images)} file(s) -> {args.out}")
    ok = 0
    for im in images:
        asset = im.get("asset_path") or ""
        rel_url = im.get("url") or f"/project_files/{pid}/{asset}"
        if rel_url.startswith("/"):
            dl_path = rel_url
        else:
            dl_path = f"/project_files/{pid}/{asset}"
        fname = safe_filename(im.get("original_filename") or os.path.basename(asset) or "image.png")
        try:
            raw = request("GET", dl_path, token=token, binary=True)
            out_path = unique_path(args.out, fname)
            with open(out_path, "wb") as f:
                f.write(raw)
            ok += 1
            print(f"  ✓ {fname}  ({len(raw)//1024} KB)")
        except Exception as e:
            print(f"  ✗ {fname}: {e}")

    print(f"\n✅ 下载完成 {ok}/{len(images)}")
    print(f"- 目录：{os.path.abspath(args.out)}")
    print(f"- 项目：{meta.get('project_name','')} by {meta.get('author_name','')}")


if __name__ == "__main__":
    main()
