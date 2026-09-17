#!/usr/bin/env python3
"""convert_time.py - Convert Seedance time ranges into MiniMax H3 timestamps.

Seedance prompts express shots as ranges (0-3s, 3s-6s, 00:01.8-00:02.8,
第0到3秒 ...). MiniMax H3 expects per-shot cut points written as
``At MM:SS.mmm`` with strictly increasing values inside the total duration.
This tool performs that conversion deterministically.

Usage:
    python convert_time.py "0-3s, 3-6s, 6-10s"
    python convert_time.py "(0:00-0:01.8), (0:01.8-0:02.8)" --style h3
    python convert_time.py --ranges "0-3s;3-6s;6-10s" --json
    python convert_time.py "0-3s, 3-6s" --strict-base   # omit Shot 1 zero anchor

Styles:
    table  human-readable mapping table (default)
    h3     ready-to-paste [Shot N] skeleton lines
    json   machine-readable report

Exit codes: 0 ok, 2 usage/parse error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TIME_RE = re.compile(
    r"""(?P<min>\d{1,2}):(?P<sec>\d{1,2}(?:\.\d{1,3})?)   # m:ss / mm:ss(.mmm)
      | (?P<only>\d+(?:\.\d{1,3})?)                       # bare seconds
    """,
    re.VERBOSE,
)

RANGE_ITEM_SPLIT_RE = re.compile(r"[,;\n]+")

CN_PREFIXES = ("第", "从")


def parse_time(token: str) -> float:
    """Parse one time token (m:ss(.mmm) or seconds) into float seconds."""
    token = token.strip()
    if not token:
        raise ValueError("empty time token")
    match = TIME_RE.fullmatch(token)
    if not match:
        raise ValueError(f"unrecognized time token: {token!r}")
    if match.group("min") is not None:
        minutes = int(match.group("min"))
        seconds = float(match.group("sec"))
        return minutes * 60.0 + seconds
    return float(match.group("only"))


def clean_token(token: str) -> str:
    """Strip Seedance decorations: 'Shot N' labels and Chinese 第/从 ... 秒 wrappers."""
    token = token.strip()
    token = re.sub(r"(?i)\bshot\s*\d+\s*[:：]?", " ", token)
    for p in CN_PREFIXES:
        if token.startswith(p):
            token = token[len(p):]
    return token.strip()


def parse_ranges(raw: str) -> List[Tuple[float, float]]:
    """Parse a comma/semicolon/newline separated list of time ranges.

    Each item must contain exactly two time tokens; separators may be
    '-', '--', en/em dash, '~', Chinese dao/zhi, parentheses or spaces.
    """
    items = [it for it in RANGE_ITEM_SPLIT_RE.split(raw) if it.strip()]
    if not items:
        raise ValueError("no ranges provided")
    out: List[Tuple[float, float]] = []
    for item in items:
        cleaned = clean_token(item)
        tokens = [m.group(0) for m in TIME_RE.finditer(cleaned)]
        # merge minute-second pairs: TIME_RE may split '0:01' into '0'+':01'? no,
        # the regex consumes them atomically, so len(tokens)==2 is expected.
        if len(tokens) < 2:
            raise ValueError(
                f"range {item.strip()!r} needs a start and an end "
                f"(e.g. '0-3s'); detected time tokens: {tokens}"
            )
        if len(tokens) > 2:
            raise ValueError(
                f"range {item.strip()!r} contains more than two time values "
                f"(drop descriptive text from range lists); detected: {tokens}"
            )
        start, end = parse_time(tokens[0]), parse_time(tokens[1])
        if end <= start:
            raise ValueError(f"non-increasing range: {item.strip()!r}")
        out.append((start, end))
    return out


def fmt(seconds: float) -> str:
    """Format seconds as H3 MM:SS.mmm."""
    total_ms = round(seconds * 1000)
    minutes, rem_ms = divmod(total_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{minutes:02d}:{secs:02d}.{ms:03d}"


def build_report(ranges: List[Tuple[float, float]]) -> dict:
    duration = ranges[-1][1]
    prev_end = 0.0
    rows = []
    for idx, (start, end) in enumerate(ranges, start=1):
        issues = []
        if abs(start - prev_end) > 0.0005 and start >= prev_end:
            issues.append(f"gap of {start - prev_end:.3f}s after previous range")
        elif start < prev_end - 0.0005:
            issues.append("OVERLAP with previous range")
        rows.append(
            {
                "shot": idx,
                "seedance_range": f"{fmt(start)}-{fmt(end)}",
                "cut_point": fmt(start),
                "end": fmt(end),
                "issues": issues,
            }
        )
        prev_end = max(prev_end, end)
    return {"duration": fmt(duration), "duration_seconds": round(duration, 3), "shots": rows}


def render_table(report: dict, strict_base: bool) -> str:
    lines = [
        "Seedance -> H3 timeline conversion",
        "-" * 64,
        f"{'Shot':<6}{'Seedance range':<24}{'H3 cut point':<18}Note",
        "-" * 64,
    ]
    for row in report["shots"]:
        note = "first shot (zero anchor omitted)" if (strict_base and row["shot"] == 1) else ""
        if row["issues"]:
            note = ("; ".join(row["issues"]) + (" " if note else "")) + note
        lines.append(f"{row['shot']:<6}{row['seedance_range']:<24}{row['cut_point']:<18}{note}")
    lines.append("-" * 64)
    lines.append(f"Total duration: {report['duration']} ({report['duration_seconds']}s)")
    if not strict_base:
        lines.append('Closing fade line suggestion: The frame fades to black by %s.' % report["duration"])
    return "\n".join(lines)


def render_h3(report: dict, strict_base: bool) -> str:
    lines = []
    for row in report["shots"]:
        n = row["shot"]
        if strict_base and n == 1:
            lines.append(f"[Shot {n}] <describe opening composition, style, subject action> ...")
        else:
            lines.append(f"[Shot {n}] At {row['cut_point']}, <the camera cuts to ... describe this shot> ...")
    lines.append("")
    lines.append(f"# Total duration: {report['duration']} - closing fade: 'The frame fades to black by {report['duration']}.'")
    if strict_base:
        lines.append("# Note: strict base mode - Shot 1 carries no timestamp (official base-en.txt style).")
    else:
        lines.append("# Note: zero-anchor mode - Shot 1 keeps 'At 00:00.000' so every Seedance range maps 1:1 to a visible stamp.")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Seedance time ranges to H3 timestamps.")
    parser.add_argument("ranges", nargs="?", help='range list, e.g. "0-3s, 3-6s, 6-10s"')
    parser.add_argument("--ranges", dest="ranges_opt", help="alternative to positional argument")
    parser.add_argument("--style", choices=["table", "h3", "json"], default="table")
    parser.add_argument("--strict-base", action="store_true",
                        help="omit Shot 1 zero anchor (official base-en.txt style)")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args(argv)

    raw = args.ranges or args.ranges_opt
    if not raw:
        parser.error("provide a range list, e.g. \"0-3s, 3-6s, 6-10s\"")
    try:
        ranges = parse_ranges(raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = build_report(ranges)

    if args.json or args.style == "json":
        payload = {"input": raw, "mode": "strict-base" if args.strict_base else "zero-anchor", **report}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.style == "h3":
        print(render_h3(report, args.strict_base))
    else:
        print(render_table(report, args.strict_base))

    warnings = [i for row in report["shots"] for i in row["issues"]]
    if warnings:
        print("\nwarnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
