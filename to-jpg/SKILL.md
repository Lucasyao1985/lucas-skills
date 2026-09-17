---
name: to-jpg
description: 高质量转换任意图片格式为JPG，无伪色无画质断层。支持 WEBP, PNG, GIF, BMP, TIFF, JXL, AVIF, HEIC 批量转换。Use when user says "转jpg"、"转换为jpg"、"批量转jpg"、"修复jpg伪色/色块/断层"、"webp转jpg"、"avif转jpg"、"图片格式转换"，或提供图片文件要求输出 .jpg。输出与输入同目录同名 .jpg。
metadata:
  author: Lucas
  version: 1.2.0
user-invocable: true
compatibility: 需要系统 Python（D:\Conda\python.exe）与 Pillow 12+（`python -c "import PIL"` 验证）。Windows 环境已验证。
---

# /to-jpg - 高质量JPG转换

将任意图片格式转换为高质量 JPG，无伪色无画质断层。

## 核心规则（Critical）

1. **必须使用 `scripts/convert.py` 执行转换**——不要自行拼 ffmpeg 或其他命令
2. 输出与输入同目录同名（`image.webp` → `image.jpg`），不覆盖原文件
3. 参数固定：quality=97、4:4:4 全色度采样、透明通道转白色背景、DPI 96
4. 用系统 Python 运行（`D:\Conda\python.exe` 有 Pillow；其他解释器可能没有）

## Instructions

### Step 1: 确认输入

列出用户给的文件/通配符，确认存在且格式在支持列表内：
WEBP PNG GIF BMP TIFF TIF JXL AVIF HEIC

### Step 2: 运行转换

```bash
python "C:\Users\Lucas\.claude\skills\to-jpg\scripts\convert.py" <文件或通配符...>
```

支持单文件和通配符（`*.png`、`**/*.webp`、`folder/*.avif`）。

Expected output:
```
✅ 转换完成: <输出路径>.jpg        ← 每个文件一行
✅ 完成: 2/2 文件转换成功
```

### Step 3: 报告

向用户报告转换数量、成功数、输出文件路径。若有不支持格式（如 gif 动画仅取第一帧），如实说明。

## 质量保证（为什么这样转换）

| 参数 | 值 | 说明 |
|---|---|---|
| 质量 | 97 | 视觉无损 |
| 色度采样 | 4:4:4 | 无颜色压缩损失，最重要 |
| 透明处理 | 白色背景 | 正确处理 Alpha 通道（RGBA/LA/P 模式） |
| DPI | 96 | 标准屏幕分辨率 |

效果与 iloveimg.com 输出质量一致。

## Examples

### Example 1: 单文件转换

用户说："把 image.webp 转成 jpg"

1. 确认 image.webp 存在
2. 运行 `python scripts/convert.py image.webp`
3. 输出 `image.jpg`，报告完成

### Example 2: 批量转换

用户说："把这个文件夹里所有 png 转成 jpg"

1. 运行 `python scripts/convert.py "*.png"`（在文件所在目录）
2. 逐个输出 `.jpg`，报告 `✅ 完成: N/N 文件转换成功`

### Example 3: 修复伪色

用户说："jpg 有色块断层，帮我修复"

说明：JPG 本身已有损，convert.py 输出的是新转的 JPG（4:4:4 无伪色）。若源文件是 WEBP/PNG 转 JPG，转换后即无伪色；若源文件本身是低质量 JPG，无法通过转换修复，如实告知用户。

## Troubleshooting

### 输出乱码或报 UnicodeEncodeError

**原因**：Windows 控制台默认 GBK 编码，emoji 输出崩溃（已修复）

**解决**：脚本已内置 `sys.stdout.reconfigure(encoding="utf-8")`。若仍报错，确认用的是系统 Python 而非其他解释器。

### ModuleNotFoundError: No module named 'PIL'

**原因**：用错了 Python（如 conda 的 aircon-control 环境没有 Pillow）

**解决**：用系统 Python：`D:\Conda\python.exe`（Pillow 12.3.0 已验证）。

### 转换失败

**原因**：文件损坏、格式不受支持、或 Pillow 缺少对应编解码插件（AVIF/HEIC/JXL 需要额外插件）

**解决**：确认格式在支持列表内；报错信息会指明原因，如实报告用户。
