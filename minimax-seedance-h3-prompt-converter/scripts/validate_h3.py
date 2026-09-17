#!/usr/bin/env python3
"""validate_h3.py - Validate a MiniMax H3 prompt produced from a Seedance conversion.

Eight gates (see references/quality-checklist.md):
  1 structure completeness      2 first-line alignment instruction
  3 duplicate identity blocks   4 picture-identity leak guard
  5 timeline sanity             6 sound fields present
  7 Seedance residue            8 dialogue/speaker formatting

Usage:
    python validate_h3.py prompt.txt --mode auto --duration 10
    python validate_h3.py prompt.txt --mode i2va --json
    cat prompt.txt | python validate_h3.py -

Modes: t2va i2va fl2va l2va ref2va auto
Exit codes: 0 = pass (warnings allowed), 1 = validation errors found, 2 = usage error.
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

# --------------------------------------------------------------------------- #
# Lexicons
# --------------------------------------------------------------------------- #

APPEARANCE_LEXICON = [
    # face shape / features
    r"v[- ]line face", r"oval face", r"round face", r"square jaw", r"delicate jaw",
    r"large bright eyes", r"small nose", r"glossy lips", r"double eyelid",
    r"high cheekbones", r"dimple[sd]?",
    # hair
    r"long straight black hair", r"straight black hair", r"black hair",
    r"brown hair", r"blonde hair", r"blond hair", r"silver hair", r"pink hair",
    r"curly hair", r"wavy hair", r"ponytail", r"bob cut", r"twin tails?", r"bangs",
    r"hair color", r"hair colour",
    # skin
    r"fair skin", r"pale skin", r"porcelain skin", r"tanned skin", r"freckles?",
    r"visible pores",
    # body proportions
    r"slender figure", r"slim figure", r"curvy body", r"petite build",
    r"tall and slim", r"body proportions",
]
APPEARANCE_RE = re.compile("|".join(APPEARANCE_LEXICON), flags=re.IGNORECASE)

CLOTHING_LEXICON = [
    r"wearing an? [a-z][a-z\- ]*(?:dress|qipao|cheongsam|kimono|hoodie|suit|uniform|blouse|skirt|gown)",
    r"ivory mandarin-collar", r"charcoal wide-leg trousers", r"silk qipao",
]
CLOTHING_RE = re.compile("|".join(CLOTHING_LEXICON), flags=re.IGNORECASE)

WHITELIST_CONTEXT = re.compile(
    r"(shown in|from|taken solely from|established by|preserv\w+|defined by|based on)"
    r"[^.]{0,120}$",
    flags=re.IGNORECASE,
)

RESIDUE_PATTERNS = [
    (r"\b\d{1,2}\s*[-–—~～]\s*\d{1,2}(?:[:：]\d{1,2})?(?:\.\d{1,3})?\s*s\b",
     "Seedance range notation like '0-3s'"),
    (r"\(\s*\d{1,2}[:：]\d{2}(?:\.\d+)?\s*[-–—~～]\s*\d{1,2}[:：]\d{2}(?:\.\d+)?\s*\)",
     "Seedance range notation like '(0:00-0:01.8)'"),
    (r"@\s*图\s*\d+", "Chinese image reference '@图N'"),
    (r"<\s*图片\s*\d+\s*>", "Chinese image tag '<图片N>'"),
    (r"@\s*Image\s*\d+", "'@Image N' reference (convert to '<Picture N>' or Subject)"),
    (r"(?:主体|场景|动作|镜头语言|运镜|光线|氛围|音效|背景音乐|BGM|台词|时长)\s*[:：]",
     "Chinese field label from the Seedance template"),
    (r"\b(?:storyboard grid|\d+[- ]panel\b|宫格)", "storyboard-grid layout instruction"),
]

SECTION_BASE = ["integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:"]
SECTION_REF2VA = ["subject_definitions:", "summary:", "retention_analysis:",
                  "detailed_description:", "overall_soundscape:", "non_diegetic_music:"]

ALIGN_I2VA = re.compile(
    r"^For the target video, at 0\.00 seconds into the target video, "
    r"<Picture \d+> \(from \[Shot \d+\]\) is fully referenced\.\s*$"
)
ALIGN_FL2VA = re.compile(
    r"^How the reference pictures align with the target video\b.*"
    r"aligns with the 0\.00-second mark of the target video;.*"
    r"aligns with the \d+\.\d\d-second mark of the target video\.\s*$"
)
ALIGN_L2VA = re.compile(
    r"^How the reference pictures align with the target video\b.*"
    r"<Picture \d+> \(from \[Shot \d+\]\) aligns with the \d+\.\d\d-second mark "
    r"of the target video\.\s*$"
)

STAMP_RE = re.compile(r"At (\d{2}):(\d{2}\.\d{3})")
SHOT_HEAD_RE = re.compile(r"\[Shot (\d+)\]")
DIALOGUE_RE = re.compile(r"<d>\[([^\]]+)\](.*?)</d>", flags=re.DOTALL)
SPEAKER_RE = re.compile(r"\(S\d+(?:,\s*S\d+)*\)")

BASE_MODES = {"t2va", "i2va", "fl2va", "l2va"}


def _err(errors, warnings, gate, msg, where=None):
    """Record a validation ERROR."""
    item = {"gate": gate, "message": msg}
    if where:
        item["where"] = where
    errors.append(item)


def _warn(warnings, gate, msg, where=None):
    item = {"gate": gate, "message": msg}
    if where:
        item["where"] = where
    warnings.append(item)


def detect_mode(text: str) -> str:
    n_pics = len(set(re.findall(r"<\s*Picture\s*(\d+)\s*>", text, re.I)))
    low = text.lower()
    if "subject_definitions:" in low:
        return "ref2va"
    if any(k in low for k in ("首尾帧", "first frame", "last frame")) and n_pics >= 1:
        return "fl2va" if n_pics >= 1 else "t2va"
    if n_pics == 0:
        return "t2va"
    return "i2va"


def gate_structure(text: str, mode: str, errors, warnings):
    required = SECTION_REF2VA if mode == "ref2va" else SECTION_BASE
    positions = []
    for sec in required:
        idx = text.find(sec)
        positions.append(idx)
        if idx == -1:
            _err(errors, warnings, "structure", f"missing required section '{sec}'")
    found = [p for p in positions if p != -1]
    if len(found) > 1 and found != sorted(found):
        _err(errors, warnings, "structure",
             f"sections out of order; expected order: {' -> '.join(required)}")
    if mode == "ref2va":
        if "integrated_multimodal_description:" in text:
            _warn(warnings, "structure",
                  "ref2va uses 'detailed_description:'; found base-mode field "
                  "'integrated_multimodal_description:'")


def gate_alignment(text: str, mode: str, errors, warnings):
    first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if mode == "i2va":
        if not ALIGN_I2VA.match(first_line):
            _err(errors, warnings, "alignment",
                 "I2VA first line must be exactly: For the target video, at 0.00 seconds "
                 "into the target video, <Picture N> (from [Shot N]) is fully referenced.")
    elif mode == "fl2va":
        if not ALIGN_FL2VA.match(first_line):
            _err(errors, warnings, "alignment",
                 "FL2VA first line must follow 'How the reference pictures align ...' "
                 "with a 0.00-second clause and an S.SS-second clause.")
    elif mode == "l2va":
        if not ALIGN_L2VA.match(first_line):
            _err(errors, warnings, "alignment",
                 "L2VA first line must follow 'How the reference pictures align ...' "
                 "with '<Picture N> (from [Shot N])' and an S.SS-second clause.")
    elif mode == "t2va" and ("is fully referenced" in first_line or "aligns with" in first_line):
        _err(errors, warnings, "alignment", "T2VA must not carry an alignment instruction line.")
    elif mode == "ref2va" and ("is fully referenced." in first_line and "target video" in first_line):
        _warn(warnings, "alignment",
              "Ref2VA normally starts with subject_definitions:, not an alignment line.")
    if mode in ("i2va", "fl2va", "l2va"):
        rest = "\n".join(text.strip().splitlines()[1:]).lstrip()
        if rest and not re.match(r"(integrated_multimodal_description:|detailed_description:)", rest):
            _warn(warnings, "alignment",
                  "expected one blank line then the first core field after the alignment line.")


def gate_identity(text: str, mode: str, errors, warnings):
    pics = re.findall(r"<\s*Picture\s*\d+\s*>", text)
    # raw Seedance markers also activate the guard (they must have been
    # converted to <Picture N> already; residue is reported separately)
    raw_refs = re.findall(r"@\s*(?:图|Image|picture)\s*\d+", text, flags=re.IGNORECASE)
    has_pic_ref = bool(pics) or bool(raw_refs)
    main_field = "detailed_description:" if mode == "ref2va" else "integrated_multimodal_description:"
    start = text.find(main_field)
    body = text[start:] if start != -1 else text

    if has_pic_ref:
        if mode == "ref2va":
            # full-reference mode delegates identity via <Subject N> labels
            delegation_hits = len(re.findall(r"<\s*Subject\s*\d+\s*>", body))
        else:
            delegation_hits = len(re.findall(
                r"(?:shown in|defined by)\s*<\s*Picture", body, re.I))
        if delegation_hits == 0:
            _warn(warnings, "identity",
                  "picture reference present but no standard identity delegation "
                  "('... shown in <Picture N>' or '<Subject N>' labels in ref2va) "
                  "found in the description body.")
        for m in APPEARANCE_RE.finditer(body):
            ctx = body[max(0, m.start() - 130):m.end()]
            if WHITELIST_CONTEXT.search(ctx):
                continue
            _warn(warnings, "identity",
                  f"possible appearance description while a picture reference exists: "
                  f"'{m.group(0)}'", where=ctx.strip()[-160:])
        for m in CLOTHING_RE.finditer(body):
            ctx = body[max(0, m.start() - 130):m.end()]
            if WHITELIST_CONTEXT.search(ctx):
                continue
            _warn(warnings, "identity",
                  f"possible fixed-outfit description while a picture reference exists "
                  f"(allowed only as the flagged sole outfit change): '{m.group(0)}'",
                  where=ctx.strip()[-160:])
        dup = len(re.findall(r"whose exact face[^.]*taken solely from <\s*Picture", body, re.I))
        if dup > 1:
            _err(errors, warnings, "identity",
                 f"full identity-delegation sentence repeated {dup} times; delegate once, "
                 f"then refer back with 'the same woman/man/character'.")
    else:
        if mode == "ref2va":
            _warn(warnings, "identity",
                  "no '<Picture N>' labels found although mode is ref2va; check subject_definitions.")


def gate_timeline(text: str, mode: str, duration: float | None, errors, warnings):
    main_field = "detailed_description:" if mode == "ref2va" else "integrated_multimodal_description:"
    start = text.find(main_field)
    end_sound = text.find("overall_soundscape:")
    body = text[start:end_sound if end_sound != -1 else len(text)] if start != -1 else text

    shots = [(int(m.group(1)), m.start()) for m in SHOT_HEAD_RE.finditer(body)]
    if not shots:
        _err(errors, warnings, "timeline", "no '[Shot N]' markers found in the description body.")
        return
    nums = [n for n, _ in shots]
    if nums != list(range(1, len(nums) + 1)):
        _err(errors, warnings, "timeline",
             f"shot numbers must be contiguous starting at 1; found {nums}")

    stamps: List[tuple] = []
    for pos, (n, s_pos) in enumerate(shots):
        seg_end = shots[pos + 1][1] if pos + 1 < len(shots) else len(body)
        seg = body[s_pos:seg_end]
        found = STAMP_RE.findall(seg)
        if n == 1:
            continue  # zero-anchor optional in shot 1
        if not found:
            _err(errors, warnings, "timeline", f"[Shot {n}] is missing its 'At MM:SS.mmm' cut point.")
        else:
            mm, ssms = found[0]
            stamps.append((n, int(mm) * 60 + float(ssms)))
    prev_name, prev_val = 1, 0.0
    for n, val in stamps:
        if val <= prev_val:
            _err(errors, warnings, "timeline",
                 f"cut points must be strictly increasing: [Shot {prev_name}] {prev_val:.3f}s >= "
                 f"[Shot {n}] {val:.3f}s")
        elif duration is not None and val > duration + 0.0005:
            _err(errors, warnings, "timeline",
                 f"[Shot {n}] cut point {val:.3f}s exceeds duration {duration}s")
        prev_name, prev_val = n, val
    if duration is not None:
        fade = re.search(r"by (\d{2}):(\d{2}\.\d{3})", body)
        if fade:
            total = int(fade.group(1)) * 60 + float(fade.group(2))
            if abs(total - duration) > 0.05:
                _warn(warnings, "timeline",
                      f"closing fade lands at {total:.3f}s but declared duration is {duration}s")


def gate_sounds(text: str, errors, warnings):
    for field in ("overall_soundscape:", "non_diegetic_music:"):
        idx = text.find(field)
        if idx == -1:
            continue  # already reported by structure gate
        after = text[idx + len(field):]
        nxt = min([p for p in (after.find("\nintegrated_multimodal_description"),
                               after.find("\ndetailed_description"),
                               after.find("\nsubject_definitions")) if p != -1],
                  default=len(after))
        content = after[:nxt].strip()
        if not content:
            _err(errors, warnings, "sounds", f"'{field}' has no content (use 'N/A' only for requested silence).")
        elif content.lower() == "n/a":
            continue
        elif len(content) < 8:
            _err(errors, warnings, "sounds", f"'{field}' content looks truncated: '{content}'")


def gate_residue(text: str, errors, warnings):
    for pattern, label in RESIDUE_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            _err(errors, warnings, "residue", f"{label}: '{m.group(0)}'")


def gate_dialogue(text: str, mode: str, errors, warnings):
    opens = len(re.findall(r"<d>", text))
    closes = len(re.findall(r"</d>", text))
    if opens != closes:
        _err(errors, warnings, "dialogue", f"unbalanced <d> tags: {opens} opened vs {closes} closed")
    for m in DIALOGUE_RE.finditer(text):
        lang, payload = m.group(1).strip(), m.group(2)
        if not lang:
            _err(errors, warnings, "dialogue", "dialogue missing language tag: <d>[Language] ...</d>")
        if not payload.strip():
            _err(errors, warnings, "dialogue", "empty dialogue block")
    speakers = SPEAKER_RE.findall(text)
    if DIALOGUE_RE.search(text) and not speakers:
        _err(errors, warnings, "dialogue",
              "dialogue present but no stable speaker IDs '(S1)' found")
    for m in re.finditer(r"\([Ss]\d+[^)]*\)", text):
        token = m.group(0)
        if not SPEAKER_RE.fullmatch(token):
            _warn(warnings, "dialogue", f"malformed speaker ID: '{token}'")


def _body_of(text: str, mode: str) -> str:
    """Return the description-body slice (alignment line and sound fields excluded)."""
    main_field = "detailed_description:" if mode == "ref2va" else "integrated_multimodal_description:"
    start = text.find(main_field)
    end = text.find("overall_soundscape:")
    return text[start:end if end != -1 else len(text)] if start != -1 else text


def validate(text: str, mode: str | None, duration: float | None) -> dict:
    errors, warnings = [], []
    resolved = (mode or "auto").lower()
    if resolved == "auto":
        resolved = detect_mode(text)

    gate_structure(text, resolved, errors, warnings)
    gate_alignment(text, resolved, errors, warnings)
    gate_identity(text, resolved, errors, warnings)
    gate_timeline(text, resolved, duration, errors, warnings)
    gate_sounds(text, errors, warnings)
    gate_residue(text, errors, warnings)
    gate_dialogue(text, resolved, errors, warnings)

    return {
        "valid": not errors,
        "mode": resolved,
        "mode_source": mode or "auto-detected",
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "_note": "shots counted inside the description body only",
            "shots": len(SHOT_HEAD_RE.findall(_body_of(text, resolved))),
            "dialogue_blocks": len(DIALOGUE_RE.findall(text)),
            "speakers": len(set(re.findall(r"\((S\d+)\)", text))),
            "picture_labels": sorted(set(re.findall(r"<\s*(Picture \d+)\s*>", text))),
            "words": len(re.findall(r"\w+", text)),
        },
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an H3 prompt converted from Seedance.")
    parser.add_argument("input", help="prompt file path ('-' for stdin)")
    parser.add_argument("--mode", choices=["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va"],
                        default="auto")
    parser.add_argument("--duration", type=float, default=None,
                        help="declared total duration in seconds")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args(argv)

    if args.input == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.input)
        if not path.exists():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")

    report = validate(text, args.mode, args.duration)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if report["valid"] else "FAIL"
        print(f"H3 validation [{status}]  mode={report['mode']} ({report['mode_source']})")
        print(f"shots={report['stats']['shots']}  dialogue={report['stats']['dialogue_blocks']}  "
              f"speakers={report['stats']['speakers']}  pictures={report['stats']['picture_labels']}")
        if report["errors"]:
            print(f"\nERRORS ({len(report['errors'])}):")
            for e in report["errors"]:
                print(f"  [{e['gate']}] {e['message']}")
                if "where" in e:
                    print(f"      context: ...{e['where']}")
        if report["warnings"]:
            print(f"\nWARNINGS ({len(report['warnings'])}):")
            for w in report["warnings"]:
                print(f"  [{w['gate']}] {w['message']}")
                if "where" in w:
                    print(f"      context: ...{w['where']}")
        if not report["errors"] and not report["warnings"]:
            print("\nAll eight gates clean.")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
