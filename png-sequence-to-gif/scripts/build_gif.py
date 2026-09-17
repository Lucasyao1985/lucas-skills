"""
png-sequence-to-gif: build a looping animated GIF from a numbered PNG sequence.

Usage:
    python scripts/build_gif.py <input.zip-or-dir> <output.gif> [--duration 100] [--bg white|none]

Behavior:
  - Sorts frames by the trailing number in the filename (emoji_1.png..emoji_16.png),
    so emoji_10 sorts after emoji_9 (string sort would put it after emoji_1).
  - Detects whether the source actually has transparency; if alpha is solid 255,
    only emits a single GIF (the "transparent" and "white-bg" outputs would be
    byte-identical, so don't waste space on duplicates).
  - Preserves transparency when present by quantizing with FASTOCTREE and mapping
    fully-transparent pixels to palette index 255 with disposal=2.

This script is a library: it exposes `build(input_path, output_path, duration_ms, bg)`
so it can be imported and reused, and it also runs as a CLI when invoked directly.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageSequence

FRAME_RE = re.compile(r"(\d+)(?!.*\d)")  # last run of digits in the stem


def _list_frames(input_path: str) -> list[Path]:
    """Return frame paths sorted by the trailing number in the filename."""
    p = Path(input_path)
    if p.is_file() and p.suffix.lower() == ".zip":
        # Extract to a sibling temp dir next to the zip, named after the zip stem.
        extract_dir = p.with_suffix("")  # e.g. emojis -> emojis
        if extract_dir.exists():
            # Reuse existing extraction; PNGs in there are what we want.
            candidates = list(extract_dir.glob("*.png"))
        else:
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(p) as z:
                z.extractall(extract_dir)
            candidates = list(extract_dir.glob("*.png"))
    else:
        candidates = list(p.glob("*.png"))

    if not candidates:
        raise SystemExit(f"No PNG files found under {input_path!r}")

    def sort_key(fp: Path) -> int:
        m = FRAME_RE.search(fp.stem)
        return int(m.group(1)) if m else 0

    return sorted(candidates, key=sort_key)


def _has_real_transparency(frames: Iterable[Path]) -> bool:
    """Return True iff at least one source frame has pixels with alpha < 250."""
    for fp in frames:
        im = Image.open(fp)
        if im.mode != "RGBA":
            continue
        a = np.array(im.getchannel("A"))
        if (a < 250).any():
            return True
    return False


def _to_frame(im_rgba: Image.Image, transparent: bool) -> Image.Image:
    """Quantize one frame to a palette PNG with optional transparency index 255."""
    alpha = np.array(im_rgba.getchannel("A"))
    q = im_rgba.quantize(colors=255, method=Image.FASTOCTREE)
    arr = np.array(q)
    if transparent:
        arr[alpha < 32] = 255
    out = Image.fromarray(arr, "P")
    pal = q.getpalette() + [0, 0, 0]
    out.putpalette(pal)
    if transparent:
        out.info["transparency"] = 255
    return out


def build(input_path: str, output_path: str, duration_ms: int = 100,
          bg: str | None = None) -> dict:
    """
    Build the GIF.

    Args:
        input_path: path to a .zip of PNGs, or a directory containing PNGs.
        output_path: where to write the resulting .gif.
        duration_ms: per-frame delay in milliseconds.
        bg: None (keep transparency if present), "white" (flatten onto white),
            or an (R,G,B,A) tuple for a custom background.

    Returns a dict with stats: frames, width, height, has_transparency, output.
    """
    frames_src = _list_frames(input_path)
    has_transparency = _has_real_transparency(frames_src)

    flat_bg = None
    if bg == "white":
        flat_bg = (255, 255, 255, 255)
    elif isinstance(bg, (tuple, list)) and len(bg) in (3, 4):
        flat_bg = tuple(bg) + (255,) * (4 - len(bg))

    # Decide transparency for the output:
    #   - If user forced a bg, flatten (no transparency).
    #   - Else if source has real transparency, preserve it.
    #   - Else: just use the source as-is (already opaque).
    preserve_transparency = (flat_bg is None) and has_transparency

    out_frames: list[Image.Image] = []
    for fp in frames_src:
        im = Image.open(fp).convert("RGBA")
        if flat_bg is not None:
            base = Image.new("RGBA", im.size, flat_bg)
            base.alpha_composite(im)
            im = base
        out_frames.append(_to_frame(im, transparent=preserve_transparency))

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_frames[0].save(
        out_path,
        save_all=True,
        append_images=out_frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )

    return {
        "frames": len(out_frames),
        "width": out_frames[0].width,
        "height": out_frames[0].height,
        "has_transparency": preserve_transparency,
        "output": str(out_path),
    }


def _verify(path: str) -> None:
    im = Image.open(path)
    n = sum(1 for _ in ImageSequence.Iterator(im))
    print(
        f"verified: {path} | size={im.size} | frames={n} | "
        f"duration={im.info.get('duration')}ms | loop={im.info.get('loop')}"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("input", help=".zip file or directory of numbered PNG frames")
    ap.add_argument("output", help="path to write the resulting .gif")
    ap.add_argument("--duration", type=int, default=100,
                    help="per-frame delay in ms (default: 100)")
    ap.add_argument("--bg", default="auto",
                    help='"white" to flatten onto white, "none" to force no bg, '
                         'or "auto" to detect from source alpha (default: auto)')
    args = ap.parse_args(argv)

    bg: str | None
    if args.bg == "auto":
        bg = None
    elif args.bg.lower() in ("none", "no", "transparent"):
        bg = None
    else:
        bg = args.bg  # "white" or a custom tuple via future extension

    stats = build(args.input, args.output, duration_ms=args.duration, bg=bg)
    print(stats)
    _verify(stats["output"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
