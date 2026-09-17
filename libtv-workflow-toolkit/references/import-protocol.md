# LibTV 画布导入协议（nodes/batch）

> 逆向自画布前端 minified 源码：`convertNodeToCanvasNode`（t6）、`convertEdgeToConnection`（t8）、
> 复制流水线（w_063.js 函数 U）。以下字段名与类型均经 2026-09-12 实测验证（16 节点/26 连线导入成功）。

## 关键事实

1. **LibTV 没有"上传 JSON 导入"功能**。画布图在服务端是节点/连线实体表，不是一个大 JSON。
2. `draft/update` 的 `draftJson` **只存视口外的少量状态**，客户端固定发 `"{}"`；把快照塞进 `draftJson` 服务端不报错但节点数为 0（已实测踩坑）。
3. 官方"复刻"本质 = `detail` 拉源图 → `filterHiddenGraph` → 转换 → `createProject` → `nodes/batch` 逐批写入 → `draft/update` 写视口。
4. 跨账号直接 `copy-by-project` 源项目会报 `30001 source project does not belong to space`，社区模板需走转换重建路线（即本 skill 的导入脚本）。

## 写入流程

```
create-with-space {name, spaceId}          → projectUuid
POST /api/canvas/nodes/batch               → 节点，每批 ≤200，requestId 如 "import:n:0"
POST /api/canvas/nodes/batch               → 连线，每批 ≤500，requestId 如 "import:c:0"
POST /api/canvas/project/draft/update      → {viewportX:"0", viewportY:"0", viewportZoom:"1", draftJson:"{}"}
GET  /api/canvas/project/detail-by-space   → 校验 nodeList/connectionList 数量与源一致
```

## 节点字段（t6 输出，全部必按此类型）

```json
{
  "nodeKey":   "<原节点id，如 i-v3xmfmpmmqea>",
  "projectUuid": "<新项目uuid>",
  "type":      2,                      // 后端数字枚举，见下表
  "name":      "<节点名>",
  "tag":       "prop",                 // = 原 data._tag；无则省略
  "position":  {"positionX": "552", "positionY": "1296"},   // 字符串！
  "measured":  {"width": "622", "height": "350"},           // 字符串，可选
  "parentKey": "",                                          // 无分组为空串
  "data":      "<节点data对象整体的JSON字符串>"              // 删除 _tag（已提升为 tag 字段）
}
```

### 后端 NodeType 数字枚举（模块 143027）

| 前端 type 字符串 | 后端数字 |
|---|---|
| text | 1 |
| image | 2 |
| video | 3 |
| audio | 4 |
| group | 5 |
| script | 20 |
| script_v2 | 21 |
| video-clip | 35 |
| space-scene-720 | 36 |
| reference | 40 |
| shot-breakdown | 45 |

未知类型一律回退 `1`（TEXT）。前端→后端映射对上述类型是恒等的（`convertFrontendNodeTypeToBackend`）。

### data 对象预处理（t6 清洗规则）

- 删除 `_tag`（提升为节点 `tag` 字段）
- `url` 数组中 blob:/data: 开头的项过滤掉
- `poster`/`panoramaUrl` 同理
- 源节点的 `protectionType`、`copyrightChain` 并入 data；`resourceMeta` 并入为 `_resourceMeta`
- 保留其余全部字段：`params`（model/prompt/settings/imageList/videoList/mixedList…）、`clipTimelineData`、`taskInfo` 等原样带入

## 连线字段（t8 输出）

```json
{
  "projectUuid": "<新项目uuid>",
  "connectionId": "e-2jrfz798zmng",
  "source": "i-c35hpp9m6ubh",
  "target": "v-2ev8bhmj66ms",
  "sourceHandle": "source",
  "targetHandle": "target",
  "type": "default",
  "deletable": true,
  "selectable": true
}
```

## 已知坑

1. **viewport 必须字符串**：数字会报 `10003 Mismatch type string`（X/Y/Zoom 三个都是）。
2. **`draftJson` 字段必填**：即使只更新视口也要带 `"{}"`。
3. **建项目名建议 ASCII**：中文名可能触发社区审核 `CheckText` 返回 `10000`。
4. **成片时间线可能引用已删除节点**：智能剪辑节点的 `data.clipTimelineData.clips[].sourceNodeId` 指向的节点可能已不在图中（作者删过旧版），导入后该片段需在画布里手动重接。
5. **导入的是结构与提示词**：节点输出图/视频为空，需在 LibTV 内重新运行生成；素材 URL 已在 data 中，一般可直接复用。
6. **节点 id 保持原样**：连线按 `nodeKey`/`source`/`target` 对应，重命名 id 会导致连线丢失。
