---
name: png-sequence-to-gif
description: >
  Convert a numbered PNG sequence (e.g. emoji_1.png..emoji_16.png) inside a
  .zip or folder into a single looping animated GIF, preserving transparency
  when the source frames actually have an alpha channel. Use when the user
  provides a zip of emoji/sticker frames and asks to "make a GIF", "合成动图",
  "把这些png做成gif", "生成表情包", or "把帧合成gif"; when a folder of
  numbered PNGs needs to become a loop; or when the user wants to package
  raw frames into a shareable .gif file.
metadata:
  author: Lucas
  version: 1.0.0
compatibility: 需要 Python 3.10+ 与 Pillow（`pip install Pillow numpy`）。
  GIF 输出由脚本本地生成，不依赖外部服务。
---

# PNG Sequence → Animated GIF

Take a batch of numbered PNG frames (typical pattern: `emoji_1.png`,
`emoji_2.png`, …, `emoji_16.png`) — either inside a `.zip` or already
unpacked in a folder — and produce **one looping animated GIF** that keeps
transparency when the source actually has it.

## When to use this skill

- The user gives you a zip that **looks** like an animation (numbered PNGs
  in it) and says "make a GIF" / "合成动图" / "做成表情包" / "把帧合成 gif".
- The user has a folder of numbered PNG frames and wants a single looping
  GIF.
- The user pastes a **sprite sheet** (a single image containing a grid
  of animation frames, often JPG without alpha) and wants the frames
  extracted and assembled into a GIF.
- A previous conversation produced a PNG sequence and now needs to be
  delivered as a GIF.

Do **not** use this skill when the user already has a `.gif`/`.webp`/`.mp4`
they want edited (use a video/GIF editor instead), or when frames aren't
numbered and don't sit on a regular grid (renumber or ask the user).

## Workflow

### Step 0: (sprite sheets only) Split the grid into frames

If the source is a single image with multiple poses/frames on a regular
grid (very common for "表情包" sprite sheets posted as JPG or PNG), split
it into a numbered PNG sequence first. Use the bundled helper:

```bash
python scripts/split_sprite.py "<sheet.jpg>" "<work>/frames" --rows 4 --cols 4
```

This produces:
- `<work>/frames/cell_01.png` … `cell_NN.png` — plain RGB (preserves
  the source's background, usually white).
- `<work>/frames/keyed/cell_01.png` … `cell_NN.png` — RGBA with a clean
  alpha mask so the background is truly transparent.

The alpha mask is built from edge density on a 32-px tile grid plus a
"near-pure-white" cleanup pass, so it survives JPG compression noise.
After this step, continue from Step 3 with the appropriate subdir as
the input. Skip this step entirely for zip / folder inputs.

### Step 1: Inspect the source

Before doing anything, look at what is actually inside the archive or folder.
Do not assume the zip contains a GIF — most "emoji pack" zips are PNG
sequences.

```bash
python -c "
import zipfile, sys
z = zipfile.ZipFile(sys.argv[1])
for i in z.infolist():
    print(i.filename, i.file_size)
" "<input.zip>"
```

Confirm:
- The frames are PNGs (extension `.png`).
- They follow a numbered naming pattern (`<name>_<n>.png`).
- Count the frames (typical 8 / 12 / 16 / 24).

If the user pointed at a folder, list it: `ls <folder>/*.png | sort -V`.

### Step 2: Set up Python + Pillow (one-time per environment)

Pillow must be available in the Python that will run the script. Use a
managed venv so the system Python is not polluted:

```bash
PY="C:/Users/Lucas/.workbuddy-ai/binaries/python/versions/3.13.12/python.exe"
ENV="C:/Users/Lucas/.workbuddy-ai/binaries/python/envs/default"
[ ! -f "$ENV/Scripts/python.exe" ] && "$PY" -m venv "$ENV"
"$ENV/Scripts/python.exe" -m pip install -q Pillow numpy
```

If the user is on a different machine, replace the paths with their own
`python -m venv .venv && source .venv/bin/activate && pip install Pillow numpy`.

### Step 3: Run the build script

The bundled script is at `scripts/build_gif.py`. It accepts either a `.zip`
or a directory, sorts frames by their trailing number, and decides whether
to keep transparency based on the source alpha channel.

```bash
"<venv>/Scripts/python.exe" scripts/build_gif.py \
    "<input.zip-or-dir>" \
    "<output>.gif" \
    --duration 100
```

Parameters:
- `--duration` — per-frame delay in ms. `100` ≈ 10 fps (default, good for
  most sticker/emoji loops). Use `60` for snappier loops, `150` for slower.
- `--bg` — optional background to flatten onto:
  - `auto` (default): keep transparency if any frame actually has it,
    otherwise emit a single opaque GIF.
  - `white`: always flatten onto white (no transparency).
  - `none`: force opaque (skip transparency even if the source has it).

The script prints a stats dict and a one-line verification (size, frame
count, duration, loop).

### Step 4: Verify the output

The script auto-verifies with `ImageSequence.Iterator`, but spot-check
visually by opening the file in a preview tool, or via:

```bash
python -c "
from PIL import Image, ImageSequence
im = Image.open('<output>.gif')
print('frames', sum(1 for _ in ImageSequence.Iterator(im)))
print('size', im.size, 'duration', im.info.get('duration'), 'loop', im.info.get('loop'))
"
```

A correct output has `loop == 0` (infinite loop), `disposal == 2`
(frames don't smear into each other), and the expected frame count.

### Step 5: Deliver

Use `present_files` to show the GIF inline and let the user download it.
Mention the final filename, dimensions, frame count, and per-frame delay.

## Bundled script

| File | Purpose |
| --- | --- |
| `scripts/build_gif.py` | Library + CLI. `build(input, output, duration_ms, bg)` is importable. The CLI entry point parses `--duration` and `--bg`. |
| `scripts/split_sprite.py` | Library + CLI. `mask_for_cell(rgb_array)` is importable. CLI: `python scripts/split_sprite.py <sheet> <out-dir> --rows 4 --cols 4 [--no-key]`. Splits a sprite sheet into a numbered PNG sequence and, unless `--no-key` is passed, also writes a transparent-keyed variant. |

## Troubleshooting

**GIF is bigger than expected / colors look muddy.**
The source frames probably have full alpha (no real transparency) but many
subtle color variations. The script already limits each frame to 255 colors
plus index 255 for transparent; if you need a smaller file, downscale the
frames first (`Pillow.Image.thumbnail`) or accept some loss by re-encoding
with fewer colors (`colors=128`).

**Frame order is wrong (emoji_10 appears before emoji_2).**
You sorted as strings. The script uses a regex on the trailing digits, so
`emoji_2.png` and `emoji_10.png` sort correctly. If you re-implement this
elsewhere, do not use plain `sorted()` on the filenames.

**Transparent area is black or has a halo in the GIF.**
`quantize(..., method=MEDIANCUT)` on RGBA raises an error; you must use
`method=Image.FASTOCTREE`. Also, the source PNGs need a real alpha channel
— if the source's alpha is all 255, there is no transparency to preserve
(check with `(np.array(im.getchannel('A')) < 250).any()`).

**Output flickers between frames.**
You set `disposal=0` (the default) instead of `disposal=2`. Use
`disposal=2` so each frame replaces the previous one cleanly.

**Transparent GIF has black/white speckle in the background.**
The source was a JPG (or any RGB image without alpha) that *looked* white
in the background but actually has compression noise. A naive
`white-pixel → transparent` key produces speckle. Use the sprite-sheet
helper to regenerate frames with a proper edge-density mask:
`python scripts/split_sprite.py <sheet> <work>`. The `<work>/keyed/`
output will have a clean alpha. If the source is already a folder of
RGB PNGs, you can post-process them with the helper's `mask_for_cell`
function (importable from `scripts/split_sprite.py`).

**Two outputs are byte-identical.**
The source frames are fully opaque, so the "transparent" and "white-bg"
versions of the same frames are visually identical. Emit only one file —
don't waste space on duplicates. (The bundled script does this
automatically.)

## Example

User: `@"<emojis.zip>" 做成 GIF，放在 <outdir>/emoji.gif`

```bash
"$ENV/Scripts/python.exe" "$SKILL_DIR/scripts/build_gif.py" \
    "<emojis.zip>" "<outdir>/emoji.gif"
# -> {frames: 16, width: 314, height: 314, has_transparency: True, output: ...}
# verified: <outdir>/emoji.gif | size=(314, 314) | frames=16 | duration=100ms | loop=0
```

Then `present_files` with the output path.
