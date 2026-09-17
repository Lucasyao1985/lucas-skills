# 构图、光影、负向条款库

## 1. 画幅规则

- 画幅**必须显式声明**，禁止默认 1:1。写法：`竖屏 3:4` / `横屏 16:9` / `1:1 方图`。
- UI/截图样机内外画幅分离：外画幅（发布图 4:5）与内屏比例（真实手机 19.5:9）各自声明，内屏禁止拉伸变形。
- 宫格图：整图画幅与单格画幅解耦（`{panel_ratio}` 与整图比例分开两个变量）。

## 2. 五种构图模式（替代几何分块）

不要写"左边XX右边XX"的坐标式分块（模型易画成 PPT 版式），用整段构图模式：

| 模式 | 固定句式 |
|---|---|
| 沉浸式 | full-bleed composition, subject and environment fill the entire frame, no borders |
| 环绕式 | central subject surrounded by circular wreath of [元素], symmetrical radial layout |
| 极简留白 | single subject placed on [位置], ≥40% negative space, minimal elements |
| 满版式 | edge-to-edge collage of [元素], dense layered layout, no empty margins |
| 杂志式 | editorial magazine layout, large headline zone at top, hero image occupying lower 2/3 |

反色块负向词（海报/封面类通用）：
`no top color block, no PPT-style layout, no slide template, no geometric quadrant partition, no thick border frame`

## 3. 主体占比区间

- 产品/人物主体占画面高度 60-85%（主图型），40-60%（场景型）。
- 取景完整性：头顶与脚底（或产品底缘）各留 ≥5% margin，禁裁切关键部位。
- 三层空间：前景（装饰/道具）→ 中景（主体）→ 背景（环境），各层内容写具体。

## 4. 光影条款

- 默认中性自然光固定句：`soft natural daylight, color temperature 5000-5500K, even illumination`。
- 影棚白底：`clean studio lighting, soft shadow under product`。
- 物理一致性：高光方向与投影方向必须吻合；彩色光源影响邻近表面颜色。
- 人工布光参数化（最多 3 盏灯，每盏五要素）：`类型(key/fill/rim) + 入射角 + 色温或HEX + 强度 + 软硬`。
- 反 AI 味禁令：no fake light leaks, no plastic specular highlights, no ambient glow walls, no over-saturated color grading。

## 5. 空间语义规避三规则（多视图/多角度必读）

模型对 left/right/mirror 会物理镜像翻面，多视图提示词：

1. **禁用** left side view / right side view / mirrored——侧面统一写 `Side Profile View`；第三面写镜头运动语言 `viewed from the opposite side as if the camera orbited around the subject`。
2. 场景多角度用 **ON SCREEN** 描述 + LAYOUT LOCK：`all objects stay in fixed positions; only the camera viewpoint changes`。
3. 角色卡固定版式写相对关系：`one side shows…, the other side shows…`，不写左右。

## 6. 通用负向词表（按需取用 5-10 项，禁全量倾倒）

```
通用质量：lowres, blurry, jpeg artifacts, watermark, signature, text, logo
解剖：bad anatomy, extra limbs, extra fingers, malformed hands, distorted face,
      asymmetrical eyes, deformed body
写实漂移（非写实风格用）：realistic photo, photorealistic, realistic skin texture,
      depth of field, cinematic lighting, film grain
卡通漂移（写实风格用）：anime, cartoon, illustration, 3D render, cgi
版式反模式：PPT-style layout, top color block, slide template, geometric quadrant
电商：over-saturated colors, fake light effects, plastic sheen, cluttered background,
      props overflowing the frame
```

## 7. defaults 默认参数表（用户未指定时兜底）

| 参数 | 默认值 |
|---|---|
| 分辨率 | 1K（平台有明确规格时用平台值） |
| 光线 | 中性自然光 5000-5500K |
| 负向 | 通用质量 5 项 + 解剖 3 项 |
| 文字 | 无文字，除非用户逐字提供 |
| 张数 | 单场景 4 变体（探索期独立图非拼图） |
| 相机词 | 禁相机型号/胶片/调色词（除非摄影类项目） |

## 8. 出图自检四问（眯眼测试）

1. 眯眼看剪影：主体轮廓是否清晰可辨？
2. 第一眼焦点落在哪里？是否落在主体上？
3. 有没有出现用户没要的文字/水印/多余肢体？
4. 文字（若有）逐字核对：拼写、大小写、标点与用户原文一致？
