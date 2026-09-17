# LibTV API 接口清单与报错码表

> 真实网关 `https://api.liblib.tv`（前端静态配置里的 `api2.liblib.art` 是假的，勿信 —— 见 E09）。
> 鉴权：自定义请求头 `token: <usertoken>`，**API 不读 Cookie**。usertoken 重新登录后轮换失效。
> 素材域 `https://libtv-res.liblib.art` 免鉴权，可 10 并发直下。

## 核心接口

| 用途 | 方法 | 接口 | 关键参数 |
|---|---|---|---|
| 分享页详情（/detail 页） | GET | `/api/community/project/template/detail` | `projectTemplateUuid=<32位uuid>` ⚠️ 不是 `templateUuid` |
| 画布项目详情（/canvas 页） | GET | `/api/canvas/project/detail-by-space` | `spaceId=<数字>&projectUuid=<uuid>` |
| 项目详情 | GET | `/api/canvas/project/detail` | `projectUuid`（仅自己空间内的项目可查） |
| 我的项目列表 | POST | `/api/canvas/project/list` | `{}` → `projectMetaList[].projectSpaceId` 就是 spaceId |
| 建项目（指定空间） | POST | `/api/canvas/project/create-with-space` | `{name, spaceId}`，返回 `data.projectMeta.uuid` |
| 删项目 | POST | `/api/canvas/project/delete` | `{projectUuid}` |
| **写画布（节点/连线）** | POST | `/api/canvas/nodes/batch` | `{projectUuid, nodes:{create:[…≤200]}, connections:{create:[…≤500]}, requestId}` |
| 草稿/视口 | POST | `/api/canvas/project/draft/update` | `{projectUuid, viewportX/Y/Zoom(字符串), draftJson:"{}"}` |
| 官方复刻（同空间） | POST | `/api/canvas/project/copy-by-project` | `{projectUuid, spaceId}`；跨账号源项目会报 `30001` |
| 版本快照 | POST | `/api/canvas/project/version/snapshot` | 内部版本管理用 |

## 返回码速查

| code | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | — |
| 10000 | 未知错误（`extra_msg` 带 `CheckText`） | 项目名未过社区审核，换 ASCII 名 |
| 10001 | 用户未授权 | token 头缺失/失效，重新抓 usertoken |
| 10003 | 请求参数无效 | 看 `extra_msg` 里提示的 required 字段名，逐个补齐；也用于类型错误（如 viewport 要字符串） |
| 10051 | 数据不存在 | uuid 错、参数名错、或项目不在可见范围 |
| 30001 | 无权访问该项目 | 项目不属于当前 space（源项目私有/新项目未挂空间） |

## 数据结构

- **snapshot 格式**（分享页 flight/模板接口的 `snapshotData`）：`{"nodes":[…react-flow节点], "edges":[…], "savedAt":ms}`
  - 节点：`{id, type:"image"/"video"/"video-clip", position:{x,y}, measured:{width,height}, data:{name, _tag, params:{model,prompt,settings,imageList,…}, url,…}}`
- **entity 格式**（detail-by-space 的 `projectDetail`）：`{"nodeList":[…], "connectionList":[…], "projectDraft":{viewportX…}}`
  - 节点：`{nodeKey, projectUuid, type:<数字枚举>, name, position:{positionX:"…",positionY:"…"}, measured(字符串), parentKey, data:"<JSON字符串>", status, workflowUuid}`
  - 连线：`{projectUuid, connectionId, source, target, sourceHandle, targetHandle, type:"default", deletable, selectable}`
- 两种格式经 `scripts/import_workflow.py` 的 `load_graph()` 统一处理。

## Phase 3 逆向法（接口失效时重建）

1. 抓页面 HTML：`curl -s --compressed "<URL>" -o page.html`
2. 解码 flight 载荷：正则 `self\.__next_f\.push\(\[1,("...")\]` 逐段 `json.loads` 后拼接；`"snapshotData":"$43"` 引用对应行 `43:T<hex长度>,{...}`，从首个 `{` 开始 `raw_decode`
3. 下载全部 `<script src>` chunk（URL 缺 `_next` 段时改写 `static/` → `static/_next/static/`；必须 `--compressed`，否则存的是 gzip）
4. 挖接口：`grep -ohE '["`]/api/[a-zA-Z0-9/_.-]+["`]' c_*.js | sort -u`
5. 挖调用参数：`grep -ohE '.{100}<接口名>.{250}' c_*.js`（真实参数名看调用点，不要猜）

## 历史踩坑表（E01-E09）

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| E01 | HTML 很大但无 `__NEXT_DATA__` | Next.js App Router 纯客户端渲染 | 放弃解析 HTML，走接口重放或 flight 解析 |
| E02 | 猜测的 `/api/...` 全 404 | 接口路径无法枚举 | 从 JS chunk grep |
| E03 | 带 Cookie 请求 `10001` | API 只认 `token:` 头 | 用 token 头重放 |
| E04 | chunk 里 grep 不到接口 | curl 未 `--compressed` | 加 `--compressed` |
| E05 | chunk 下载全 404 | 路径缺 `_next` 段 | 改写 URL |
| E06 | `python3: command not found` | Windows Python 路径 | 探测绝对路径 |
| E07 | Python 找不到 `/tmp/...` | Git Bash 虚拟路径 | `cygpath -w` 转换 |
| E08 | 并发下载 0 个文件 | 路径被 sed 写坏 | 循环内直接用 Unix 风格路径 |
| E09 | 按前端配置 `apiHost` 请求 404 | 真实网关是 `api.liblib.tv` | 以抓包流量为准 |
