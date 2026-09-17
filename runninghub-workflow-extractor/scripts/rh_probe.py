#!/usr/bin/env python3
"""Probe RunningHub API endpoints with optional auth.

Useful for Step-4 style manual exploration before running the full pipeline.

Examples:
  python rh_probe.py /api/webapp/detail '{"webappId":"123"}'
  python rh_probe.py /api/workflow/copy '{"workflowId":"456"}' --token eyJ...
  python rh_probe.py /api/user/cost/average '{}' --cookie-file cookies.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rh_extract import RHClient, BASE_AI  # noqa: E402


def main():
    # console may be GBK/cp936 and unable to print CJK from API responses
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="API path, e.g. /api/webapp/detail")
    ap.add_argument("body", nargs="?", default="{}", help="JSON body string")
    ap.add_argument("--base", default=BASE_AI)
    ap.add_argument("--token", default=None)
    ap.add_argument("--cookie-file", default=None)
    ap.add_argument("--cookies-raw", default=None)
    args = ap.parse_args()

    try:
        payload = json.loads(args.body)
    except json.JSONDecodeError:
        sys.exit("body is not valid JSON: %s" % args.body)

    client = RHClient(base=args.base, token=args.token,
                      cookie_file=args.cookie_file, cookies_raw=args.cookies_raw)
    status, js, raw = client.post_json(args.path, payload)
    print("HTTP %s | parsed=%s" % (status, js is not None))
    print(raw[:2000])
    if len(raw) > 2000:
        print("... (truncated, %d chars total)" % len(raw))


if __name__ == "__main__":
    main()
