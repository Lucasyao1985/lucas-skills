#!/usr/bin/env python3
"""detect_mode.py - Detect the likely MiniMax H3 mode for a Seedance-style prompt.

Modes: T2VA (text only), I2VA (single first-frame image), FL2VA (first+last
keyframes), L2VA (last frame only), Ref2VA (multi-image character/scene refs or
storyboard grids).

Usage:
    python detect_mode.py input.txt
    python detect_mode.py --text "@图1 一位女性站在天台..."  --json

Exit codes: 0 ok, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PICTURE_PATTERNS = [
    r"<\s*Picture\s*(\d+)\s*>",
    r"\[\s*Picture\s*(\d+)\s*\]",
    r"@\s*Image\s*(\d+)",
    r"\bImage\s*(\d+)\s*[:：]",
    r"@\s*图\s*(\d+)",
    r"<\s*图片\s*(\d+)\s*>",
    r"\[\s*图\s*(\d+)\s*\]",
    r"@\s*picture\s*(\d+)",
]
PAIR_HINTS = ["首尾帧", "首尾两帧", "第一帧和最后一帧", "first and last frame",
              "first & last frame", "fl2va", "start and end frame"]
FIRST_HINTS = ["首帧", "第一帧", "开头一帧", "开头帧", "起始帧",
               "first frame", "starting frame", "opening frame"]
LAST_HINTS = ["尾帧", "最后一帧", "结尾一帧", "结尾帧", "末帧",
              "last frame", "ending frame", "final frame"]
L2VA_HINTS = ["仅尾帧", "只有尾帧", "尾帧参考", "以尾帧", "only the last frame",
              "last frame only", "l2va"]
GRID_KEYWORDS = [
    "storyboard", "grid", "panel", "宫格", "分镜表", "九宫格", "四宫格",
    "row 1", "character sheet", "三视图", "turnaround",
]
REF_HINTS = [
    "角色设定", "人物设定", "服装设定", "场景设定",
    "character reference", "outfit reference", "scene reference",
    "multiple images", "多张图", "两张图", "three images",
]


def _contains_any(keywords, text, low):
    return [k for k in keywords if k.lower() in low or k in text]


def detect(text: str) -> dict:
    evidence: List[str] = []
    pictures = set()
    for m in re.finditer("|".join(PICTURE_PATTERNS), text, flags=re.IGNORECASE):
        pictures.add(m.group(1))
        evidence.append(f"picture reference found: {m.group(0)}")
    n_pics = len(pictures)

    low = text.lower()
    first_hits = _contains_any(FIRST_HINTS, text, low)
    last_hits = _contains_any(LAST_HINTS, text, low)
    pair_hits = _contains_any(PAIR_HINTS, text, low)
    l_only = _contains_any(L2VA_HINTS, text, low)
    grid_hits = _contains_any(GRID_KEYWORDS, text, low)
    ref_hits = _contains_any(REF_HINTS, text, low)
    has_first, has_last = bool(first_hits), bool(last_hits)

    score = {"T2VA": 0.0, "I2VA": 0.0, "FL2VA": 0.0, "L2VA": 0.0, "Ref2VA": 0.0}

    # --- keyframe language ---
    if pair_hits or (has_first and has_last):
        score["FL2VA"] += 4.0
        evidence.append("first+last frame language -> keyframe pair")
    elif has_last:
        if l_only:
            score["L2VA"] += 4.5
            evidence.append(f"explicit last-frame-only language: {l_only}")
        else:
            score["L2VA"] += 4.0
            evidence.append(f"last-frame language: {last_hits}")
    elif has_first:
        if n_pics >= 2:
            score["FL2VA"] += 2.0
            evidence.append("first-frame language with multiple pictures")
        else:
            score["I2VA"] += 2.0
            evidence.append(f"first-frame language with a single/implicit image: {first_hits}")

    # --- explicit picture references ---
    if n_pics == 0:
        if not (has_first or has_last):
            score["T2VA"] += 3.0
            evidence.append("no picture references and no keyframe language -> text-only")
    elif n_pics == 1:
        score["I2VA"] += 2.5
        evidence.append("exactly one picture reference")
    else:
        score["FL2VA"] += 1.5
        score["Ref2VA"] += 1.5
        evidence.append(f"{n_pics} distinct picture references")

    # --- identity / storyboard signals ---
    if grid_hits:
        score["Ref2VA"] += 3.0
        evidence.append(f"storyboard/identity-sheet keywords: {grid_hits}")
    if ref_hits:
        score["Ref2VA"] += 1.5
        evidence.append(f"multi-reference hints: {ref_hits}")
    if n_pics <= 1 and (grid_hits or ref_hits):
        score["Ref2VA"] += 1.0
        evidence.append("identity/storyboard language despite few explicit picture tags")

    best_mode, best = max(score.items(), key=lambda kv: kv[1])
    second = sorted(score.values(), reverse=True)[1] if len(score) > 1 else 0.0
    confidence = round(min((best - second * 0.5) / 4.5, 1.0), 2) if best > 0 else 0.05
    ordered = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "mode": best_mode,
        "confidence": max(confidence, 0.05),
        "ranking": [{"mode": m, "score": s} for m, s in ordered],
        "picture_count": n_pics,
        "evidence": evidence,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect MiniMax H3 mode from a Seedance prompt.")
    parser.add_argument("input", nargs="?", help="path to prompt file ('-' for stdin)")
    parser.add_argument("--text", help="inline prompt text")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.text:
        text = args.text
    elif args.input == "-":
        text = sys.stdin.read()
    elif args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        parser.error("provide a file path, '-' for stdin, or --text")

    result = detect(text)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Suggested mode : {result['mode']}  (confidence {result['confidence']:.0%})")
        print(f"Picture refs   : {result['picture_count']}")
        print("Ranking        : " + ", ".join(f"{r['mode']}={r['score']:g}" for r in result["ranking"]))
        print("Evidence:")
        for ev in result["evidence"]:
            print(f"  - {ev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
