# H3 六模式契约与官方结构

## 家族 A：单镜成片式（T2VA / I2VA / FL2VA / L2VA）

输出结构固定四块：

```
[对齐首行，仅 I2VA/FL2VA/L2VA 有，必须是第一行，后接空行]
integrated_multimodal_description: [Shot 1] …
overall_soundscape: …
non_diegetic_music: …
(Negative prompt: … 用户工作流需要时附加)
```

### 四模式差异表

| 模式 | 对齐首行 | 描述逻辑 |
|---|---|---|
| T2VA | 无 | [Shot 1] 不加时间戳，先写整体风格+初始取景；后续镜头写递增切点 `[Shot 2] At 00:03.500…`；一镜到底则不列镜头，写连续阶段 |
| I2VA | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` | 首帧锚定→先复述图中可见的风格/主体/构图锚点→动作启动→连续变化→结果收束；禁止写出与首帧矛盾的描述 |
| FL2VA | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark…; Picture 2 (from Shot N) aligns with the S.SS-second mark.`（秒数两位小数如 15.00） | 起始状态→可观察中间变化→逐步缩小差异→精确落到末帧状态；默认一个连续镜头让模型插值 |
| L2VA | 对齐句指向 `[Shot N]` 与 S.SS 秒 | 合理前置状态→明确运动路径→收束→精确落帧；参考图属于最后一镜 |

### 单镜时码写法

- 多切：`[Shot 2] At 00:03.500, …` 递增切点，总和不超时长。
- 一镜到底：无镜头列表，写"连续阶段"（开始→发展→收束），常配 `single continuous shot, no cuts, no transitions`。

## 家族 B：多模态参考六段式

输出结构固定六段（顺序不可变）：

```
subject_definitions:
summary:
retention_analysis:
detailed_description: [Shot 1] …
overall_soundscape:
non_diegetic_music:
```

### subject_definitions 五类标签

| 标签 | 定义内容 |
|---|---|
| `<Subject N>` | 稳定角色/物体/产品身份：形态头身比、五官、配色、材质、服装配饰、标志物 + 防漂移规则 |
| `<Picture N>` | 该图担任的参考角色：角色 / 物件 / 场景 / 风格 / 构图 / 分镜 / 首帧 / 尾帧 |
| `<Video N>` | 该视频担任的参考角色：动作 / 运镜 / 剪辑节奏 / 风格 / 待编辑源素材 / 画内音频 |
| `<Audio N>` | 音色 / 对白 / 音乐节奏 / 歌词 / 情绪；整段用或部分用 |

写法规则：
- 每条参考**只定义一次**，只保留该次任务需要的维度。
- 一条视频兼有画面和声音时，**分轨定义**（视觉轨 + 音频轨各一条）。
- 参考标签必须出现在它发挥作用的镜头里（`<Subject 1> 开口说话`、`<Video 1> 提供运镜路径`），不许只堆在前言。
- 骨架句：`<Subject 1> is the character shown in <Picture 1>. Its visible identity comes exclusively from <Picture 1>, including …, and all other identifying features. <Picture 1> is the source asset for <Subject 1>, not a keyframe, and must never appear in the target video as a visible frame, still image, or closing shot.`

### retention_analysis 写法

写新动作之前先声明保留什么。可见内容层：身份/几何/布局/色彩/空间关系/相机风格/环境/产品logo文字精度；音频层：音色/口音/节奏/歌词/乐器质感/同步点。三态：

```
<Subject 1> (appears in [Shot 1]): fully_preserved — [特征紧凑复述 5-8 项], zero drift.
<Video 1> (camera, action, scene): fully_preserved — [保留维度清单].
<Video 1> (original character): excluded — [被替换内容明确列出].
```

### Reference-Fit 适配三态

- **满足** → 定义并声明保留维度
- **部分满足** → 只定义已满足的维度 + 询问是否补生成缺失锚点
- **不满足** → 不得指派该角色，如实告知，给三选：直接用 / 补生成锚点 / 不用参考纯文生

### R/C/P/E 简化分工（多参考快速分配）

| 角色 | 继承 | 隔离 |
|---|---|---|
| R 风格构图锚 | 风格、光影 | 不继承脸与内容 |
| C 角色锚 | 服装、体型、局部标识 | 隔离原色光环境 |
| P 道具锚 | 形状、材质、磨损、比例 | 隔离原氛围 |
| E 环境锚 | 空间布局 | 色彩由统一风格容器定 |

## 参数声明行（成片级项目用）

`MiniMax H3｜2K｜15 秒｜16:9｜24fps｜同步生成完整原创配乐、环境声与动作音｜OUTPUT_MODE=…｜主路由=…`

素材逐项绑定职责（一个主职责 + 可选次贡献）；身份锁每人物只保留画面可辨认的 4-6 个锚点。

## 文本/UI 特殊规则（画面有精确文字时）

- 文字清单唯一真源：每个精确字符串只出现一次、加引号、全篇同拼写/大小写/标点/空格；`除清单文字外，不出现任何其他可读文字。`
- 复杂 UI（>3 个精确字符串/整页 UI/版面锁定）走"参考图先行"两段式：先出 UI 参考图（生图 skill），视频提示词声明 `@图片1 是 UI/文字/构图/色彩系统参考图。这张内容必须按"图片"来理解，不能按文字重新处理。`
- 允许的动效：面板滑入/按钮高亮/光标点击/加载条；清单文字与参考图完全一致不动。
- 负向：不可读 UI、随机字母、拼错、重复标签、布局漂移、假品牌文字、水印。

## 模式选择决策树

```
有参考素材吗？
├─ 无 → T2VA（要不要精确文字？要→先出文字参考图）
├─ 一张图
│   ├─ 图是"视频开始的样子" → I2VA
│   └─ 图是"视频结束的样子" → L2VA
├─ 两张图（开始+结束）→ FL2VA
├─ 多素材组合（角色+风格+动作+音频）→ 家族B 六段式
└─ 底板是完整视频，要改内容 → 编辑替换（replacement-editing.md）
     ├─ 换角色/换物体 → 角色替换模板
     ├─ 换字幕/换文字 → 字幕替换模板
     ├─ 插入道具/局部改 → 局部编辑模板
     └─ 保时间线换视觉风格 → 风格替换模板
```
