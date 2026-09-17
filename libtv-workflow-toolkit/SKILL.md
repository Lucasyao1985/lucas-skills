---
name: libtv-workflow-toolkit
description: 下载与导入 LibTV（liblib.tv / LiblibAI 视频画布）自研画布工作流。自动从 /detail/<uuid> 分享页或 /canvas 画布页提取完整工作流 JSON（节点+连线+提示词+模型参数），按 01_工作流JSON/02_配图/03_视频/04_音频 目录规范批量下载全部媒体素材并做大小与魔数双校验；还可将工作流通过官方 nodes/batch 协议导入到自己账号的画布。当用户给出 liblib.tv 或 libtv 链接并要求下载工作流/素材/成片视频、询问 LibTV 画布节点与提示词数据、或要求把 LibTV 工作流复刻/导入/克隆到自己账号时使用。触发词：liblib、libtv、LibTV画布、下载工作流、导入画布、复刻模板。不适用于 ComfyUI/RunningHub 等其他平台的工作流。
metadata:
  author: Lucas
  version: 1.0.0
  category: workflow-automation
---

# LibTV 画布工作流下载与导入工具

## Important（开始前必读）

- **鉴权**：LibTV API 不读 Cookie，只认自定义请求头 `token: <usertoken>`。usertoken 会随重新登录轮换失效。
- **公开详情页无需登录**：`/detail/<uuid>` 分享页数据内嵌在页面里，匿名可取；只有**导入到自己账号**和**访问私有画布**才必须提供 usertoken。
- **三域名分工**：`www.liblib.tv`（页面）、`api.liblib.tv`（数据接口，真实网关）、`libtv-res.liblib.art`（素材直链，免鉴权可并发下载）。
- 本工具产出的是 LibTV 原生画布格式，**不能直接导入 ComfyUI**（节点体系不同）。

## Instructions

### Step 1: 抓取工作流 JSON

```bash
python scripts/fetch_detail.py "https://www.liblib.tv/detail/<templateUuid>" --out <输出目录> [--token <usertoken>]
```

- 自动识别页面类型：`/detail/<uuid>` 走社区模板接口（有 token 时）或 flight 载荷解析（无 token 也能用）；`/canvas?projectId=...&spaceId=...` 走 `detail-by-space` 接口（必须给 token）。
- 产出：`01_工作流JSON/project_full.json`（画布图：snapshot 格式为 `nodes+edges`，画布页格式为 `nodeList+connectionList`）、`project_meta.json`、`api_response_full.json`、`cover.jpg`。
- 成功标志：`nodes: N connections: M`（N>0），meta 含 `name/snapshotId/updateAt`。

### Step 2: 批量下载素材

```bash
python scripts/download_assets.py --input <输出目录>/01_工作流JSON/project_full.json --out <输出目录>
```

- 解析全部节点收集 `libtv-res.liblib.art` 素材链接（自动跳过 `/wm/` 水印版），按模板规范命名 `{节点序号}_{节点名}_{序号}.{扩展名}` 落盘到 `02_配图/`、`03_视频/`、`04_音频/`，成片另存为 `03_视频/000_成片_final_output.mp4`。
- 10 并发 curl 下载，完成后逐文件校验：大小 ≥1KB 且 PNG/JPG/WEBP/MP4 魔数正确。
- 先看清单不下载：加 `--dry-run`。

### Step 3: 导入到自己账号（可选，需要 usertoken）

```bash
python scripts/import_workflow.py --input <输出目录>/01_工作流JSON/project_full.json \
  --token <usertoken> --space-id <你的spaceId> [--name import-xxx] [--project-uuid <已有空项目uuid>]
```

- 流程：`create-with-space` 建项目 → `nodes/batch` 写入节点（≤200/批）与连线（≤500/批）→ `draft/update` 写视口 → `detail-by-space` 校验节点/连线数与源一致。
- `spaceId` 获取：登录 LibTV 后任一自己项目列表接口返回 `projectMetaList[].projectSpaceId`；或 F12 抓任意 canvas 请求查看参数。
- ** LibTV 没有上传 JSON 文件导入的功能**，快照 JSON 必须经本脚本转换为节点实体协议才能写入（详见 references/import-protocol.md）。
- 项目名建议用 ASCII（中文可能被社区审核接口 `CheckText` 拒绝，报 `10000 未知错误`）。
- 成功标志：`✅ nodes: N  connections: M` 与源一致，输出画布 URL。
- 失败默认保留项目供排查；确认不要再加 `--delete-on-fail`。

### Step 4: 校验与报告

- 下载与导入完成后向用户报告：文件数/体积/校验结果、节点数与连线数、真实生产链路（依据节点上下游关系与模型名归纳）、成片时间线引用的节点是否在图中存在（智能剪辑 `clipTimelineData` 可能引用已被作者删除的旧节点）。

## Examples

### 例 1：下载公开分享页工作流

用户说："下载 https://www.liblib.tv/detail/823a16f5... 里面的工作流和素材"

1. `fetch_detail.py <URL> --out F:/820/2026-09-12 项目名`（无 token，走 flight 解析）
2. `download_assets.py --input .../project_full.json --out F:/820/2026-09-12 项目名`
3. 汇报：72 个文件 343.6MB 全部校验通过；16 节点/26 连线；生产链路 = Logo→定妆→分镜→Hailuo 视频→智能剪辑。

### 例 2：导入到自己的画布

用户说："把这个 LibTV 工作流复刻到我账号里"

1. 确认已有 `project_full.json` 与有效 usertoken（没有先跑 Step 1，并请用户提供 token）。
2. `import_workflow.py --input ... --token ... --space-id ... --name my-import`
3. 校验输出 `nodes/connections` 与源一致，给出画布 URL 让用户打开检查。

## Troubleshooting

| 报错 | 根因 | 解决 |
|---|---|---|
| `10001 用户未授权` | token 头缺失/失效 | 重新抓 usertoken（F12 → Network → 任意 api.liblib.tv 请求头 `token:`） |
| `10003 请求参数无效`（提示缺字段） | 参数名与接口不符 | 以接口报错提示的 required 字段名为准逐个补齐（如 `spaceId`、`projectTemplateUuid`） |
| `10051 数据不存在` | uuid 错或参数名错（如用 `templateUuid` 而非 `projectTemplateUuid`） | 核对 URL 参数与接口参数名差异 |
| `30001 无权访问该项目` | 项目不属于当前 space（源项目私有/新项目未挂空间） | 用 `create-with-space` 建项目；查自己的 `projectSpaceId` |
| `10000 未知错误 + CheckText` | 项目名未过社区审核 | 换 ASCII 项目名 |
| flight 解析出 0 节点 | 页面结构变化 | 按 references/api-endpoints.md 的 Phase 3 重新逆向 JS chunk |
| Python 报 `/tmp/...` FileNotFoundError | Git Bash 虚拟路径与 Windows Python 不一致 | 用 `cygpath -w` 转换或直接用 `C:/...` 路径 |
| JS chunk grep 不到接口 | curl 未加 `--compressed` 存了 gzip 原始字节 | 统一加 `--compressed` |

## Performance Notes

- 下载量大（数百 MB）时保持 10 并发即可，libtv-res 域名无需鉴权不会限流到失败。
- 导入前不要修改 `project_full.json` 的节点 id，连线依赖 `nodeKey` 对应。
- 完整接口清单、报错码表见 `references/api-endpoints.md`；节点/连线字段映射见 `references/import-protocol.md`。
