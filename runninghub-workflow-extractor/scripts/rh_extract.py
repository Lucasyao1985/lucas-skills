#!/usr/bin/env python3
"""RunningHub workflow extractor.

End-to-end pipeline: classify a RunningHub page, probe the app/workflow APIs,
recover a hidden workflowId via node fingerprint matching, extract the
workflow JSON through the copy endpoint, validate it, and save raw text.

Standard library only. Examples:

  python rh_extract.py https://www.runninghub.ai/ai-detail/2086649152448098305 --token eyJ... --out ./out
  python rh_extract.py https://www.runninghub.ai/workflow-detail/123456 --out ./out
  python rh_extract.py <ai-detail-url> --token eyJ... --owner-user-id 2086640260783665153
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_AI = "https://www.runninghub.ai"
BASE_CN = "https://www.runninghub.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


class RHClient:
    """Minimal JSON POST client for RunningHub."""

    def __init__(self, base=BASE_AI, token=None, cookie_file=None, cookies_raw=None):
        self.base = base.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": UA,
            "Origin": self.base,
            "Referer": self.base + "/",
        }
        if token:
            self.headers["Authorization"] = "Bearer " + token
        cookie_pairs = []
        if cookies_raw:
            cookie_pairs.append(cookies_raw)
        if cookie_file:
            data = json.loads(Path(cookie_file).read_text(encoding="utf-8"))
            # Cookie-Editor export format: list of {name, value}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookie_pairs.append("%s=%s" % (item["name"], item["value"]))
        if cookie_pairs:
            self.headers["Cookie"] = "; ".join(cookie_pairs)

    def post(self, path, payload=None, timeout=30):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload or {}).encode("utf-8"),
            headers=self.headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")

    def post_json(self, path, payload=None):
        status, text = self.post(path, payload)
        try:
            return status, json.loads(text), text
        except json.JSONDecodeError:
            return status, None, text


def classify(url):
    m = re.search(r"/ai-detail/(\d+)", url)
    if m:
        return "webapp", m.group(1)
    m = re.search(r"/workflow-detail/(\d+)", url)
    if m:
        return "workflow", m.group(1)
    sys.exit("ERROR: URL is neither an ai-detail nor workflow-detail link: %s" % url)


def node_ids_of_content(content):
    """Extract the set of node ids from a workflowContent dict/string."""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return set()
    nodes = content.get("nodes") if isinstance(content, dict) else None
    if not isinstance(nodes, list):
        return set()
    ids = set()
    for n in nodes:
        if isinstance(n, dict) and "id" in n:
            ids.add(n["id"])
    return ids


def core_classes_of_content(content):
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return []
    nodes = content.get("nodes") if isinstance(content, dict) else []
    classes = []
    for n in nodes or []:
        if isinstance(n, dict):
            t = n.get("type") or ""
            if t and t not in classes:
                classes.append(t)
    return classes


def main():
    # console may be GBK/cp936 and unable to print CJK from API responses
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Extract a RunningHub ComfyUI workflow.")
    ap.add_argument("url", help="ai-detail or workflow-detail page URL")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--base", default=BASE_AI, help="API base host")
    ap.add_argument("--token", default=None, help="Rh-Accesstoken JWT (Bearer)")
    ap.add_argument("--cookie-file", default=None, help="Cookie-Editor style JSON export")
    ap.add_argument("--cookies-raw", default=None, help="raw Cookie header string")
    ap.add_argument("--owner-user-id", default=None,
                    help="publisher userId for user/list (else taken from detail payload)")
    ap.add_argument("--max-candidates", type=int, default=5,
                    help="max workflows to copy during fingerprint matching")
    ap.add_argument("--report", action="store_true", help="write markdown report")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = RHClient(base=args.base, token=args.token,
                      cookie_file=args.cookie_file, cookies_raw=args.cookies_raw)
    page_type, obj_id = classify(args.url)
    lines = ["# RunningHub Workflow Extraction Report", "",
             "- Page: %s" % args.url,
             "- Type: %s (id %s)" % (page_type, obj_id), ""]
    print("[1] page type: %s, id: %s" % (page_type, obj_id))

    saved_files = []

    def save_json(name, raw_text, label):
        p = out_dir / name
        p.write_text(raw_text, encoding="utf-8")  # RAW text - never re-serialize
        saved_files.append((str(p), label))
        print("    saved: %s (%s)" % (p, label))
        return p

    candidates = []

    if page_type == "workflow":
        wid = obj_id
        print("[2] public workflow -> copy directly")
        st, js, raw = client.post_json("/api/workflow/copy", {"workflowId": wid})
        if st != 200 or not js or js.get("code") != 0:
            sys.exit("copy failed: HTTP %s body=%s" % (st, raw[:300]))
        content = js["data"].get("workflowContent") if isinstance(js.get("data"), dict) else None
        if not content:
            sys.exit("copy succeeded but no workflowContent in response")
        save_json("workflow_%s.json" % wid,
                  content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                  "public workflow copy")
    else:
        print("[2] probing /api/webapp/detail")
        st, js, raw = client.post_json("/api/webapp/detail", {"webappId": obj_id})
        if st != 200 or not js or js.get("code") != 0:
            sys.exit("webapp/detail failed: HTTP %s body=%s" % (st, raw[:300]))
        detail = js.get("data") or {}
        name = detail.get("name") or "unnamed"
        owner = detail.get("publishAccess", {}).get("owner") or args.owner_user_id
        input_nodes = detail.get("inputNodes") or []
        fp_ids = set()
        fp_names = set()
        for n in input_nodes:
            if isinstance(n, dict) and "nodeId" in n:
                try:
                    fp_ids.add(int(n["nodeId"]))
                except (TypeError, ValueError):
                    pass
            if isinstance(n, dict) and n.get("nodeName"):
                fp_names.add(n["nodeName"])
        lines += ["- App name: %s" % name,
                  "- Owner userId: %s" % owner,
                  "- inputNodes count: %d, fingerprint IDs: %s" % (
                      len(input_nodes), sorted(fp_ids))]
        print("    app: %s | owner: %s | fingerprint: %s" % (name, owner, sorted(fp_ids)))

        wid = detail.get("workflowId")
        if wid:
            print("[3] workflowId exposed: %s -> copying" % wid)
        else:
            print("[3] workflowId hidden (expected) -> fingerprint matching")
            if not owner:
                sys.exit("no owner userId in detail; pass --owner-user-id")
            st2, js2, raw2 = client.post_json("/api/workflow/user/list", {"userId": str(owner)})
            rows = (js2.get("data") or {}).get("records") if js2 else None
            if not rows:
                sys.exit("user/list failed: HTTP %s body=%s" % (st2, raw2[:300]))
            print("    publisher has %d public workflows; screening..." % len(rows))
            scored = []
            for row in rows:
                cand_wid = row.get("workflowId") or row.get("id")
                st3, js3, _ = client.post_json("/api/portal/workflow/detail",
                                               {"workflowId": str(cand_wid)})
                meta = (js3.get("data") or {}) if js3 else {}
                title = meta.get("name") or ""
                print("      candidate %s: %r nodeCount=%s" %
                      (cand_wid, title, meta.get("nodeCount")))
                score = 0
                low = title.lower()
                for kw in re.findall(r"[a-z0-9]{3,}", name.lower()):
                    if kw in low:
                        score += 1
                scored.append((score, cand_wid, title))
            scored.sort(reverse=True)
            CONFIDENT = False
            best = None  # (rank_score, wid, title, content, id_overlap, class_overlap)
            for score, cand_wid, title in scored[: args.max_candidates]:
                st4, js4, _ = client.post_json("/api/workflow/copy",
                                               {"workflowId": str(cand_wid)})
                if st4 != 200 or not js4 or js4.get("code") != 0:
                    print("      copy failed for %s (HTTP %s)" % (cand_wid, st4))
                    continue
                data = js4.get("data") or {}
                content = data.get("workflowContent")
                ids = node_ids_of_content(content)
                classes = set(core_classes_of_content(content))
                overlap = len(ids & fp_ids)
                class_hit = len(classes & fp_names)
                class_ratio = (class_hit / len(fp_names)) if fp_names else 0.0
                print("      copied %s: ID overlap %d/%d, class match %d/%d (%.0f%%)"
                      % (cand_wid, overlap, len(fp_ids), class_hit,
                         len(fp_names), class_ratio * 100))
                # confidence gate: full/partial ID match, or strong class-level match.
                # Raw IDs are unreliable when the app graph was renumbered - a
                # candidate with ~0 ID overlap but high class overlap is a BASE
                # VERSION; one with low on BOTH is UNRELATED and must never be
                # auto-saved as the result (false positive).
                confident = (
                    (fp_ids and overlap == len(fp_ids))
                    or (fp_ids and overlap >= max(3, 0.5 * len(fp_ids)))
                    or class_ratio >= 0.6
                )
                rank = (overlap, class_ratio)
                if best is None or rank > best[0]:
                    best = (rank, cand_wid, title, content, overlap, class_ratio)
                if confident:
                    CONFIDENT = True
                if fp_ids and overlap == len(fp_ids):
                    break  # full match
            if not CONFIDENT or best is None:
                print("\nNO CONFIDENT MATCH among public candidates.")
                print("The app's internal graph is likely fully renumbered/extended")
                print("or private. Best-effort candidate by theme: inspect manually.")
                if best is not None:
                    print("closest candidate: %s (%s) ID overlap %d/%d, class %d/%d"
                          % (best[1], best[2], best[4], len(fp_ids), best[5], len(fp_names)))
                sys.exit(2)
            _, wid, title, content, overlap, class_ratio = best
            verdict = ("FULL MATCH" if fp_ids and overlap == len(fp_ids)
                       else "BASE VERSION (partial ID/class match)")
            lines += ["- Selected workflowId: %s (%s)" % (wid, title),
                      "- Fingerprint verdict: %s (IDs %d/%d, classes %d/%d)"
                      % (verdict, overlap, len(fp_ids), int(class_ratio * len(fp_names)),
                         len(fp_names))]
            print("[4] selected %s -> %s" % (wid, verdict))
        safe_name = re.sub(r'[\\/:*?"<>|]+', "_", name) or "workflow"
        save_json("%s_%s.json" % (safe_name, wid),
                  content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                  "extracted workflow")

    print("[5] validation")
    last_file = Path(saved_files[-1][0])
    parsed = json.loads(last_file.read_text(encoding="utf-8"))
    nodes = parsed.get("nodes", [])
    links = parsed.get("links", [])
    classes = core_classes_of_content(parsed)
    lines += ["- Validation: JSON OK, %d nodes / %d links" % (len(nodes), len(links)),
              "- Node classes: %s" % ", ".join(classes[:20])]
    print("    %d nodes / %d links" % (len(nodes), len(links)))

    if args.report:
        rp = out_dir / "extraction-report.md"
        rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("[6] report: %s" % rp)
    print("DONE")


if __name__ == "__main__":
    main()
