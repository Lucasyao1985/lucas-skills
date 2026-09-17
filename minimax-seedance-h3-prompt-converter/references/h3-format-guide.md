# H3 Target Format Guide (MiniMax H3 Output Specification)

本文件是转换目标的完整格式规范，提炼自 `minimax-h3-prompt-writing` 的 `references/base-en.txt` 与 `ref-en.txt`。转换产出的每一项都必须符合本规范。

## 1. Five Modes Overview

| Mode | 输入锚点 | 正文起点 |
|------|---------|---------|
| T2VA | 纯文字 | 直接三字段 |
| I2VA | 单图 = 首帧（0.00s） | 首帧指令 + 从图展开 |
| FL2VA | 首帧 + 尾帧 | 首尾对齐指令 + 连续路径 |
| L2VA | 单图 = 尾帧 | 尾帧对齐指令 + 收敛路径 |
| Ref2VA | 多图/网格定义角色与场景 | 六段结构 |

## 2. First-Line Alignment Instructions (verbatim)

首行必须是下列原文之一，随后空一行再进入核心字段。

**I2VA** — 逐字使用：

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

**FL2VA** — `N` 为最后一个 Shot 的编号，`S.SS` 为总时长（两位小数）：

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.
```

**L2VA**：

```text
How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.
```

**T2VA / Ref2VA** 没有对齐行；Ref2VA 以 `subject_definitions:` 开头。

## 3. Base Structure (T2VA / I2VA / FL2VA / L2VA)

三个核心字段，顺序固定：

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `integrated_multimodal_description`：视觉、动作、分镜、说话人、台词、歌声、同步 diegetic 声音的主时间轴。
- `overall_soundscape`：全片环境声、物理动作声、非语言人声的连续段落总结（1–4 句）。
- `non_diegetic_music`：只有观众能听到、角色听不到的配乐（1–3 句）；写配器、速度、节奏、力度变化，不写抽象情绪词、不解释音乐功能。

## 4. Ref2VA Six-Section Structure

顺序固定：`subject_definitions:` → `summary:` → `retention_analysis:` → `detailed_description:` → `overall_soundscape:` → `non_diegetic_music:`

- 标签体系：`<Subject N>`（可复用可见内容）、`<Picture N>`（具体帧/构图锚）、`<Video N>`（整片编辑/续接来源）、`<Audio N>`（音频信号）。标签一经分配，六段内含义不变。
- `summary` 以方括号任务类型开头：`[reference generation]`、`[keyframe completion]`、`[video editing + audio reuse]` 等，多关系用 ` + ` 组合。
- `retention_analysis` 关系标记：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`；音频用 `fully_copy` / `partially_copy` / `reference` / `weak_reference`。
- `detailed_description` 生成类任务通常 350–500 英文词；正文前先用一至两句确立整体风格，再进 `[Shot 1]`。

## 5. Shots, Cuts, and Timestamps

- `[Shot 1]` 开场。官方基准写法首镜不带时间戳；Seedance 转换场景允许在首镜句内补 `At 00:00.000` 零锚点（两种均合规，全篇统一即可）。
- 后续每个 Shot 以严格递增的切点开头：`[Shot 2] At 00:03.500, the camera cuts to ...`
- 切镜动词：`the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot changes to` / `the shot switches to`；用户明确要求时可用 cross-dissolve、fade、wipe。
- 对白跨切点用 `<scenetrans>` 并声明声音延续；被视频结尾截断的语音用 `<cutoff>`。
- 结尾淡出：`The frame fades to black by 00:15.000.`

## 6. Camera Motion Vocabulary

完整表达 = 运动类型 + 幅度 + 速度（幅度中等、速度正常时可省略），写成自然英语句子而非标签堆叠：

| 维度 | 表达 |
|------|------|
| 运动类型 | Zoom In / Zoom Out · Push In / Pull Out · Pan Left / Pan Right · Truck Left / Truck Right · Tilt Up / Tilt Down · Pedestal Up / Pedestal Down · Arc Shot · Tracking Shot · Static Shot · Shake Slightly / Shake Strongly · POV · Roll Clockwise / Roll Counterclockwise |
| 幅度 | with small amplitude / with large amplitude |
| 速度 | at slow speed / at fast speed |

示例：
```text
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
The camera pans right with large amplitude at fast speed, revealing the open doorway.
```

## 7. Speakers and Dialogue

- 出声主体分配稳定 ID `(S1)` `(S2)`；多人齐说用 `(S1,S2)`；同一人全程同 ID；不出声的角色不编号。
- 说话人首次出现时给出音色锚定信息（年龄感、性别、音高、语速、录音距离——属音频特征，不是外貌描写）。
- 格式：`The young woman with a bright, unprocessed speaking voice recorded at close handheld-phone distance (S1) says: <d>[English] ...</d>`
- `<d>` 内只放语言标签和用户提供的原话，逐字保留，不翻译不改写。
- 画外音固定短语 `says in an off-screen voiceover`，其后紧跟声明唇部闭合。
- 画面内可见文字用英文双引号包裹并保留原文：`A red neon sign reading "营业中" glows above the doorway.`

## 8. Word-Count Baselines

| 任务类型 | 正文基准 |
|---------|---------|
| T2VA / I2VA / FL2VA / L2VA | 与信息量匹配，单镜不少于一句完整视听描述，多镜按信息负载分配 |
| Ref2VA detailed_description | 350–500 英文词；对白密集时优先保证完整台词时间轴 |

## 9. Hard Constraints Recap

1. 字段名、标签、时间戳记法永远保持英文原样
2. 台词原文逐字保留在 `<d>` 内
3. `overall_soundscape` 不重复正文已有的对白/歌曲/diegetic 音乐
4. `non_diegetic_music` 无配乐时写 `N/A`
5. 用户明确要求全程静音时两个声音字段都写 `N/A`
