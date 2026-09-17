# Character Replacement Rules

## subject_definitions 规则

### <Subject 1> 定义模板

```
<Subject 1> is the person in <Picture 1>, with [完整身份描述].
```

完整身份描述必须包含以下全部维度：

| 维度 | 描述要求 | 示例 |
|------|----------|------|
| 面部五官 | 眼型、鼻型、唇型、眉型 | almond-shaped eyes, straight nose, full lips |
| 脸型 | 脸型轮廓 | oval face, sharp jawline |
| 发型 | 发型样式 | shoulder-length wavy hair |
| 发色 | 精确颜色 | jet black with chestnut highlights |
| 肤色 | 肤色描述 | warm medium complexion |
| 身体外貌 | 身材、体型 | slender build, 170cm |
| 服装 | 款式、颜色、材质 | cream silk kurta with gold embroidery |
| 配饰 | 所有可见配饰 | pearl necklace, gold-rimmed glasses, lapel pin |
| 整体形象 | 气质、风格 | regal bearing, traditional Indian ceremonial |

### <Picture 1> 定义模板

```
<Picture 1> is the character reference image for <Subject 1>, showing [front/back/side/close-up views], locking the complete identity of [Subject 1].
```

### <Video 1> 定义模板

```
<Video 1> is the motion reference video providing camera movement, action choreography, scene environment, and composition. The person visible in <Video 1> is NOT <Subject 1> and their facial features, hairstyle, body appearance, clothing, and accessories are completely excluded from the target video.
```

## retention_analysis 规则

```
<Subject 1> (appears in [Shot 1], fully_preserved): all identity attributes from <Picture 1> — facial features, hairstyle, hair color, skin tone, body appearance, clothing, and accessories — are fully preserved.
<Picture 1> ([Shot 1] identity anchor): fully_preserved - locks the complete identity of <Subject 1>.
<Video 1> (camera movement, action, scene, composition): fully_preserved - all camera movement, action choreography, scene environment, and composition are retained.
<Video 1> (original person visible in the video): excluded - their face, hairstyle, body appearance, clothing, and accessories are completely replaced by <Subject 1>.
```

## Hard Constraints Checklist

写 detailed_description 后，逐项检查：

- [ ] 人物身份完整来自 `<Picture 1>`（脸、发型、发色、肤色、五官、身体、服装、配饰）
- [ ] `<Video 1>` 中人物的脸/发型/身体/服装/配饰完全不保留
- [ ] 服装来自 `<Picture 1>`，不来自 `<Video 1>`
- [ ] 面部全程稳定，不漂移、不变化、不崩坏
- [ ] 肢体贴合 `<Video 1>` 原始动作
- [ ] 场景/运镜/构图完全来自 `<Video 1>`
- [ ] 画面风格/摄影质感/光照与 `<Video 1>` 统一
- [ ] 无穿模、无身份混合、无错误肢体

## detailed_description 强制声明

在 `[Shot 1]` 中必须显式声明的句子：

```
[Subject 1] (S1) wears the exact clothing, hairstyle, and accessories from <Picture 1>, with no features inherited from the person visible in <Video 1>.
```

```
The camera movement, action choreography, scene environment, and composition are carried over directly from <Video 1>.
```

```
[Subject 1] maintains the exact identity established in <Picture 1> throughout the entire video — facial features remain stable with no morphing, drift, or degradation.
```
