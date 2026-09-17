# Example 04 — Seedance 首尾帧 → FL2VA

## Seedance Input

```text
首帧：木桌上空玻璃杯，晨光斜照
尾帧：同机位，杯中盛满琥珀色咖啡，热气上升
镜头：固定机位微推，咖啡注入过程连续不断
6秒
音效：液体注入声、清晨鸟鸣
```

单图首帧 + 单图尾帧成对出现 → `FL2VA`；正文写路径不写两张静态图。

## Converted H3 Prompt

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 6.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, an empty clear glass cup sits on a warm wooden table in slanted morning light, matching the framing of Picture 1. The camera pushes in with small amplitude at slow speed as a steady stream of amber coffee pours into the cup from above the frame; the liquid climbs the glass walls, a crema layer swirls across the surface, and thin steam begins to rise. The pour thins to its last drops exactly as the cup reaches fullness, settling into the level, color, steam, lighting, and composition established by Picture 2 at the end of the shot.

overall_soundscape: Morning birdsong carries faintly outside while the coffee stream strikes the empty glass, rises to a fuller liquid tone, then slows to isolated drops as the cup fills.

non_diegetic_music: N/A
```

## Conversion Notes

| 维度 | 处理 |
|------|------|
| 对齐行 | 两帧均属 [Shot 1]（单镜插值），尾帧秒数 = 总时长 6.00 |
| 路径原则 | 不重复描述两张静态图；只写注入过程的可观察变化：液面爬升→油脂漩涡→蒸汽→收尾对齐 |
| 镜头 | 微推 = pushes in with small amplitude at slow speed；FL2VA 默认单镜 |
| 声音 | 注入声全程在 overall_soundscape 展开动态；无 BGM → N/A |
