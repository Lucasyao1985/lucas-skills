#!/usr/bin/env python
"""Import a LibTV canvas workflow snapshot into your own account.

LibTV has NO "upload JSON to import" feature. The canvas graph is stored as
node/connection entities; writes go through POST /api/canvas/nodes/batch.
This script converts the snapshot JSON (nodes+edges react-flow dump, or
nodeList+connectionList entity dump) into the wire protocol and imports it.

Field mapping reversed from minified client code (convertNodeToCanvasNode=t6,
convertEdgeToConnection=t8 in the canvas chunks) — see references/import-protocol.md.

Requires: valid usertoken (--token or LIBTV_TOKEN env), your projectSpaceId.
"""
import argparse
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "https://api.liblib.tv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36"

# backend NodeType enum (module 143027): TEXT=1 IMAGE=2 VIDEO=3 AUDIO=4 GROUP=5
# COMMENT=10 TABLE=15 SCRIPT=20 SCRIPT_V2=21 VIDEO_CLIP=35 SPACE_SCENE_720=36 REFERENCE=40 SHOT_BREAKDOWN=45
TYPE_MAP = {"text": 1, "image": 2, "video": 3, "audio": 4, "group": 5,
            "script": 20, "script_v2": 21, "video-clip": 35,
            "space-scene-720": 36, "reference": 40, "shot-breakdown": 45}


def api(method, path, token, body=None):
    req = urllib.request.Request(API + path, method=method, headers={
        "User-Agent": UA, "token": token, "webid": os.environ.get("LIBTV_WEBID", ""),
        "x-language": "zh", "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "origin": "https://www.liblib.tv", "referer": "https://www.liblib.tv/",
    }, data=json.dumps(body or {}, ensure_ascii=False).encode("utf-8"))
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def load_graph(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data.get("data"), dict) and "projectDetail" in data["data"]:
        data = data["data"]["projectDetail"]
    if "projectDetail" in data:
        data = data["projectDetail"]
    if isinstance(data.get("data"), dict) and "detail" in data["data"]:
        data = data["data"]
    if isinstance(data.get("detail"), dict) and "snapshotData" in data["detail"]:
        data = json.loads(data["detail"]["snapshotData"])
    if isinstance(data.get("snapshotData"), str):
        data = json.loads(data["snapshotData"])
    nodes = data.get("nodes") or data.get("nodeList") or []
    edges = data.get("edges") or data.get("connectionList") or []
    return nodes, edges


def node_data(node):
    """Unified node data dict + react-flow-ish fields for both input formats."""
    nd = node.get("data")
    if isinstance(nd, str):
        try:
            nd = json.loads(nd)
        except Exception:
            nd = {}
    return nd


def convert_node(node, project_uuid):
    """Mirror convertNodeToCanvasNode (t6)."""
    d = dict(node_data(node))
    tag = str(d.pop("_tag", "") or "").strip() or None
    fe_type = node.get("type") or node_data(node).get("type")
    if isinstance(fe_type, str):
        fe_type = fe_type.lower()
        backend_type = TYPE_MAP.get(fe_type, 1)
    else:
        backend_type = fe_type if isinstance(fe_type, int) and fe_type > 0 else 1
    if node.get("protectionType") is not None and "protectionType" not in d:
        d["protectionType"] = node["protectionType"]
    if node.get("copyrightChain") and "copyrightChain" not in d:
        d["copyrightChain"] = node["copyrightChain"]
    if node.get("resourceMeta") and "_resourceMeta" not in d:
        d["_resourceMeta"] = node["resourceMeta"]
    pos = node.get("position") or {}
    item = {
        "nodeKey": node.get("id") or node.get("nodeKey"),
        "projectUuid": project_uuid,
        "type": backend_type,
        "name": d.get("name"),
        "position": {"positionX": str(int((pos.get("x") if "x" in pos else float(pos.get("positionX") or 0)))),
                     "positionY": str(int((pos.get("y") if "y" in pos else float(pos.get("positionY") or 0))))},
        "parentKey": node.get("parentId") or node.get("parentKey") or "",
        "data": json.dumps(d, ensure_ascii=False),
    }
    if tag:
        item["tag"] = tag
    m = node.get("measured")
    if m and m.get("width") is not None:
        item["measured"] = {"width": str(m["width"]), "height": str(m["height"])}
    return item


def convert_edge(edge, project_uuid):
    """Mirror convertEdgeToConnection (t8)."""
    return {
        "projectUuid": project_uuid,
        "connectionId": edge["id"] if "id" in edge else edge.get("connectionId"),
        "source": edge["source"],
        "target": edge["target"],
        "sourceHandle": edge.get("sourceHandle") or None,
        "targetHandle": edge.get("targetHandle") or None,
        "type": edge.get("type") or "default",
        "deletable": edge.get("deletable", True),
        "selectable": edge.get("selectable", True),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="project_full.json（nodes+edges 或 nodeList+connectionList）")
    ap.add_argument("--token", default=os.environ.get("LIBTV_TOKEN", ""), help="usertoken（必填）")
    ap.add_argument("--space-id", required=True, help="你的 projectSpaceId")
    ap.add_argument("--name", default="imported-workflow", help="新项目名（建议 ASCII）")
    ap.add_argument("--project-uuid", default="", help="复用已建好的空项目，跳过创建")
    ap.add_argument("--delete-on-fail", action="store_true", help="失败时删除新建项目（默认保留）")
    args = ap.parse_args()
    if not args.token:
        sys.exit("缺少 token：传 --token 或设 LIBTV_TOKEN 环境变量")

    nodes, edges = load_graph(args.input)
    if not nodes:
        sys.exit("输入中未找到节点")
    print(f"source graph: nodes={len(nodes)} edges={len(edges)}")

    # 1. 建项目
    if args.project_uuid:
        puuid = args.project_uuid
        print(f"复用项目 {puuid}")
    else:
        resp = api("POST", "/api/canvas/project/create-with-space", args.token,
                   {"name": args.name, "spaceId": int(args.space_id)})
        if resp.get("code") != 0:
            sys.exit(f"创建项目失败: {resp}")
        puuid = resp["data"]["projectMeta"]["uuid"]
        print(f"新项目 {puuid}（{args.name}）")

    # 2. 写入节点 / 连线（官方分批：节点≤200，连线≤500）
    try:
        for i in range(0, len(nodes), 200):
            chunk = [convert_node(n, puuid) for n in nodes[i:i + 200]]
            r = api("POST", "/api/canvas/nodes/batch", args.token,
                    {"projectUuid": puuid, "nodes": {"create": chunk}, "connections": {},
                     "requestId": f"import:n:{i}"})
            if r.get("code") != 0:
                raise RuntimeError(f"nodes batch {i} 失败: {r}")
            print(f"nodes {min(i + 200, len(nodes))}/{len(nodes)}")
        for i in range(0, len(edges), 500):
            chunk = [convert_edge(e, puuid) for e in edges[i:i + 500]]
            r = api("POST", "/api/canvas/nodes/batch", args.token,
                    {"projectUuid": puuid, "nodes": {}, "connections": {"create": chunk},
                     "requestId": f"import:c:{i}"})
            if r.get("code") != 0:
                raise RuntimeError(f"connections batch {i} 失败: {r}")
            print(f"connections {min(i + 500, len(edges))}/{len(edges)}")

        # 3. 视口（draftJson 固定 "{}"，只存 viewport）
        api("POST", "/api/canvas/project/draft/update", args.token,
            {"projectUuid": puuid, "viewportX": "0", "viewportY": "0", "viewportZoom": "1", "draftJson": "{}"})

        # 4. 校验
        v = api("GET", f"/api/canvas/project/detail-by-space?spaceId={args.space_id}&projectUuid={puuid}",
                args.token)
        if v.get("code") != 0:
            raise RuntimeError(f"校验请求失败: {v}")
        pd = v["data"]["projectDetail"]
        got_n = len(pd.get("nodeList") or [])
        got_e = len(pd.get("connectionList") or [])
        ok = got_n == len(nodes) and got_e == len(edges)
        print(f"{'✅' if ok else '⚠️'} verify: nodes {got_n}/{len(nodes)}  connections {got_e}/{len(edges)}")
        print(f"画布: https://www.liblib.tv/canvas?projectId={puuid}&spaceId={args.space_id}")
        if not ok:
            sys.exit(2)
    except Exception as e:
        print(f"导入失败: {e}")
        if args.delete_on_fail and not args.project_uuid:
            r = api("POST", "/api/canvas/project/delete", args.token, {"projectUuid": puuid})
            print(f"已删除测试项目 {puuid}: code={r.get('code')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
