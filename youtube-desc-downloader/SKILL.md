---
name: youtube-desc-downloader
description: Download YouTube video descriptions to local text files. Use when user shares a YouTube URL and asks to "download description", "save description", "下载简介", "下载描述", or wants to batch-download descriptions from a YouTube channel (optionally filtered to one month). Supports single video and batch channel download.
metadata:
  author: Lucas
  version: 2.0.0
  input: YouTube URL (video or channel) + optional save path + optional count/month
  output: UTF-8 text files with video title, URL, and full description (URLs untruncated)
compatibility: Requires Python 3 and yt-dlp in PATH (yt-dlp is used only to list a channel's video IDs). Needs a working network route to youtube.com.
---

# YouTube 视频简介下载器

将 YouTube 视频的完整简介（描述）下载为本地 UTF-8 文本文件。

## 使用方式

用户提供 YouTube 链接时自动触发，下载视频简介到指定路径。

**示例触发语句：**
- "下载这个视频的简介 https://www.youtube.com/watch?v=xxx"
- "下载 https://www.youtube.com/@channel 8月份的，放在 D:\\xxx"
- "把这个频道最新的简介都下载下来"
- 用户直接粘贴 YouTube 链接并提到"简介"、"描述"、"description"

## ⚠️ 首选方法（2026-09 起有效）

**不要用 `yt-dlp --dump-json` 取简介** —— 从数据中心 / VPN 出口 IP 访问时，
YouTube 的 InnerTube `player` 端点会返回
`LOGIN_REQUIRED: Sign in to confirm you're not a bot`，
加 `--cookies-from-browser` 也常常失败（Chrome/Edge 会独占锁住 Cookies 数据库）。

改用 **InnerTube `next` 端点**（watch 页侧栏 / 简介面板的数据源），**不需要登录**。
仓库自带脚本已实现全部逻辑：

```bash
# 频道 + 指定月份
python scripts/fetch_descriptions.py "https://www.youtube.com/@imjuya/videos" \
    --month 2026-08 --out "D:\\目标目录" --limit 44 --proxy http://127.0.0.1:7890

# 单个视频
python scripts/fetch_descriptions.py "https://www.youtube.com/watch?v=4Qd11REGVkk" \
    --out "D:\\目标目录" --proxy http://127.0.0.1:7890
```

### 原理（自己实现时照抄）

1. `POST https://www.youtube.com/youtubei/v1/next?key=<WEB_KEY>&prettyPrint=false`
   body：`{"context":{"client":{"clientName":"WEB","clientVersion":"2.2026...","hl":"zh-CN","gl":"US"}},"videoId":"<id>"}`
   `WEB_KEY` 可用 `AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8`（YouTube 网页端公开 key）。
2. 标题取 `…videoPrimaryInfoRenderer.title.runs[].text`（**是原始中文标题**，
   比 `--flat-playlist` 返回的自动翻译英文标题靠谱）。
3. 简介取 `…expandableVideoDescriptionBodyRenderer.attributedDescriptionBodyText
   .attributedDescription`：
   - `.content` 是正文，但**所有 URL 被截断成 ~40 字符**（如 `https://x.com/…/2083...`）；
   - `.commandRuns[]` 里每项有 `startIndex` / `length` / `onTap.innertubeCommand
     .urlEndpoint.url`，指向 `/redirect?...&q=<真实URL>`。
4. **按下标倒序**把 `content[start:start+length]` 替换成解码后的真实 URL，
   才能得到与网页一致的完整简介（否则 URL 全是省略号）。

### 输出文件格式

```
Title: <原始完整标题>
URL: https://www.youtube.com/watch?v=<id>
---

<完整简介>
```

文件名规则（橘鸦Juya / AI 早报系列）：
把标题里的日期标记挪到最前面 →
`【AI 早报 2026-08-03】MiniMax H3 多模态视频模型预计将于今日发布权重.txt`

**日期标记有两种写法，都要认：**

| 标题里的标记 | 处理 |
| --- | --- |
| `【AI 早报 2026-08-27】`（标准） | 直接用 |
| `【AI 早报0909】`（偶发省略写法） | 补全年份 → `2026-09-09`；年份取页面 `videoPrimaryInfoRenderer.dateText` 里的 4 位年，取不到就用当前年 |

⚠️ 别用 `dateText` 当发布日期：它受 `gl` 时区影响会差一天
（实测 09-09 那期 `dateText` 是 `2026年9月8日`，而标题写的是 0909）。
**标题标记才是准的**，`dateText` 只用来补年份。

## 网络要求（本机）

- YouTube 直连不通。需走系统代理 `http://127.0.0.1:7890`（Clash）。
- 沙箱内连不上 7890，执行命令时必须 **关闭沙箱**（`dangerouslyDisableSandbox`）。
- ⚠️ **一定要显式传 `--proxy http://127.0.0.1:7890`**。
  宿主环境已经预设了 `HTTPS_PROXY=http://127.0.0.1:1861`（WorkBuddy 沙箱代理，
  白名单不含 youtube），脚本若自动读取环境变量就会走它并报
  `Tunnel connection failed: 502 Bad Gateway`。
  脚本启动时会打印 `proxy: …`，先看这一行确认走对了出口。

## 仍然可用的 yt-dlp 用法

| 目的 | 命令 | 说明 |
| --- | --- | --- |
| 列频道视频 ID | `yt-dlp --flat-playlist --print "%(id)s" <channel>/videos --playlist-end 60` | ✅ 可用（browse 端点不拦） |
| 取简介 | `yt-dlp --dump-json <video>` | ❌ LOGIN_REQUIRED |
| 最近 15 期简介 | `https://www.youtube.com/feeds/videos.xml?channel_id=<UC…>` | ✅ 可用，含 `<media:description>`，但**只有 15 条**，不够整月 |

频道 ID 拿法：抓频道页 HTML，grep `"externalId":"UC…"`（`--flat-playlist --print "%(channel_id)s"` 返回 `NA`，不可用）。

## 常见问题

### 问题：所有 player client 都报 "Sign in to confirm you're not a bot"
`tv` / `android_vr` / `web_embedded` / `mweb` / `web_safari` / `tv_simply` 全部一样。
`android` / `ios` 直接 400 `Precondition check failed`。
**结论：换 client 没用，改用 `next` 端点（见上）。**

### 问题：`--cookies-from-browser chrome` 报 "Could not copy Chrome cookie database"
Chrome/Edge 运行时独占锁定 `…/User Data/Default/Network/Cookies`，
`shutil.copy2` 报 `WinError 32`，`sqlite3` 以 `?immutable=1` 也打不开。
只能先关闭浏览器，或改走 `next` 端点（推荐，无需 cookie）。

### 问题：公共 Invidious / Piped 实例
2026-09 实测基本全挂：`inv.nadeko.net` / `yewtu.be` / `invidious.f5.si` 返回
`403 Endpoint disabled`，Piped 实例 502/525/500，`api.invidious.io` 列表里
绝大多数 `"api": false`。**不要指望这条路。**

### 问题：中文乱码
Windows 终端默认 GBK。脚本开头已 `sys.stdout.reconfigure(encoding='utf-8')`，
写文件一律 `encoding='utf-8'`。

### 问题：文件名含非法字符
`re.sub(r'[\\/:*?"<>|]', '', title)` 清理，并截断到合理长度。

## Examples

### Example 1: 下载单个视频简介
```bash
python scripts/fetch_descriptions.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
    --out . --proxy http://127.0.0.1:7890
```
→ 输出 `dQw4w9WgXcQ.txt`，含 Title / URL / 完整简介。

### Example 2: 下载某频道某月全部简介
```bash
python scripts/fetch_descriptions.py "https://www.youtube.com/@imjuya/videos" \
    --month 2026-08 --out "D:\\.claude-workspaces\\mimo\\AI早报视频简介-橘鸦Juya\\2026年8月" \
    --limit 44 --proxy http://127.0.0.1:7890
```
- `--limit` 要覆盖到目标月份最早那条，宁大勿小（每个 ID 一次请求，约 1-2 秒）。
- 已存在的文件会重算并标记 `same` / `updated` / `new`，可安全重复运行。
- 实测 2026-08 全月 31 条：`31 saved, 13 skipped, 0 failed`，重跑全部 `same`。
- 实测 2026-09（截至 9月11日）11 条：`11 saved, 3 skipped, 0 failed`。

### Example 3: 追更进行中的月份
```bash
python scripts/fetch_descriptions.py "https://www.youtube.com/@imjuya/videos" \
    --month 2026-09 --out "D:\\.claude-workspaces\\mimo\\AI早报视频简介-橘鸦Juya\\2026年9月" \
    --limit 14 --proxy http://127.0.0.1:7890
```
频道每日更新，重复跑只会把新一期标成 `new`，旧的标 `same`，不会重复写。
