---
name: wechat-article-downloader
description: >
  下载微信公众号文章为本地 Markdown 和 HTML 文件，并自动下载全部图片到本地
  images 目录，保留标题、公众号名、作者、发布时间、摘要、加粗、链接、列表、
  引用、代码块和表格。Use when user pastes a WeChat Official Account article
  URL (mp.weixin.qq.com/s/...) and asks to download, save, archive, or convert
  it, or says "下载公众号文章", "保存微信公众号", "下载这篇微信文章",
  "把公众号文章转成 Markdown", "download wechat article",
  "save wechat article", "archive WeChat article". Trigger on any URL
  containing mp.weixin.qq.com/s/.
metadata:
  author: Lucas
  version: 1.0.0
compatibility: 需要 Python 3.8+，并安装 requests、beautifulsoup4（pip install requests beautifulsoup4）。需要网络访问 mp.weixin.qq.com 与图片域名 mmbiz.qpic.cn。
---

# WeChat Article Downloader

下载微信公众号文章，保存为带本地图片的 Markdown 与 HTML，供离线阅读、归档或二次处理。

## 快速开始

```bash
python -X utf8 "<skill目录>/scripts/download_article.py" "https://mp.weixin.qq.com/s/xxxxxx" --output "D:/保存目录"
```

输出为 SUCCESS 开头的 JSON，包含 title / account / publish / markdown / html / images_ok / images_failed。失败时输出 ERROR 开头的原因并以非零码退出。

## 输出结构

未指定 `--output` 时，默认在当前目录创建 `./<文章标题>/`：

```text
文章标题/
├── index.md      # Markdown 正文，图片引用指向本地 images/
├── index.html    # 独立 HTML，保留微信原始排版样式，本机双击即可离线阅读
└── images/       # 按出现顺序命名：001.gif、002.png、003.jpg ...
```

index.md 顶部自动生成元信息：标题、公众号、作者、发布时间、摘要、原文链接。

## 工作流程

1. 确认链接属于 `mp.weixin.qq.com/s/`（短链 `mp.weixin.qq.com/s?__biz=...` 也支持）。
2. 运行脚本（加 `-X utf8` 避免 Windows 控制台中文乱码）。
3. 检查结果：
   - `images_failed` 大于 0：图片保留远程链接，正文不受影响；可重跑一次，偶发 CDN 拒连会恢复。
   - 输出 ERROR：按下方 Troubleshooting 处理。
4. 向用户报告：文章标题、保存路径、图片成功/失败数量。

## 命令行选项

| 选项 | 说明 |
| --- | --- |
| `--output DIR` / `-o` | 输出目录，默认 `./<文章标题>/` |
| `--format md\|html\|both` / `-f` | 输出格式，默认 `both` |
| `--no-images` | 不下载图片，Markdown/HTML 保留远程图片链接 |

批量下载多篇文章时，在同一输出根目录下逐篇运行即可，每篇文章一个子目录。

## 示例

### 示例 1：下载单篇文章

用户说："下载这篇公众号文章 https://mp.weixin.qq.com/s/8Us0IEoNZzK9jb8awhrAlg"

```bash
python -X utf8 scripts/download_article.py "https://mp.weixin.qq.com/s/8Us0IEoNZzK9jb8awhrAlg" -o "C:/Users/Lucas/Downloads/wechat"
```

结果：生成 `C:/Users/Lucas/Downloads/wechat/<标题>/index.md`、`index.html` 与 `images/`（34 张图片全部成功）。

### 示例 2：只存文字、不要图片

用户说："把这篇文章的公众号内容存成 markdown，图片不用下"

```bash
python -X utf8 scripts/download_article.py "https://mp.weixin.qq.com/s/xxxxxx" -f md --no-images
```

结果：只生成 `index.md`，图片为 mmbiz.qpic.cn 远程链接。

## Troubleshooting

### ERROR: 该内容已被发布者删除 / 此内容因违规无法查看
文章已被作者删除或被平台下架，无法下载。告知用户即可，不要重试。

### ERROR: 页面中没有找到正文（#js_content）
常见原因：链接需要微信客户端验证（环境异常页）、是公众号主页而非文章页、或该链接是"合集/专辑"页。让用户确认链接是否为单篇文章正文页；若确认是文章，建议用户在浏览器中打开并提供能正常访问的会话 Cookie 后再试。

### ERROR: 无法抓取页面: ...
网络问题或被临时限流。等待约 30 秒重试一次；仍失败则检查本机网络与代理设置。

### 部分图片下载失败（images_failed 大于 0）
mmbiz.qpic.cn 偶发拒连。脚本已自动重试 2 次；失败的图片在输出中保留远程 URL，通常整体重跑一次即可补齐。

### Windows 控制台中文乱码或 UnicodeEncodeError
务必带 `-X utf8` 参数运行（脚本同时会自行将 stdout 切到 UTF-8）。

## 注意事项

- 仅供个人学习与备份用途，请尊重原作者版权，不要批量抓取或二次传播。
- 该脚本直接解析页面 HTML，无需登录、无浏览器依赖；公众号文章正文是服务端渲染的，正常网络下即可获取。
