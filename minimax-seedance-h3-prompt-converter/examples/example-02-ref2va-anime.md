# Example 02 — Seedance 多图角色设定 + 时间轴 → Ref2VA（二次元）

## Seedance Input

```text
图1：白发红瞳女剑士角色设定（三视图），服装为黑色短甲配赤色腰带
图2：竹林场景设定，晨雾
0-4s: 竹林中景，她按刀静立，雾气流动
4-7s: 快速拔刀斩出，一道剑光掠过，竹叶纷落
7-10s: 收刀归鞘，她睁眼看向镜头，低声说：“还有谁？”
风格：日式动画、赛璐璐上色
BGM：太鼓与尺八
音效：竹林沙沙声、拔刀锐响
```

## Detected Mode

`Ref2VA` —— 两张图片分别定义角色（图1）与场景（图2），非首帧锚定。

## Converted H3 Prompt

```text
subject_definitions:
<Subject 1> is the white-haired, red-eyed swordswoman defined by <Picture 1>, with her facial design, hairstyle, and black short armor with a crimson sash taken entirely from <Picture 1>.
<Subject 2> is the misty bamboo grove at dawn established by <Picture 2>, with tall green culms and drifting ground fog.

summary:
[reference generation] The target video shows <Subject 1> standing in <Subject 2> across three shots: a still ready stance, a single fast draw-and-slash that scatters leaves, and a resheathing beat ending on her gaze toward the viewer.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - character design, hair color, and outfit follow <Picture 1> without change.
<Subject 2> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - grove layout, morning fog density, and soft dawn light retained from <Picture 2>.

detailed_description:
The target video uses a Japanese cel-shaded anime style with clean line art and flat color fields.
[Shot 1] A medium shot establishes <Subject 2>, the bamboo grove wrapped in slow-drifting morning fog. <Subject 1> stands motionless at center frame, one hand resting on the sheath at her hip, culms swaying faintly around her.
[Shot 2] At 00:04.000, the shot cuts to a slightly low angle as she explodes into a single draw-and-slash; an arc of white blade-light crosses the frame while severed bamboo leaves spiral down through the fog around her planted back foot.
[Shot 3] At 00:07.000, the shot cuts back to the medium framing as the blade slides home into the sheath with a soft click. She lifts her chin and looks straight into the lens through the thinning mist. She says with a calm, low young female voice (S1): <d>[Mandarin Chinese] 还有谁？</d>

overall_soundscape: Bamboo culms creak and leaves rustle in the drifting fog, joined by the sharp ring of the draw, the whisper of falling leaves, and a soft click as the blade resheathes.

non_diegetic_music: Sparse taiko drum hits answered by a shakuhachi line at a deliberate tempo, stopping just before the final line lands.
```

## Conversion Notes

| 维度 | 处理 |
|------|------|
| 身份 | 角色三视图 → `<Picture 1>`；外貌特征只出现在 `subject_definitions` 且标注"取自图"；正文零外貌词 |
| 二次元规则 | 与真人同规则；委托措辞用 "defined by / taken entirely from <Picture 1>" |
| 六段结构 | subject_definitions → summary → retention_analysis → detailed_description → 声音两段，顺序固定 |
| summary | 任务类型 `[reference generation]`；无帧锚定故不含 keyframe completion |
| 时间轴 | 三段时间轴 → Shot 2 `At 00:04.000`、Shot 3 `At 00:07.000` |
| 台词 | 中文原句保留，语言标签如实标注，(S1) 全程唯一 |
