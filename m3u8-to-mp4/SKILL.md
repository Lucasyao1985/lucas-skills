---
name: m3u8-to-mp4
description: M3U8视频合并为MP4。当用户提到"合并m3u8"、"m3u8转mp4"、"合并视频"、"ts合并"、"HLS合并"、"迅雷下载的视频合并"、"合并ts文件"、"分段视频合并"时触发。处理迅雷等下载器保存的HLS分段视频（.m3u8+.ts），无损合并为完整MP4文件。
user-invocable: true
metadata:
  author: Lucas
  version: 1.1.0
  openclaw:
    requires:
      bins: [ffmpeg]
    os: [win32, linux]
compatibility: 需要 ffmpeg（含 -allowed_extensions 支持，4.2+）。Windows/Linux 已验证。
---

# /m3u8-to-mp4 — M3U8 分段视频合并技能

将 M3U8/HLS 分段视频（`.ts` 文件）合并为完整 MP4 文件。

## 典型场景

迅雷、IDM 等下载器下载 X/Twitter、抖音、B站等平台视频时，会保存为 HLS 分段格式：

```
视频目录/
  index.m3u8          ← 播放列表（索引文件）
  index/
    0.map             ← 初始化片段（可能有）
    0.ts              ← 视频分段
    1.ts
    2.ts
    ...
```

## 调用方法

```
/m3u8-to-mp4 <m3u8文件路径 | 目录路径>
```

### 例子:
```
/m3u8-to-mp4 "E:\迅雷下载\video.m3u8"
/m3u8-to-mp4 "E:\迅雷下载\video.m3u8\index.m3u8"
/m3u8-to-mp4 "E:\迅雷下载\某个视频目录"
```

## 执行逻辑

### 第 1 步：定位 m3u8 文件

- 如果输入是 `.m3u8` 文件路径 → 直接使用
- 如果输入是目录 → 查找目录内的 `*.m3u8` 文件
- 如果目录内有子目录包含 `.m3u8` → 使用子目录内的文件
- 如果找不到 `.m3u8` → 报错提示

### 第 2 步：确定输出路径

- 输出文件与 m3u8 文件同级目录
- 文件名：将目录名或 m3u8 文件名中的特殊字符清理后加 `.mp4` 后缀
- 如果已存在同名文件 → 自动加序号（`_1.mp4`、`_2.mp4`...）

### 第 3 步：执行合并

```bash
ffmpeg -allowed_extensions ALL -i "index.m3u8" -c copy "output.mp4" -y
```

**关键参数说明：**

| 参数 | 说明 |
|------|------|
| `-allowed_extensions ALL` | **必须**。否则 ffmpeg 会拒绝读取 `.map` 等非标准扩展名的初始化片段 |
| `-c copy` | 直接复制流，不重新编码，速度极快（通常 < 2秒） |
| `-y` | 覆盖已存在的输出文件 |

> ⚠️ **不要省略 `-allowed_extensions ALL`**。迅雷下载的 M3U8 通常包含 `.map` 初始化片段，ffmpeg 默认会因安全策略拒绝读取，导致报错 `Filename extension of '0.map' is not a common multimedia extension`。

### 第 4 步：验证输出

合并完成后检查：
- 输出文件是否存在且大小 > 0
- 用 `ffprobe` 获取时长、分辨率、编码信息
- 与 m3u8 中的分段总时长对比，确认完整性

## 输出格式

```
✅ 合并完成
   输入: E:\迅雷下载\video.m3u8 (12段, 37.45秒)
   输出: E:\迅雷下载\video.mp4 (12.5MB)
   分辨率: 2160x2160
   编码: H.264 High
   帧率: 60fps
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `Filename extension of '0.map' is not a common multimedia extension` | ffmpeg 安全策略阻止非标准扩展名 | 添加 `-allowed_extensions ALL` 参数 |
| `Error when loading first segment` | m3u8 中的路径与实际文件不匹配 | 检查 `index/` 子目录是否存在且包含 `.ts` 文件 |
| 输出文件无法播放 | ts 分段损坏或加密 | 用 VLC 尝试直接打开 m3u8，确认源文件完整性 |
| 合并后时长不对 | 部分 ts 分段缺失 | 对比 m3u8 中声明的分段数与实际文件数 |
| `Invalid data found when processing input` | 未加 `-allowed_extensions ALL` | 必须加此参数 |

## Examples

### Example 1: 迅雷下载的视频合并

用户说："把迅雷下载的这个视频合并了 E:\迅雷下载\video.m3u8\index.m3u8"

1. 定位 m3u8：输入是 .m3u8 文件 → 直接使用
2. 输出路径：`E:\迅雷下载\video.m3u8.mp4`（同名加 .mp4）
3. 执行 `ffmpeg -allowed_extensions ALL -i "index.m3u8" -c copy "video.m3u8.mp4" -y`
4. ffprobe 验证时长/分辨率

Result: `✅ 合并完成` + 输入/输出/分辨率/编码/帧率信息。

### Example 2: 目录输入

用户说："合并这个目录 E:\迅雷下载\某个视频目录"

1. 目录内查找 `*.m3u8`（含子目录），找到后按 Example 1 流程合并
2. 找不到 .m3u8 → 报错提示用户确认目录内容

## 支持的视频来源

- ✅ X/Twitter（迅雷下载的 HLS 视频）
- ✅ 抖音/TikTok
- ✅ B站（部分视频使用 HLS）
- ✅ YouTube（部分下载器保存为 HLS）
- ✅ 任何 HLS 流保存的分段视频

## 注意事项

- 合并是无损操作（`-c copy`），不重新编码，不损失画质
- 输出文件大小 = 所有 ts 分段大小之和（忽略容器开销差异）
- 如果 m3u8 中的 ts 路径使用绝对 URL（`https://...`），ffmpeg 会尝试联网下载——本地文件不会出现此问题
- 加密的 HLS 视频（`#EXT-X-KEY` 标签）需要密钥文件才能合并
