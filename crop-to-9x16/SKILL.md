---
name: crop-to-9x16
description: 裁剪图片为指定宽高比（默认9:16），居中裁切，不压缩分辨率。支持任意宽高比：9:16 1:1 4:3 16:9 3:4 2:3 等。Use when user says "裁成9:16"、"改成9比16"、"裁切为竖屏"、"去掉两边"、"裁成正方形"、"裁成1:1"、"改宽高比"、"crop to 9:16"，或提供图片要求裁切为特定比例。输出带比例后缀（如 _9x16.jpg），不覆盖原图。
metadata:
  author: Lucas
  version: 1.0.0
user-invocable: true
compatibility: 需要系统 Python（D:\Conda\python.exe）与 Pillow 10+（`python -c "import PIL"` 验证）。Windows 环境已验证。
---

# /crop-to-9x16 - 图片宽高比裁剪

将图片居中裁切为指定宽高比，不压缩分辨率，不拉伸不变形。

## 核心规则（Critical）

1. **必须使用 `scripts/crop.py` 执行裁切**——不要自行拼 ffmpeg 或其他命令
2. 输出与输入同目录，文件名加比例后缀（`photo.jpg` → `photo_9x16.jpg`）
3. 居中裁切：从两侧（或上下）等距裁掉多余像素，保留原始分辨率
4. 用系统 Python 运行（`D:\Conda\python.exe` 有 Pillow；其他解释器可能没有）

## 支持的宽高比

| 参数 | 比例 | 说明 |
|---|---|---|
| `9:16` | 0.5625 | 竖屏短视频（默认） |
| `1:1` | 1.0 | 正方形 |
| `4:3` | 1.333 | 传统横屏 |
| `16:9` | 1.778 | 宽屏 |
| `3:4` | 0.75 | 竖屏照片 |
| `2:3` | 0.667 | 竖屏人像 |
| `3:2` | 1.5 | 横屏照片 |
| 自定义 | 任意 | 直接输入如 `5:4` |

## Instructions

### Step 1: 确认输入

列出用户给的文件/通配符，确认存在且为图片格式：
JPG JPEG PNG WEBP BMP TIFF TIF GIF（取第一帧）

### Step 2: 运行裁切

```bash
python "C:\Users\Lucas\.claude\skills\crop-to-9x16\scripts\crop.py" --ratio 9:16 <文件或通配符...>
```

支持单文件和通配符（`*.png`、`**/*.jpg`、`folder/*.webp`）。

常用命令：
```bash
# 裁成 9:16 竖屏（默认）
python scripts/crop.py --ratio 9:16 image.jpg

# 裁成 1:1 正方形
python scripts/crop.py --ratio 1:1 image.jpg

# 裁成 16:9 横屏
python scripts/crop.py --ratio 16:9 image.jpg

# 批量裁切
python scripts/crop.py --ratio 9:16 *.jpg
```

Expected output:
```
✅ 裁切完成: <输出路径>    ← 每个文件一行
✅ 完成: 2/2 文件裁切成功
```

### Step 3: 报告

向用户报告：
- 原图尺寸 → 输出尺寸
- 裁掉了哪边（左右/上下），各裁掉多少像素
- 输出文件路径

## 裁切逻辑

```
原图 912×1136，目标 9:16
当前比例: 912/1136 = 0.803
目标比例: 9/16 = 0.5625
当前 > 目标 → 宽度过剩 → 裁左右
输出宽度: 1136 × 9/16 = 638
每侧裁掉: (912 - 638) / 2 = 137px
输出: 638×1136 ✅
```

## Examples

### Example 1: 裁成 9:16 竖屏

用户说："把这张图裁成9:16"

1. 确认图片存在
2. 运行 `python scripts/crop.py --ratio 9:16 image.jpg`
3. 输出 `image_9x16.jpg`，报告裁切结果

### Example 2: 批量裁正方形

用户说："把文件夹里所有图片裁成1:1"

1. 运行 `python scripts/crop.py --ratio 1:1 *.jpg *.png`
2. 逐个输出带 `_1x1` 后缀的文件

### Example 3: 保留原文件名

用户说："裁成9:16，覆盖原图"

1. 运行 `python scripts/crop.py --ratio 9:16 --inplace image.jpg`
2. 直接覆盖 `image.jpg`

## Troubleshooting

### ModuleNotFoundError: No module named 'PIL'

**原因**：用错了 Python

**解决**：用系统 Python：`D:\Conda\python.exe`（Pillow 12+ 已验证）。

### 输出图片和原图一样大

**原因**：原图已经是目标比例

**解决**：无需裁切，如实告知用户。

### 报 UnicodeEncodeError

**原因**：Windows 控制台 GBK 编码问题

**解决**：脚本已内置 UTF-8 编码处理，确认用的是 `D:\Conda\python.exe`。
