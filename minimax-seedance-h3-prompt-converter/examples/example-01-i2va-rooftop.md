# Example 01 — Seedance 字段式 + @图1 → I2VA

## Seedance Input

```text
@图1 参考图中女生站在城市天台边缘，晚风吹动衣角。
0-3s 固定中景，她背对镜头俯瞰城市，风衣下摆翻飞；
3-6s 缓慢推镜至近景，她转过身面向镜头露出笑容，说：“风好大啊！”
6-10s 镜头围绕她顺时针环绕半圈，身后城市灯光渐次亮起，她张开手臂闭上眼睛。
氛围：电影感、黄昏逆光
BGM：轻柔钢琴曲
音效：高空风声、远处街道车流声
```

## Detected Mode

`I2VA` —— 恰好一张图片引用（@图1 → <Picture 1>），作为首帧/主角参考。

## Converted H3 Prompt

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, the young woman shown in <Picture 1> stands at the edge of a city rooftop at dusk, preserving her exact face, hairstyle, and outfit from the image while warm backlight rims her silhouette and the wind moves the hem of her coat. The camera holds a static medium shot as she looks over the skyline with her back to the lens, the city bathed in golden-hour glow below. [Shot 2] At 00:03.000, the camera pushes in with small amplitude at slow speed toward a close shot as she turns to face the lens and breaks into a natural smile. She says with a bright, unprocessed speaking voice (S1): <d>[Mandarin Chinese] 风好大啊！</d> [Shot 3] At 00:06.000, the camera arcs around her clockwise as the city lights come on behind her one district at a time; she spreads her arms and closes her eyes into the wind, backlit hair drifting across the frame. The frame fades to black by 00:10.000.

overall_soundscape: High-altitude wind sweeps across the rooftop while distant traffic hums below, and the fabric of her coat flutters on every gust.

non_diegetic_music: Sparse soft piano notes at a slow tempo, fading out with the closing frame.
```

## Conversion Notes

| 维度 | 处理 |
|------|------|
| 身份 | 删除"参考图中女生"潜在外貌联想；委托句一次成文；正文只写动作与光线 |
| 时间轴 | `0-3s/3-6s/6-10s` → `[Shot 1]`(零锚点) / `At 00:03.000` / `At 00:06.000`；淡出 `by 00:10.000` |
| 镜头 | 固定中景 → static medium shot；缓慢推镜 → pushes in with small amplitude at slow speed；顺时针环绕半圈 → arcs around her clockwise |
| 光线氛围 | 黄昏逆光+电影感 → warm backlight rims her silhouette + golden-hour glow |
| 声音 | 音效→overall_soundscape；BGM→non_diegetic_music（配器+速度）；台词→(S1)+`<d>` 原文保留 |
