---
name: youvibe-downloader
description: Download images and files from youvibe.run project pages. Use when user shares a youvibe.run/content-viewer URL with project_id, asks to "download youvibe images", "下载 youvibe 图片", or provides youvibe.run links containing media. Handles PoW proof-of-work protection and anonymous temp login automatically. Supports custom save path.
metadata:
  author: Lucas
  version: 1.0.0
  input: youvibe.run content-viewer URL (with project_id) + optional save path
  output: image/media files downloaded to local directory
compatibility: 需要 Python 3.8+（仅标准库，无第三方依赖）；需要网络访问。依赖 youvibe.run vibe_backend API（PoW 防护 + temp 匿名登录）。
---

# YouVibe 下载器

下载 youvibe.run 项目页面的图片等媒体文件，自动绕过三层防护（PoW 工作量证明 + 匿名登录 + 凭证下载）。

## 使用方式

用户提供 youvibe.run 链接时自动触发。

**示例触发语句：**
- "下载这个页面的图片 https://youvibe.run/en/content-viewer.html?project_id=xxx"
- "下载 https://youvibe.run/en/content-viewer.html?project_id=xxx 的资料"
- "Download images from https://youvibe.run/..."

## 工作流程

### Step 1: 解析 URL
从用户输入提取 `project_id`：
```
https://youvibe.run/en/content-viewer.html?project_id={PROJECT_ID}
```

### Step 2: 运行下载脚本
```bash
python scripts/youvibe_download.py {PROJECT_ID} --out "{保存目录}"
```

脚本自动完成：
1. **PoW 证明**：FNV-1a 哈希挖矿（难度前缀 `000`），生成 `X-Client-Timestamp / X-Client-Nonce / X-Client-Proof` 三头
2. **匿名登录**：`POST /vibe_backend/user/login`（type=temp + 随机 device_id）获取 Bearer token
3. **取元数据**：`GET /vibe_backend/project_metadata_by_id/{id}` 列出全部 `project_images`
4. **逐张下载**：`GET /vibe_backend/project_files/{id}/{asset_path}` + Bearer + PoW 头
5. **保存**：默认 `{原始文件名}`，重名自动加序号

### Step 3: 输出结果

```
✅ 下载完成
- 目录：{save_dir}
- 文件数：N
- 项目：{project_name} by {author_name}
```

## 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `project_id` | ✅ | URL 中 `project_id=` 后的 UUID |
| `--out` | ❌ | 保存目录，默认当前目录 |
| `--info` | ❌ | 仅打印项目元数据不下载 |

## 默认保存路径

用户指定优先；未指定时用当前工作目录。

## 错误处理

| 错误场景 | 处理方式 |
|---|---|
| 401 Unauthorized | PoW 时间戳过期或时钟偏差大 → 脚本自动重取服务器时间重试一次 |
| 无 project_images | 提示该项目不含图片，列出可用字段 |
| 登录失败 | 检查网络；device_id 每次随机生成不会冲突 |
| API 结构变更 | 对照 references/api-notes.md 更新端点与算法 |

## 技术细节

见 `references/api-notes.md`：PoW 算法、登录流程、API 端点清单、页面 JS 对应关系。
