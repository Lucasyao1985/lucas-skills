#!/usr/bin/env python
"""Batch-download all media assets referenced by a LibTV canvas workflow.

Directory layout (follows the F:\\820 template convention):
  <out>/01_工作流JSON/  workflow JSONs (already present) + cover.jpg
  <out>/02_配图/        images, named {node index:03d}_{node name}_{seq:02d}{ext}
  <out>/03_视频/        videos + 000_成片_final_output.mp4
  <out>/04_音频/        audio
Writes _manifest.tsv and verifies size >=1KB + PNG/JPG/WEBP/MP4 magic bytes.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RES = "libtv-res.liblib.art"
EXT_TYPE = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".gif": "image",
            ".mp4": "video", ".webm": "video", ".mov": "video",
            ".mp3": "audio", ".wav": "audio", ".aac": "audio", ".m4a": "audio"}
SUBDIR = {"image": "02_配图", "video": "03_视频", "audio": "04_音频"}
MAGIC = {".png": (b"\x89PNG", 0), ".jpg": (b"\xff\xd8", 0), ".jpeg": (b"\xff\xd8", 0),
         ".webp": (b"RIFF", 0), ".gif": (b"GIF8", 0), ".mp4": (b"ftyp", 4),
         ".webm": (b"\x1a\x45\xdf\xa3", 0)}


def walk_urls(obj):
    if isinstance(obj, str):
        return [obj] if obj.startswith("http") and RES in obj else []
    if isinstance(obj, dict):
        return [u for v in obj.values() for u in walk_urls(v)]
    if isinstance(obj, list):
        return [u for v in obj for u in walk_urls(v)]
    return []


def clean(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name or "")[:50] or "node"


def load_graph(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data.get("data"), dict) and "projectDetail" in data["data"]:
        data = data["data"]["projectDetail"]
    if "projectDetail" in data:
        data = data["projectDetail"]
    if isinstance(data.get("data"), dict) and "detail" in data["data"]:
        data = data["data"]["detail"]
    if isinstance(data.get("detail"), dict) and "snapshotData" in data["detail"]:
        data = data["detail"]
    if isinstance(data.get("snapshotData"), str):
        det, snap = data, json.loads(data["snapshotData"])
        data = {**{k: v for k, v in det.items() if k != "snapshotData"}, **snap}
    nodes = data.get("nodes") or data.get("nodeList") or []
    edges = data.get("edges") or data.get("connectionList") or []
    return data, nodes, edges


def node_urls(node):
    """URLs from snapshot node (data deep) or entity node (data is JSON string)."""
    nd = node.get("data")
    if isinstance(nd, str):
        try:
            nd = json.loads(nd)
        except Exception:
            nd = {}
    return list(dict.fromkeys(walk_urls(nd))), nd


def build_manifest(data, nodes, edges, out):
    manifest = []
    if (data.get("coverUrl") or "").startswith("http"):
        manifest.append(("01_工作流JSON", "cover.jpg", data["coverUrl"]))
    if (data.get("finalOutput") or "").startswith("http"):
        manifest.append(("03_视频", "000_成片_final_output.mp4", data["finalOutput"]))
    for idx, node in enumerate(nodes, 1):
        urls, nd = node_urls(node)
        name = clean(nd.get("name") or node.get("name") or node.get("id") or node.get("nodeKey"))
        for j, u in enumerate(urls, 1):
            if "/wm/" in u:
                continue
            ext = os.path.splitext(u.split("?")[0])[1].lower()
            if ext not in EXT_TYPE:
                ext = ".png" if "image" in u else ".mp4" if "video" in u else ".bin"
            manifest.append((SUBDIR[EXT_TYPE[ext]], f"{idx:03d}_{name}_{j:02d}{ext}", u))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="project_full.json / api_response_full.json / detail 响应")
    ap.add_argument("--out", required=True, help="输出根目录（沿用 fetch_detail 的 --out）")
    ap.add_argument("--batch", type=int, default=10, help="并发数")
    ap.add_argument("--dry-run", action="store_true", help="只生成清单不下载")
    args = ap.parse_args()

    data, nodes, edges = load_graph(args.input)
    print(f"graph: nodes={len(nodes)} edges={len(edges)}")
    manifest = build_manifest(data, nodes, edges, args.out)

    os.makedirs(os.path.join(args.out, "_report"), exist_ok=True)
    with open(os.path.join(args.out, "_manifest.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["subdir", "filename", "url"])
        w.writerows(manifest)
    print("清单:", Counter(s for s, _, _ in manifest), f"共 {len(manifest)} 个文件")
    if args.dry_run:
        return

    jobs = []
    for s, fn, u in manifest:
        d = os.path.join(args.out, s)
        os.makedirs(d, exist_ok=True)
        jobs.append((os.path.join(d, fn), u))

    done = fail = 0
    for i in range(0, len(jobs), args.batch):
        procs = [subprocess.Popen(["curl", "-s", "-m", "300", "-o", out, u]) for out, u in jobs[i:i + args.batch]]
        for p, (out, u) in zip(procs, jobs[i:i + args.batch]):
            p.wait()
            sz = os.path.getsize(out) if os.path.exists(out) else 0
            if p.returncode == 0 and sz > 0:
                done += 1
            else:
                fail += 1
                print(f"FAIL rc={p.returncode} size={sz} {os.path.basename(out)}")
        print(f"progress: {min(i + args.batch, len(jobs))}/{len(jobs)}")

    # 校验
    ok = small = badmagic = 0
    for out, _u in jobs:
        sz = os.path.getsize(out)
        ext = os.path.splitext(out)[1].lower()
        head = open(out, "rb").read(16)
        m = MAGIC.get(ext)
        if sz < 1024:
            small += 1
            print(f"SMALL {sz}B {out}")
        elif m and not head[m[1]:m[1] + len(m[0])].startswith(m[0]):
            badmagic += 1
            print(f"BADMAGIC {sz}B {out}")
        else:
            ok += 1
    total_mb = sum(os.path.getsize(o) for o, _ in jobs) / 1048576
    print(f"✅ downloaded={done} failed={fail} | verify ok={ok} small={small} badmagic={badmagic} | total {total_mb:.1f} MB")


if __name__ == "__main__":
    main()
