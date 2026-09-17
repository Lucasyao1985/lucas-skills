---
name: x-video-downloader
description: Download any media from X/Twitter posts - videos, images/photos, GIFs, X long-form article (长文) illustrations, and document files linked in the post. Use when user shares an X/Twitter URL and asks to "download video", "save this video", "下载视频", "下载图片", "下载配图", "下载长文配图", "保存媒体", "save media", or provides x.com/twitter.com URLs containing media. Handles regular posts and X articles, batch URLs, custom save path and filename.
metadata:
  author: Lucas
  version: 2.0.0
  input: X/Twitter URL（1 条或多条）+ 可选保存路径/文件名 + 可选媒体类型过滤
  output: 视频 mp4、图片 jpg/png/webp、GIF mp4、或帖子外链的直接文档文件
compatibility: 需要网络访问、Python 3（脚本仅用标准库）与 curl（Windows 自带）；依赖 fxtwitter API（https://api.fxtwitter.com）。X 长文（article）帖子的配图走 article 字段。
---

# X/Twitter 媒体下载器（视频 / 图片 / GIF / 长文配图 / 文档）

自动下载 X（Twitter）帖子中的各类媒体并保存到指定位置。

核心原则：**先出清单，再下载**。不要凭一次 WebFetch 的印象决定下载什么——先跑清单脚本拿到确定的媒体列表（类型、URL、文件名），再逐项下载并验证。X 帖子的媒体形态差异很大（普通帖 / 多图 / 视频 / 长文），清单脚本已把这些差异全部处理掉。

## 工作流程

### Step 1: 解析 URL

从用户输入提取 X/Twitter URL，支持：

- `https://x.com/{username}/status/{tweetId}`
- `https://twitter.com/{username}/status/{tweetId}`
- 已替换的 `fxtwitter.com` / `fixupx.com` / `vxtwitter.com` 链接（同样可解析）
- 一次给多条 URL 时批量处理，逐条出清单

### Step 2: 生成媒体清单

运行清单脚本（Python 标准库，无第三方依赖）：

```bash
python scripts/extract_media.py "https://x.com/{username}/status/{tweetId}"
```

输出每行一个媒体项：`类型<TAB>URL<TAB>建议文件名`，`#` 开头的行为帖子元信息（标题、媒体数）。脚本自动覆盖：

- **普通帖**：`media.photos`（图片）、`media.videos`（视频与 GIF，自动取最高码率 mp4）
- **X 长文（article 帖）**：`article.cover_media`（封面）+ `article.media_entities`（正文全部配图）。注意：article 帖的 `media` 字段是**空的**，这不是故障，脚本会自动改走 article 字段
- **文档**：正文外链中解析后指向直接文件的 URL（.pdf .docx .xlsx .pptx .zip .md .txt .csv 等）

可用参数：

| 参数 | 作用 |
|---|---|
| `--type photo\|video\|gif\|doc` | 只保留指定类型 |
| `--out DIR` | 指定输出目录（默认当前目录） |
| `--download` | 出清单后直接下载 |
| `--name FILE` | 单文件下载时强制文件名 |
| `--flat` | 多文件也不建子目录 |

### Step 3: 确定保存路径与命名

按以下决策规则执行：

- 用户指定了路径/文件名 → 照办，目录不存在则自动创建
- 单个媒体 → 直接存为 `{username}_{tweetId}.{ext}`
- 多个媒体 → 建子目录 `{username}_{tweetId}/`，文件 `{username}_{tweetId}_{序号}.{ext}`
- **X 长文** → 用 `article.title`（清单脚本会输出）起文件夹名，符合用户习惯的格式是 `{YYYY-MM-DD} {标题精简}`，封面文件名带 `_cover`，正文图带 `_img01`
- 默认目录：用户桌面 `C:\Users\Lucas\Desktop\`
- 图片 URL 自动改写为 `name=orig` 原图尺寸

### Step 4: 下载

首选脚本直下（自动带 UA、重试 3 次、校验非 0 字节）：

```bash
python scripts/extract_media.py "{url}" --download --out "{保存目录}"
```

备用方案——按清单逐条 curl：

```bash
curl -L --retry 2 -A "Mozilla/5.0" -o "{save_path}" "{media_url}"
```

### Step 5: 验证并报告

逐项检查文件存在且大于 0 字节，按下方格式汇报；有跳过的项必须说明原因，不许静默丢失。

## 输出格式

```
✅ 已下载 N 个文件（@{username} — {帖子标题或正文前 50 字}）
- 文件：{完整路径}（{大小}，{分辨率或时长}）
- 文件：{完整路径}（{大小}）
跳过：{哪一项，原因}
```

## Examples

### Example 1: 普通视频帖

用户说："下载这个视频 https://x.com/user/status/123"

1. `python scripts/extract_media.py <URL>` → 清单 1 条 video
2. 下载为 `C:\Users\Lucas\Desktop\{user}_123.mp4`
3. 验证大小，按输出格式汇报

### Example 2: 多图帖批量下载

用户说："把这条帖子的图都下载 https://x.com/user/status/456"

1. 清单返回 4 条 photo → 自动建子目录 `{user}_456/`
2. 下载 `{user}_456_01.jpg` 至 `_04.jpg`（原图尺寸）
3. 汇报 4 个文件

### Example 3: X 长文（article）配图 —— 高频场景

用户说："下载这条长文的配图 https://x.com/nanyuan0412/status/2098939503813759389"

1. 清单脚本发现 `media` 为空、`article.media_entities` 有 11 张正文图 + 封面 1 张，并输出 `article.title`
2. 建文件夹 `{YYYY-MM-DD} {标题精简}/`（按用户习惯）
3. 下载 `_cover.jpg` + `_img01.jpg` ... `_img11.jpg`
4. 如用户还要正文文字：`article.preview_text` 只有预览，全文需网页端或截图辅助（长文正文不在媒体下载范围内，但脚本输出的元信息里有标题和预览可供起头）

### Example 4: 自定义路径和文件名

用户说："下载到 D:\Videos，文件名用 test"

→ 存为 `D:\Videos\test.mp4`（目录自动创建）。多文件时 `--name` 不适用，让用户确认子目录命名。

## Troubleshooting

| 症状 | 原因 | 处理 |
|---|---|---|
| API 返回 `media` 为空 | 帖子是 X 长文（article） | 正常现象，脚本自动改走 `article.*` 字段 |
| API 403 / 404 | 私密账号或帖子已删除 | 直接告知用户，不要反复重试 |
| API 429 | 请求过频 | 等 30-60 秒重试一次，仍失败就报告 |
| 只拿到 m3u8 地址 | 视频是 HLS 流 | 下载分段后用 m3u8-to-mp4 skill 合并为 MP4 |
| 外链解析后不是直接文件 | 文档托管在网盘/文章页 | 无法直下，把最终链接给用户手动处理 |
| 下载得到 0 字节文件 | CDN 拒绝无 UA 请求 | 脚本已带 UA 并自动重试；仍失败换 curl 备用方案 |

## 参考

- `references/api-reference.md` — fxtwitter API 完整字段说明（含 article 长文结构，2026-09 实测验证）
- `scripts/extract_media.py` — 清单提取 + 下载，首选入口
- `scripts/download.sh` — 单 URL 兜底下载

## 性能说明

- 常规 2-3 次工具调用完成（清单 + 下载 + 验证）
- 批量 URL 复用同一脚本，一次调用处理全部
