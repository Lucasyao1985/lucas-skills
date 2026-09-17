#!/usr/bin/env python
"""Fetch LibTV canvas workflow JSON.

Supports:
  - https://www.liblib.tv/detail/<templateUuid>   (public share page; flight payload fallback, no token needed)
  - https://www.liblib.tv/canvas?projectId=<uuid>&spaceId=<id>  (needs token)
Output:
  <out>/01_工作流JSON/project_full.json   canvas graph (snapshot: nodes+edges / canvas: nodeList+connectionList)
  <out>/01_工作流JSON/project_meta.json   metadata without graph
  <out>/01_工作流JSON/api_response_full.json
  <out>/01_工作流JSON/cover.jpg
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"
API = "https://api.liblib.tv"


def api_get(path, token=None, timeout=30):
    req = urllib.request.Request(API + path, headers={
        "User-Agent": UA,
        "accept": "application/json, text/plain, */*",
        "x-language": "zh",
        "origin": "https://www.liblib.tv",
        "referer": "https://www.liblib.tv/",
        **({"token": token} if token else {}),
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def save_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def parse_flight(page_html):
    """Extract snapshot {nodes,edges,savedAt} from Next.js RSC flight payload."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', page_html)
    stream = "".join(json.loads(c) for c in chunks)
    # direct parse: {"edges":[...]...} embedded as text row
    m = re.search(r'"snapshotData":"\$([0-9]+)"', stream)
    if m:
        row = m.group(1)
        i = stream.find(row + ":T")
        if i >= 0:
            brace = stream.find("{", i)
            return json.JSONDecoder().raw_decode(stream[brace:])[0]
    i = stream.find('"edges":[')
    if i < 0:
        raise RuntimeError("flight 载荷中未找到 edges 数据（页面结构可能已变化）")
    brace = stream.rfind("{", 0, i)
    obj, _ = json.JSONDecoder().raw_decode(stream[brace:])
    return obj


def extract_uuid(s):
    m = re.search(r"/detail/([0-9a-f]{32})", s) or re.search(r"projectId=([0-9a-f]{32})", s)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="detail/canvas URL 或 32 位 uuid")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--token", default=os.environ.get("LIBTV_TOKEN", ""), help="usertoken（导入/私有画布必填）")
    args = ap.parse_args()

    uuid = extract_uuid(args.source) or (args.source.strip() if re.fullmatch(r"[0-9a-f]{32}", args.source.strip()) else None)
    if not uuid:
        sys.exit("无法从输入解析 32 位 uuid")

    d01 = os.path.join(args.out, "01_工作流JSON")
    os.makedirs(d01, exist_ok=True)

    detail, graph, meta = None, None, {}

    # 路径 A：社区模板接口（/detail 页，有 token 时最干净）
    if args.token:
        try:
            resp = api_get(f"/api/community/project/template/detail?projectTemplateUuid={uuid}", args.token)
            if resp.get("code") == 0:
                detail = resp["data"]["detail"]
                graph = json.loads(detail["snapshotData"])
                meta = {k: v for k, v in detail.items() if k != "snapshotData"}
                print(f"[api] code:0 snapshotId={meta.get('snapshotId')}")
        except Exception as e:
            print(f"[api] 模板接口失败，转 flight 解析: {e}")

    # 路径 B：canvas 画布页接口（需要 token + spaceId 在 URL 里）
    if graph is None and "spaceId=" in args.source and args.token:
        sid = re.search(r"spaceId=(\d+)", args.source).group(1)
        resp = api_get(f"/api/canvas/project/detail-by-space?spaceId={sid}&projectUuid={uuid}", args.token)
        if resp.get("code") != 0:
            sys.exit(f"detail-by-space 失败: {resp}")
        detail = resp["data"]["projectDetail"]
        graph = {"nodes": detail.get("nodeList", []), "edges": detail.get("connectionList", []),
                 "savedAt": detail.get("projectDraft", {}).get("lastEditedAtMs")}
        meta = {k: v for k, v in detail.items() if k not in ("nodeList", "connectionList", "projectDraft")}

    # 路径 C：flight 载荷（匿名可用）
    if graph is None:
        page = http_get(f"https://www.liblib.tv/detail/{uuid}").decode("utf-8")
        graph = parse_flight(page)
        print(f"[flight] 解析成功 nodes={len(graph.get('nodes', []))} edges={len(graph.get('edges', []))}")
        m = re.search(r'\\"name\\":\\"([^"\\]{1,120})\\"', page)
        meta = {"templateUuid": uuid, "name": m.group(1) if m else ""}

    json.dump(graph, open(os.path.join(d01, "project_full.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if detail:
        json.dump(detail, open(os.path.join(d01, "api_response_full.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    meta.setdefault("templateUuid", uuid)
    meta["sourceUrl"] = f"https://www.liblib.tv/detail/{uuid}"
    json.dump(meta, open(os.path.join(d01, "project_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 封面
    cover = meta.get("coverUrl") or ""
    if cover.startswith("http"):
        try:
            save_bytes(os.path.join(d01, "cover.jpg"), http_get(cover))
            print(f"[cover] 已保存 cover.jpg")
        except Exception as e:
            print(f"[cover] 下载失败: {e}")

    nodes = graph.get("nodes") or graph.get("nodeList") or []
    edges = graph.get("edges") or graph.get("connectionList") or []
    print(f"✅ nodes: {len(nodes)}  connections: {len(edges)}")
    print(f"输出目录: {d01}")


if __name__ == "__main__":
    main()
