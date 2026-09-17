# Example 03 — Seedance 关键词堆叠式 → T2VA（模糊风格词展开）

## Seedance Input

```text
cinematic shot, a lighthouse in a storm at night, dramatic lighting, slow dolly in, 35mm, waves crashing, orchestral score, the keeper steps onto the gallery and grips the railing
```

无图片引用，无显式时间轴 → `T2VA`；默认时长 10s（已向用户注明假设）。

## Converted H3 Prompt

```text
integrated_multimodal_description: [Shot 1] Live-action, cinematic, a low wide-angle shot frames a stone lighthouse on a wave-battered promontory at night, storm light breaking in cold blue shafts through torn cloud while rain streaks the 35mm lens. The camera pushes in with small amplitude at slow speed toward the tower as spray explodes against the seawall. [Shot 2] At 00:05.000, the shot cuts to the lamp room gallery in medium-close framing: the weathered keeper steps through the doorway, braces against the gale, and grips the wet iron railing with both hands as the beam sweeps overhead and throws his shadow across the deck. He holds his ground, coat snapping in the wind.

overall_soundscape: Heavy surf detonates against the rocks while sustained wind roars past the tower, rain rattles on the metal gallery deck, and the lamp mechanism turns with a low mechanical pulse.

non_diegetic_music: Low strings build in slow swells with sparse brass accents, cresting as the keeper grips the railing and receding under the final beat.
```

## Conversion Notes

| 维度 | 处理 |
|------|------|
| 模糊词展开 | `cinematic shot` → 低角度广角+冷蓝光束+雨痕；`dramatic lighting` → 具体光源方向与质感 |
| 摄影参数 | `35mm` 保留为镜头感描述（rain streaks the 35mm lens） |
| 动作增强 | "steps onto the gallery and grips the railing" 扩展出顶风、双手抓握、灯束投影、衣摆——未新增情节 |
| 时间轴 | 无显式时间段；按信息负载切为两镜，切点 At 00:05.000 |
| 声音 | waves crashing/wind → overall_soundscape；orchestral score → non_diegetic_music 写配器与动态 |
