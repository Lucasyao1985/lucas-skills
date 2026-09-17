"""Split a sprite-sheet image (JPG/PNG) into a numbered sequence of frames
and write them as PNGs into an output directory.

Usage:
    python scripts/split_sprite.py <input.jpg-or-png> <output-dir> \
        [--rows 4] [--cols 4]

Each cell is written as `<output-dir>/cell_NN.png` (NN = 01, 02, ...).
The script also generates a transparent-keyed version when the source is
opaque (e.g. a JPG with a white background), using an edge-density mask
plus connected-region cleanup. Keyed cells go to
`<output-dir>/keyed/cell_NN.png`.

After running, feed `<output-dir>` (or `<output-dir>/keyed`) into
`build_gif.py` to produce the animated GIF.
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageFilter


def mask_for_cell(cell_rgb: np.ndarray) -> np.ndarray:
    """Build a clean alpha mask for one sprite cell.

    Strategy: detect "character" regions via edge density on a 32-px tile
    grid (tolerates JPG compression noise in the supposedly-white
    background), then exclude pixels that are still very close to pure
    white. A 2-px Gaussian blur softens the resulting edge.
    """
    pil = Image.fromarray(cell_rgb, 'RGB').filter(ImageFilter.FIND_EDGES)
    edges = np.array(pil.convert('L'))
    h, w = edges.shape
    tile = 32
    gh, gw = h // tile, w // tile
    grid = np.zeros((gh, gw), dtype=bool)
    ebin = edges > 24
    for ty in range(gh):
        for tx in range(gw):
            block = ebin[ty * tile:(ty + 1) * tile, tx * tile:(tx + 1) * tile]
            grid[ty, tx] = block.any()

    pad = np.pad(grid, 1, constant_values=False)
    dil = (
        pad[0:-2, 0:-2] | pad[0:-2, 1:-1] | pad[0:-2, 2:] |
        pad[1:-1, 0:-2] |                       pad[1:-1, 2:] |
        pad[2:,   0:-2] | pad[2:,   1:-1] | pad[2:,   2:]
    )
    char_mask = Image.fromarray(dil.astype(np.uint8) * 255, 'L')\
        .resize((w, h), Image.NEAREST)
    char_mask = np.array(char_mask) > 127

    very_white = cell_rgb.min(axis=-1) > 250
    final = char_mask & (~very_white)

    soft = Image.fromarray((final.astype(np.uint8) * 255), 'L')\
        .filter(ImageFilter.GaussianBlur(2))
    return np.array(soft)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', help='path to the sprite sheet image (jpg/png)')
    p.add_argument('output', help='output directory; will be created')
    p.add_argument('--rows', type=int, default=4)
    p.add_argument('--cols', type=int, default=4)
    p.add_argument('--prefix', default='cell',
                   help='cell filename prefix (default: cell)')
    p.add_argument('--no-key', action='store_true',
                   help='skip generating a transparent-keyed variant')
    args = p.parse_args()

    os.makedirs(args.output, exist_ok=True)
    if not args.no_key:
        os.makedirs(os.path.join(args.output, 'keyed'), exist_ok=True)

    im = Image.open(args.input).convert('RGB')
    W, H = im.size
    cw, ch = W // args.cols, H // args.rows
    print(f'source {W}x{H}, cells {cw}x{ch} ({args.rows}x{args.cols} grid)')

    arr = np.array(im)
    idx = 0
    for r in range(args.rows):
        for c in range(args.cols):
            idx += 1
            x0, y0 = c * cw, r * ch
            x1, y1 = x0 + cw, y0 + ch
            cell = arr[y0:y1, x0:x1]
            name = f'{args.prefix}_{idx:02d}.png'
            Image.fromarray(cell, 'RGB').save(os.path.join(args.output, name))
            if not args.no_key:
                alpha = mask_for_cell(cell)
                rgba = np.dstack([cell, alpha])
                Image.fromarray(rgba, 'RGBA').save(
                    os.path.join(args.output, 'keyed', name))
    print(f'wrote {idx} cells to {args.output}')


if __name__ == '__main__':
    main()
