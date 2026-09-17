# YouVibe API 技术笔记

> 来源：逆向 `https://youvibe.run/en/config.js?v=*` 与 `content-viewer.html` 内联脚本（2026-08-21 有效）。

## 后端

- `API_BASE = https://youvibe.run/vibe_backend`
- 页面 JS 里 `CONFIG.BACKEND_URL` 生产值为 `https://youvibe.cn/vibe_backend`，
  但 `.run` 域由 `backendUrlForHost()` 重写为同域 `/vibe_backend`。

## 防护层 1：PoW（Proof of Work）

所有 `/vibe_backend/*` 请求需附三个头：

```
X-Client-Timestamp: <unix 秒>
X-Client-Nonce:     web-<n>
X-Client-Proof:     <8位hex>
```

算法（config.js `buildPublicApiProof`）：

```js
proof = fnv1a32(`${METHOD}\n${path}\n${timestamp}\n${nonce}`)
// path 为去掉 /vibe_backend 前缀的路径，如 /project_metadata_by_id/{id}
// 有效条件: proof 以 '000' 开头（难度 3），nonce 从 web-0 递增
```


FNV-1a 32 位：

```js
digest = 2166136261
for byte in utf8(value): digest = (digest ^ byte) * 16777619 mod 2^32
return hex(digest).padStart(8,'0')
```

URL 构造类请求（如 `<img src>`）也可把三元组放查询参数
`client_ts / client_nonce / client_proof`（`withPublicApiClientProof`）。

## 防护层 2：匿名登录

```
POST /vibe_backend/user/login
Content-Type: application/json
{"type":"temp","data":{"device_id":"<uuid>","platform":"web"}}
-> {"access_token":"...","refresh_token":"...","expires_in":...}
```

`device_id` 浏览器端为 FingerprintJS 指纹；任意随机 UUID 均可通过。

## 关键端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/user/login` | POST | temp 匿名登录换 token |
| `/project_metadata_by_id/{pid}` | GET | 项目元数据（含 `project_images[]`）|
| `/project_files/{pid}/{asset_path}` | GET | 下载文件（需 Bearer + PoW）|
| `/get_file_by_id/{pid}` | GET | 单文件直链（需 Bearer + PoW）|
| `/project_cover_by_id/{pid}` | GET | 封面图 |
| `/create_sharelink_by_project_id/{pid}` | POST | 创建分享链接 |

## 元数据结构（关键字段）

```json
{
  "project_id": "...",
  "project_name": "...",
  "author_name": "...",
  "description": "...",
  "project_images": [
    {
      "asset_path": "original/xxx.png",
      "url": "/project_files/{pid}/original/xxx.png",
      "original_filename": "xxx.png",
      "width": 680, "height": 511, "size": 469637,
      "is_primary": true
    }
  ]
}
```

## 排错

- **401**：时钟偏差过大（timestamp 与服务器差超出容忍窗口）或 PoW 前缀不对；
  先 `curl -sI https://youvibe.run/ | grep -i date` 校时。
- **400 Invalid asset path**：`/project_files/{pid}/` 后必须带具体 asset_path。
- **页面改版**：重新拉 `content-viewer.html` 搜 `project_metadata_by_id` /
  `get_file_by_id`，并 diff `config.js` 的 PoW 实现。
