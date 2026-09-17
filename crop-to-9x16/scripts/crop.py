#!/usr/bin/env python3
"""居中裁切图片为指定宽高比，不压缩分辨率，不拉伸不变形。"""
import os
import sys
import glob
import argparse
from PIL import Image

# Windows 控制台默认 GBK 编码，emoji 输出会崩溃 — 强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SUPPORTED_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif'}


def parse_ratio(ratio_str):
    """解析宽高比字符串，如 '9:16' -> (9, 16)"""
    try:
        parts = ratio_str.split(':')
        if len(parts) != 2:
            raise ValueError
        w, h = int(parts[0]), int(parts[1])
        if w <= 0 or h <= 0:
            raise ValueError
        return w, h
    except (ValueError, IndexError):
        print(f"❌ 无效宽高比: {ratio_str}，格式应为 W:H（如 9:16、1:1）")
        sys.exit(1)


def crop_to_ratio(img, target_w, target_h):
    """居中裁切图片到目标宽高比，返回裁切后的图片（不修改原图）"""
    orig_w, orig_h = img.size
    orig_ratio = orig_w / orig_h
    target_ratio = target_w / target_h

    if abs(orig_ratio - target_ratio) < 1e-6:
        return img.copy(), 0, 0  # 已经是目标比例，无需裁切

    if orig_ratio > target_ratio:
        # 当前偏宽 → 裁左右
        new_w = int(orig_h * target_ratio)
        new_w = new_w + (new_w % 2)  # 保证偶数
        if new_w > orig_w:
            new_w = orig_w - (orig_w % 2)
        left = (orig_w - new_w) // 2
        return img.crop((left, 0, left + new_w, orig_h)), new_w - orig_w, 0
    else:
        # 当前偏高 → 裁上下
        new_h = int(orig_w / target_ratio)
        new_h = new_h + (new_h % 2)  # 保证偶数
        if new_h > orig_h:
            new_h = orig_h - (orig_h % 2)
        top = (orig_h - new_h) // 2
        return img.crop((0, top, orig_w, top + new_h)), 0, new_h - orig_h


def process_file(path, ratio_w, ratio_h, inplace=False):
    try:
        if not os.path.exists(path):
            print(f"❌ 文件不存在: {path}")
            return False

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXT:
            print(f"⚠️  跳过不支持格式: {path}")
            return False

        img = Image.open(path)
        orig_w, orig_h = img.size

        # GIF 只取第一帧
        if hasattr(img, 'n_frames') and img.n_frames > 1:
            img.seek(0)

        cropped, crop_x, crop_y = crop_to_ratio(img, ratio_w, ratio_h)
        new_w, new_h = cropped.size

        if inplace:
            out_path = path
        else:
            ratio_tag = f"{ratio_w}x{ratio_h}"
            base, ext = os.path.splitext(path)
            out_path = f"{base}_{ratio_tag}{ext}"

        # 保持原图质量参数
        save_kwargs = {}
        if ext in ('.jpg', '.jpeg'):
            save_kwargs = {'quality': 95, 'subsampling': 0, 'optimize': True}
        elif ext == '.png':
            save_kwargs = {'compress_level': 6}
        elif ext == '.webp':
            save_kwargs = {'quality': 95, 'method': 6}

        cropped.save(out_path, **save_kwargs)

        # 报告裁切信息
        if crop_x != 0:
            side = "左右" if crop_x < 0 else "左右"
            print(f"✅ 裁切完成: {out_path}  ({orig_w}×{orig_h} → {new_w}×{new_h}, 裁左右各{abs(crop_x)//2}px)")
        elif crop_y != 0:
            print(f"✅ 裁切完成: {out_path}  ({orig_w}×{orig_h} → {new_w}×{new_h}, 裁上下各{abs(crop_y)//2}px)")
        else:
            print(f"✅ 无需裁切（已是{ratio_w}:{ratio_h}）: {out_path}")
        return True

    except Exception as e:
        print(f"❌ 裁切失败 {path}: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='居中裁切图片为指定宽高比')
    parser.add_argument('--ratio', '-r', default='9:16',
                        help='目标宽高比，格式 W:H（默认 9:16）')
    parser.add_argument('--inplace', '-i', action='store_true',
                        help='覆盖原图（不加后缀）')
    parser.add_argument('files', nargs='+', help='图片文件或通配符')
    args = parser.parse_args()

    ratio_w, ratio_h = parse_ratio(args.ratio)

    total = 0
    ok = 0

    for pattern in args.files:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path):
                total += 1
                if process_file(path, ratio_w, ratio_h, args.inplace):
                    ok += 1

    print(f"\n✅ 完成: {ok}/{total} 文件裁切成功")
    print(f"✅ 目标比例: {ratio_w}:{ratio_h}")


if __name__ == "__main__":
    main()
