---
name: minimax-video-prompt-template
description: 一键产出「生视频提示词生成器设定」（MiniMax H3 官方格式）。涵盖文生视频 T2VA、图生视频 I2VA、首尾帧 FL2VA/L2VA、多模态参考（角色/风格/物体/视频参考）与视频编辑替换（角色替换、字幕替换、局部编辑、风格替换）六大模式；内置动作链节拍设计、多镜头连续性锁、音画分层与分域负向词库。Use when user says 生视频提示词、视频提示词模板、H3提示词、图生视频、首尾帧、角色替换视频、视频编辑提示词、把XX做成视频生成器、I2VA、Ref2VA、video prompt generator.
license: MIT
metadata:
  version: 1.0.0
  author: Lucas
  source: 提炼自 MiniMax Design 官方 skill 库（105 个）
  upstream: MiniMax Design / h3-prompt-expert, video-prompting, cinematic-title-sequence, poster-motion-generator, micro-expression-video-generator, music-video-subtitle-generator, 3d-animation-short-generator, co-op-game-intro-generator, mime-object-video, pov-short-film-generator
---

# 生视频提示词设定模板（MiniMax Design 提炼版）

## 这个 skill 做什么

为项目产出**「生视频提示词生成器设定」**：一段可复用的 system prompt（角色定调 + 变量槽位 + 官方 H3 格式模板 + 硬性规则 + 门禁 + 示例），交给任意对话模型或写入应用后，每次填变量 + 传参考素材，即得可直接投喂 MiniMax H3 的最终视频提示词。

覆盖六种模式，其中**替换/编辑类**（角色替换、字幕替换、局部编辑、风格替换）有专门模板——这是把参考图角色放进参考视频、或以源视频为底板做编辑的核心能力。

与 `minimax-image-prompt-template` 配套：本 skill 是流水线下游——上游生图 skill 产出角色设定图/首帧图/末帧锚定图后，本 skill 用 I2VA / FL2VA / 多模态参考模式让其动起来。

## H3 基础参数（写提示词前先确认）

| 参数 | 值 |
|---|---|
| 时长 | 4-15 秒（原生档 5/10/15；故事/广告默认 15s，简单产品/UI/动作 10s） |
| 帧率 | 24 FPS |
| 音频 | 原生立体声；不要配乐时写 `non_diegetic_music: N/A` |
| 画幅 | 21:9 / 16:9 / 4:3 / 1:1 / 3:4 / 9:16；首尾帧模式跟随输入图原始画幅 |
| 语言 | 提示词正文默认英文（用户要求中文除外）；上屏文字按用户原文 |

## 六模式路由表

| 用户需求 / 信号 | 模式 | 读哪个 reference |
|---|---|---|
| 纯文字描述生成视频，无素材 | T2VA | h3-modes.md §家族A |
| 一张图作首帧，让它动起来 | I2VA | h3-modes.md §家族A |
| 首帧 + 尾帧两张图，中间插值 | FL2VA | h3-modes.md §家族A |
| 一张图作末帧/定格锚 | L2VA | h3-modes.md §家族A |
| 多图/多视频/音频组合（角色参考+风格参考+动作参考）| 多模态参考 | h3-modes.md §家族B |
| **编辑已有视频：换角色/换字幕/局部改/换风格** | 编辑替换 | replacement-editing.md |
| 多镜头成片（>15s 或多场景） | 多镜头 | multi-shot-continuity.md |
| 表演细节/运镜设计 | — | shot-action-chains.md |
| 音效/配乐/卡点/旁白对白 | — | audio-soundscape.md |
| 负向词选配 | — | negative-prompt-bank.md |
| 风格锚定/防漂移门禁 | — | style-anchor-video.md |

## 工作流

### Step 0：判定模式与收集信息

1. 按路由表判定模式（编辑替换类必须确认：替换什么、保留什么、底板多长）。
2. 收集：时长、画幅、参考素材清单（每张图/每段视频各自管什么）、必现文字、风格方向。
3. 缺会改变提示词骨架的信息时，用选择题问清（推荐项在前），只问骨架级问题。

### Step 1：读对应 reference

至少读 `references/h3-modes.md`（模式骨架）；编辑替换类必读 `references/replacement-editing.md`。

### Step 2：组装生成器设定

按七段范式组装（同生图 skill 的 generator-skeleton 范式，槽位换成视频变量）：

```
角色定调 → 刚性约束(防崩脸/防漂移/防禁忌动作) → 变量解析
→ 输出规范 → H3格式模版(带{槽位}) → 硬性规则 → 完整示例
```

### Step 3：填充专项模块

- 动作链/运镜/表演 → shot-action-chains.md
- 多镜头 → multi-shot-continuity.md
- 音效配乐 → audio-soundscape.md
- 风格扩展库/门禁 → style-anchor-video.md
- 负向词 → negative-prompt-bank.md（只取真实风险 3-8 项）

### Step 4：门禁自检

通用门禁（完整版见 style-anchor-video.md §门禁）：

1. 对齐首行正确（I2VA/FL2VA/L2VA 必有，且是第一行）
2. `[Shot 1]` 标记在位，时码不超出总时长
3. 主体身份具体锚定（禁"一个美丽的女人"式泛称），无 90° 纯侧脸、无背身
4. 每镜一个主运镜 + 一个主动作，动作链有开始-发展-收束-承接
5. 三层空间在场（前景道具/中景交互/背景环境）
6. 文字清单唯一真源，逐字一致
7. 声音两段分离（overall_soundscape / non_diegetic_music），不要 BGM 时写 N/A
8. 负向词只打真实风险
9. 槽位全部替换，无残留占位符，无〔〕残留

### Step 5：交付三件套

1. **生成器设定全文**（system prompt）
2. **变量槽位表**（变量名 | 说明 | 示例 | 必填性）
3. **一份填好的完整示例提示词**（对齐输出格式验证）

## 通用八段骨架（速查）

```
① 参数声明      模型/时长/画幅/分辨率/帧率/同步音频/模式（首 50-100 字符内）
② 对齐首行      I2VA/FL2VA/L2VA 的首帧/末帧对齐声明（第一行，后接空行）
③ 参考绑定      逐个素材编号声明唯一主职责 + 适配度（够用/部分/不够）
④ 视觉系统      颜色/光/材质/字体/前中后景；风格写成可见特征，不写风格名词
⑤ 主体锁        身份 4-6 个可辨锚点；防互换防漂移；文字清单唯一真源
⑥ 时间线主体    [Shot n] 时码段/节拍表；每镜一个主运镜+一个主动作；因果推进
⑦ 声音段        overall_soundscape（叙事内声）+ non_diegetic_music（配乐，无则 N/A）
⑧ 负向+收束     负向词（只打真实风险）+ 终态锁帧（定格 0.6-2s、文字完全静止）
```

## 简单场景快写（不读 references 的最小路径）

单镜 I2VA 最小模板：

```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] {风格特征句}，{主体身份锚点}，{起始状态}。
First, {动作开始}。Then, {动作发展}。The sequence unfolds as a single continuous {时长}-second shot。
The action resolves as {收束定格}。

overall_soundscape: {与动作同步的材质音 + 环境声}

non_diegetic_music: N/A

Negative prompt: {真实风险 5-8 项}
```

## 上下游衔接（图→视频流水线）

- 上游：`minimax-image-prompt-template` 产出角色设定图（多视图/表情表）、场景图、首帧图、末帧锚定图。
- 角色设定图 → 多模态参考模式的 `<Picture N>`（Subject 角色）；首帧图 → I2VA 的 `<Picture 1>`；海报/版面图 → L2VA 末帧锚或 poster-motion 型"终帧锁定参考"。
- 生图阶段就要为视频铺路：画幅一致、主体占比预留运动空间、风格特征句可直接复制进视频提示词的风格段。
