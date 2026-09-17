#!/usr/bin/env python3
import os
import sys
import glob
from PIL import Image

# Windows 控制台默认 GBK 编码，emoji 输出会崩溃 — 强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ✅ 高质量JPG转换参数 - 无伪色无断层
JPG_PARAMS = {
    'quality': 97,
    'subsampling': 0,  # 4:4:4 全色度采样 - 最重要参数
    'optimize': True,
    'progressive': False,
    'dpi': (96, 96)
}

SUPPORTED_EXT = {'.webp', '.png', '.gif', '.bmp', '.tiff', '.tif', '.jxl', '.avif', '.heic'}


def convert_file(path):
    try:
        if not os.path.exists(path):
            print(f"❌ 文件不存在: {path}")
            return False

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXT:
            print(f"⚠️  跳过不支持格式: {path}")
            return False

        out_path = os.path.splitext(path)[0] + '.jpg'

        img = Image.open(path)
        if img.mode in ('RGBA', 'LA', 'P'):
            # 正确处理透明通道 - 白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        else:
            img = img.convert('RGB')

        img.save(out_path, 'JPEG', **JPG_PARAMS)
        print(f"✅ 转换完成: {out_path}")
        return True

    except Exception as e:
        print(f"❌ 转换失败 {path}: {str(e)}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python convert.py <文件|通配符>")
        print("支持格式: WEBP PNG GIF BMP TIFF JXL AVIF HEIC")
        sys.exit(1)

    total = 0
    ok = 0

    for pattern in sys.argv[1:]:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path):
                total += 1
                if convert_file(path):
                    ok += 1

    print(f"\n✅ 完成: {ok}/{total} 文件转换成功")
    print("✅ 参数: quality=97, 4:4:4 全色度采样, 无伪色无断层")


if __name__ == "__main__":
    main()
