#!/usr/bin/env python3
"""Repair UTF-8-as-Latin-1 double-encoded (mojibake) Chinese text inside a
ComfyUI workflow JSON - locally and losslessly, no network reference needed.

Damage model: UTF-8 bytes were read as Latin-1 chars, then saved back as
UTF-8. Reversal: map each mojibake char back through Latin-1 to bytes, then
decode the byte string as UTF-8. Example: E6 85 A2 ("慢") becomes
"æ\u0085¢"; reversed it yields "慢" again.

The repair is applied by targeted replacement on the RAW file text so all
other bytes stay untouched. A .bak backup is written first unless --no-backup.

Example:
  python fix_mojibake.py Dasiwa_V1_SLA加速_MiniMaxH3_工作流.json
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# Latin-1 expanded form of multi-byte UTF-8:
# lead byte range C2..F4 mapped to U+00C2..U+00F4, continuation 80..BF -> U+0080..U+00BF
MOJIBAKE_RE = re.compile(r"[\u00c2-\u00f4](?:[\u0080-\u00bf])+")


def try_reverse(s):
    """Return repaired text, or None if s is not reversible mojibake."""
    try:
        raw = s.encode("latin-1")
    except UnicodeEncodeError:
        return None
    try:
        fixed = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\ufffd" in fixed:
        return None
    # sanity: result should contain non-ASCII (otherwise nothing was gained)
    if fixed == s or all(ord(c) < 128 for c in fixed):
        return None
    return fixed


def main():
    # console may be GBK/cp936 and unable to print mojibake chars
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="workflow JSON file (UTF-8)")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    path = Path(args.file)
    text = path.read_text(encoding="utf-8")

    matches = list(MOJIBAKE_RE.finditer(text))
    pairs = {}   # broken -> fixed, with occurrence counts
    total_hits = 0
    for m in matches:
        broken = m.group(0)
        fixed = try_reverse(broken)
        if fixed is None:
            continue
        total_hits += 1
        pairs[broken] = fixed

    if not pairs:
        print("No reversible mojibake sequences found. Nothing to do.")
        return

    replaced = 0
    new_text = text
    for broken, fixed in sorted(pairs.items(), key=lambda kv: -len(kv[0])):
        n = new_text.count(broken)
        if n:
            new_text = new_text.replace(broken, fixed)
            replaced += n
            preview = fixed if len(fixed) <= 30 else fixed[:27] + "..."
            print("fixed x%d: %s -> %s" % (n, broken[:24], preview))

    print("\nscanned sequences: %d | distinct repairs: %d | replacements applied: %d"
          % (total_hits, len(pairs), replaced))
    if replaced != total_hits:
        print("WARNING: replacement count != scan count - inspect manually.")

    if args.dry_run:
        print("dry-run: file NOT modified.")
        return

    if not args.no_backup:
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print("backup written: %s" % bak)

    path.write_text(new_text, encoding="utf-8")

    # final integrity check
    try:
        parsed = json.loads(new_text)
        nodes = len(parsed.get("nodes", [])) if isinstance(parsed, dict) else "?"
        links = len(parsed.get("links", [])) if isinstance(parsed, dict) else "?"
        residual = len(MOJIBAKE_RE.findall(new_text))
        print("post-check: JSON OK, %s nodes / %s links, residual mojibake sequences: %d"
              % (nodes, links, residual))
        print("DONE")
    except json.JSONDecodeError as e:
        sys.exit("ERROR: output no longer parses as JSON: %s" % e)


if __name__ == "__main__":
    main()
