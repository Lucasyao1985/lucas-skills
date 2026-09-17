#!/usr/bin/env python3
"""Validate an extracted ComfyUI workflow JSON and report its structure.

Checks: JSON parses, node/link counts, node class inventory, optional
fingerprint comparison against a RunningHub app detail (inputNodes IDs).

Examples:
  python rh_validate.py workflow.json
  python rh_validate.py workflow.json --fingerprint 14,118,129,142,86,79
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    # console may be GBK/cp936 and unable to print CJK
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="workflow JSON file")
    ap.add_argument("--fingerprint", default=None,
                    help="comma-separated inputNodes node IDs from the AI App")
    ap.add_argument("--expect-class", default=None,
                    help="node class that must exist, e.g. MiniMaxH3ReferenceToVideo")
    args = ap.parse_args()

    path = Path(args.file)
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        sys.exit("FAIL: not valid JSON: %s" % e)

    if not isinstance(wf, dict) or "nodes" not in wf:
        sys.exit("FAIL: parsed but no 'nodes' key - is this really a ComfyUI workflow?")

    nodes = wf["nodes"]
    links = wf.get("links", [])
    ids = {n.get("id") for n in nodes if isinstance(n, dict) and "id" in n}
    classes = {}
    for n in nodes:
        t = n.get("type") if isinstance(n, dict) else None
        if t:
            classes[t] = classes.get(t, 0) + 1

    print("OK: %d nodes / %d links" % (len(nodes), len(links)))
    print("last_link_id:", wf.get("last_link_id"))
    print("node classes (%d distinct):" % len(classes))
    for t, c in sorted(classes.items(), key=lambda kv: -kv[1]):
        print("  %-45s x%d" % (t[:45], c))

    rc = 0
    if args.expect_class:
        if args.expect_class in classes:
            print("core class check: PASS (%s present)" % args.expect_class)
        else:
            print("core class check: FAIL (%s missing)" % args.expect_class)
            rc = 1

    if args.fingerprint:
        fp = set()
        for piece in args.fingerprint.split(","):
            piece = piece.strip()
            if piece:
                try:
                    fp.add(int(piece))
                except ValueError:
                    pass
        overlap = ids & fp
        if fp and overlap == fp:
            verdict = "FULL MATCH"
        elif overlap:
            verdict = "BASE VERSION (partial match)"
        else:
            verdict = "UNRELATED"
            rc = 1
        print("fingerprint: %d/%d IDs present -> %s" % (len(overlap), len(fp), verdict))
        missing = sorted(fp - ids)
        if missing:
            print("missing fingerprint IDs: %s" % missing)

    sys.exit(rc)


if __name__ == "__main__":
    main()
