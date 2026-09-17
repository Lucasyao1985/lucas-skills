# 分域负向词库

## 使用原则

1. **只打真实风险**：从下表按本项目的风险域取 3-8 项，禁全量倾倒（负向堆砌会稀释权重）。
2. **按风险域定制**：身份项目用身份域、编辑项目用保全域、文字项目用 UI 域，交叉项目各取所需。
3. 负向词写具体失败模式（`no 90-degree side profile`），不写抽象词（`no bad quality`）。
4. 正向优先：能用正向描述解决的（"three-quarter profile"），优先正向，负向只做压制。

## 通用域（几乎总是取 3-5 项）

```
no subtitles, no text overlay, no watermark, no logo,
no on-screen text, no random letters, no garbled characters
```

## 身份 / 防崩脸域（人物+参考图项目）

```
no face distortion, no facial collapse, no deformed face, no morphing face,
no melting face, no distorted eyes, no asymmetrical face, no character drift,
no loss of facial identity, no obscured face, no 90-degree side profile,
no turning back to camera, no extra people, no character swapping,
no identity blending between subjects
```

完整 Master Negative Prompt（2D 风格化人物视频全家桶，可直接引用）：

```
no subtitles, no text overlay, no dialogue, no voice-over, no music, no BGM,
no narration, no cinematic photorealism, no live-action rendering, no 3D CG
simulation, no realistic facial texture, no realistic ear shape, no realistic
skin texture, no realistic hair color recoloring, no photographic eye rendering,
no anime-to-realistic style transfer, no photorealistic facial proportions,
no volumetric lighting, no cinematic lens flare, no motion blur, no depth of
field, no realistic shadows, no gradient shading, no portrait photography
aesthetic, no subsurface scattering, no ambient occlusion, no film grain, no
natural daylight simulation, no makeup application texture, no face distortion,
no facial collapse, no deformed face, no morphing face, no melting face, no
distorted eyes, no asymmetrical face, no character drift, no turning back to
camera, no obscured face, no 90-degree side profile, no loss of facial identity,
no hard cut, no dissolve, no fade to black, no fade in, no wipe transition, no
on-screen text, no watermark
```

## 编辑保全域（替换/编辑类专用）

```
no change to source camera movement, no change to unedited subjects,
no background mismatch, no broken occlusion, no lighting inconsistency,
no new watermark, no temporal flicker, no identity drift,
no original character remnants, no halo or edge mismatch around the replacement,
no missing copies, no extra characters beyond the source plate
```

## 文字 / UI 域

```
no unreadable UI, no random letters, no misspelled words, no duplicated labels,
no extra menu items, no layout drift, no repeated cursor, no fake brand text,
no copying official brand interfaces, no subtitle garbling,
no text moving without cause
```

## 表演域（特写/微表情项目）

```
no mouth corners lifting upward, no crying, no laughter, no exaggerated expression,
no sudden head turns, no cutting to another angle, no rapid mouth opening,
no exaggerated facial morphing
```

## 收束 / 剪辑域

```
no hard cut, no dissolve, no fade to black, no fade in, no wipe transition,
no static freeze frame (除收束定格外), no looping motion, no repetitive locomotion,
no teleporting, no motion jump cuts
```

## 场景风格域（按风格取用）

```
2D 扁平风格：no cinematic photorealism, no live-action rendering, no 3D CG,
  no depth of field, no volumetric lighting, no film grain, no gradient shading
写实风格：no anime, no cartoon, no illustration, no cgi look, no oversaturation
怪核/恐怖：no blood, no jump scare, no face close-up jump, no clean renovation,
  no luxury materials
```

## 口径替换表（负向词的安全替身）

| 想禁的 | 更安全的负向写法 |
|---|---|
| 禁侧脸 | no 90-degree side profile（保留 three-quarter） |
| 禁背身 | no turning back to camera |
| 禁崩脸 | no facial collapse, no identity loss |
| 禁加字 | no on-screen text, no subtitles |
| 禁换人 | no character swapping, no identity drift |
