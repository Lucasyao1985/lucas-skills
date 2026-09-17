# fxtwitter API 参考

> 字段结构于 2026-09-14 用真实帖子实测验证（普通长文帖 + article 帖）。

## 获取推文数据

```
GET https://api.fxtwitter.com/{username}/status/{tweetId}
```

返回 JSON：`{ code, message, tweet }`。媒体相关字段集中在 `tweet.media` 与 `tweet.article`。

## 一、普通帖媒体：`tweet.media`

```json
{
  "media": {
    "all":    [ { "type": "photo | video | gif", "...": "..." } ],
    "photos": [ { "type": "photo", "url": "图片URL", "width": 1920, "height": 1080, "altText": "..." } ],
    "videos": [ { "type": "video | gif", "url": "最高码率mp4", "thumbnail_url": "...",
                  "duration": 81.5, "width": 720, "height": 1280,
                  "formats": [ { "url": "...", "bitrate": 2176000, "container": "mp4", "codec": "h264" } ] } ]
  }
}
```

要点：

- 图片 URL 形如 `https://pbs.twimg.com/media/{id}?format=jpg&name=large`，把 `name=large` 改成 `name=orig` 即原图
- 视频 `url` 已是最高码率 mp4；无 `url` 时从 `formats` 里挑 `bitrate` 最高且 `container=mp4` 的
- GIF 的 `type` 为 `gif`，但 `url` 是 mp4（X 的 GIF 实际是 mp4）
- 视频也可能是 HLS 流（m3u8），curl 只能拿分段，需用 m3u8-to-mp4 skill 合并

### 常见视频分辨率

| 分辨率 | 宽度 | 高度 | 典型码率 |
|-------|------|------|---------|
| 360p | 320 | 568 | 632 kbps |
| 480p | 480 | 852 | 950 kbps |
| 720p | 720 | 1280 | 2176 kbps |

## 二、X 长文（article 帖）：`tweet.article`

**关键差异：article 帖的 `tweet.media` 是空对象 `{}`**，配图全部在 `tweet.article` 下：

```json
{
  "article": {
    "id": "文章ID",
    "title": "文章标题",
    "preview_text": "正文预览（前几行）",
    "created_at": "2026-09-13T00:59:08.000Z",
    "cover_media": {
      "media_info": { "original_img_url": "封面图URL", "original_img_width": 1922, "original_img_height": 818 }
    },
    "media_entities": [
      { "media_id": "...",
        "media_info": { "original_img_url": "正文配图URL", "original_img_width": 1024, "original_img_height": 1536 } }
    ],
    "content": { "blocks": [ { "text": "正文段落", "type": "unstyled" } ] }
  }
}
```

要点：

- `media_entities` 是正文全部配图（实测一篇 11 张与帖子实际一致），`cover_media` 是封面，两者是不同图片，都要下
- `article.title` 可用于生成文件夹名（用户习惯：`{YYYY-MM-DD} {标题精简}`）
- `content.blocks` 含正文文字（可提取纯文本），但 media 下载 skill 只负责媒体；正文整理交给人工/后续步骤
- `tweet.text` 在这种帖子里是文章链接本身（`https://x.com/i/article/{id}`），不是正文

## 三、文档类下载

X 不托管文档文件。可下载的"文档"只有正文外链中的**直接文件链接**：

- 正文里的 `t.co` 短链需跟随重定向解析出最终 URL，再判断扩展名或 Content-Type
- 直接文件扩展名：pdf doc docx xls xlsx ppt pptx zip rar 7z md txt csv epub
- 网盘页、飞书/Notion 文章页等非直接链接无法直下，需告知用户手动处理

## 四、帖子其他有用字段

| 字段 | 内容 |
|---|---|
| `tweet.text` / `tweet.raw_text.text` | 推文文本（raw_text 含 t.co 原始链接与 facets） |
| `tweet.author.screen_name` / `.name` | 作者用户名 / 显示名 |
| `tweet.created_at` | 发布时间 |
| `tweet.views` / `.likes` / `.retweets` / `.bookmarks` | 互动数据 |
| `tweet.article` | 仅长文帖有，见第二节 |

## 错误响应

| 状态码 | 含义 | 处理 |
|-------|------|------|
| 200 | 成功 | — |
| 404 | 推文不存在或已删除 | 告知用户，勿重试 |
| 403 | 私密账号 | 告知用户，勿重试 |
| 429 | 请求过频 | 等 30-60 秒重试一次 |
| 500 | 服务器错误 | 稍后重试一次 |
