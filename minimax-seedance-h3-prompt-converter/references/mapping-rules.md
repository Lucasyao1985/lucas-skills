# Conversion Mapping Rules (Seedance → H3)

本文件是转换器的核心规则库：身份委托、时间轴、摄影语言、声音拆分、动作增强、模式判定。

---

## 1. Identity Delegation（人物身份一致性）— 硬约束

### 1.1 触发条件

满足任一条即生效：
- 输入含 `<Picture N>` / `@图N` / `<图片N>` / `@Image N` 等图片引用
- 用户声明"上传了人物参考图"、"根据图片人物"
- Ref2VA 分镜网格定义了人物

### 1.2 禁止描述清单（零容忍）

| 类别 | 禁写示例 |
|------|---------|
| 脸型 | V-line face, oval face, round face, delicate jawline |
| 五官 | large bright eyes, small nose, glossy lips, double eyelids |
| 发型发色 | long straight black hair, blonde bob, curly ponytail |
| 肤色 | fair skin, pale complexion, tanned skin, visible pores |
| 身材比例 | slender figure, curvy body, petite build, tall and slim |
| 固定服装 | ivory mandarin-collar top, charcoal wide-leg trousers, red silk qipao |

真人角色（写实人物、商业人像、模特、演员、网红）与二次元角色（动漫人物、游戏角色、插画角色、卡通角色）适用同一规则。

### 1.3 标准委托句

- 真人：`the person shown in <Picture 1>` / `the young woman shown in <Picture 1>`
- 二次元：`the character shown in <Picture 1>`
- 强调版（首次出现时）：`The man shown in <Picture 1> — whose exact face, hairstyle, and clothing are taken solely from <Picture 1> and never change — ...`
- 场景/环境同样可委托：`preserving the environment, lighting, color palette, and spatial composition established by <Picture 1>`

全片对同一角色只做一次完整委托；后续镜头用 `the same woman` / `the same character` 回指，不再重复委托句。

### 1.4 允许描述的内容（表演层）

动作、姿态、表情变化、视线方向、在画面中的位置与占比、与镜头的距离、肢体动力学——这些不是外貌，全部保留并可增强。

### 1.5 唯一例外协议：换装镜头

参考图里不存在的服装变化（如原片 Shot 5 换旗袍）：
- 图片无法提供该信息，完全不写模型无从得知；但写了就有身份泄漏风险
- 协议：仅保留最短必要描述（如 `now wearing the single outfit change of the video, a short-sleeve red qipao`），并显式标注这是全片唯一换装
- 交付时向用户提示此风险，由用户决定保留或删除

---

## 2. Timeline Conversion

### 2.1 映射规则

- 每个 Seedance 时间段 → 一个 `[Shot N]`，编号从 1 连续递增
- 时间戳格式固定 `At MM:SS.mmm`（如 `At 00:03.500`），毫秒三位补零
- 全片切点严格递增且 ≤ 总时长
- Seedance 的段终点 = 总时长基准；结尾淡出写 `... by MM:SS.mmm`

### 2.2 首镜零锚点策略

官方 base 规范：首镜不带时间戳。用户转换规范：`0-3s → At 00:00.000`。

**本 Skill 默认**：多镜时间轴转换时首镜句内补 `At 00:00.000` 零锚点——Seedance 输入每段都有显式起点，零锚点让源时间段与输出 Shot 一一对应、可溯源。单镜 I2VA 且无显式时间轴时遵循官方省略写法。两种均通过 validate_h3.py 校验，但全篇必须统一。

```
python scripts/convert_time.py "0-3s, 3-6s, 6-10s" --style h3            # 默认带零锚点
python scripts/convert_time.py "0-3s, 3-6s, 6-10s" --style h3 --strict-base   # 首镜省略
```

### 2.3 示例

```
输入:  0-3s | 3-6s | 6-10s        （总时长 10s）
输出:  [Shot 1] At 00:00.000 ...
       [Shot 2] At 00:03.000 ...
       [Shot 3] At 00:06.000 ...
       结尾: The frame fades to black by 00:10.000.
```

非整秒示例：`(0:00–0:01.8) (0:01.8–0:02.8) ... (0:13.5–0:15)` → `At 00:01.800` `At 00:02.800` ... `At 00:13.500`，总时长 15.00s。

---

## 3. Camera Language Mapping（摄影语言）

### 3.1 镜头术语对照表

写成自然英语句子：运动类型 + 幅度 + 速度（中等幅度/正常速度可省略）。

| Seedance 表述 | H3 表达 |
|--------------|--------|
| 推镜 / dolly in / push in | `The camera pushes in with small amplitude at slow speed toward ...` |
| 拉镜 / pull back / zoom out（机位后退用 Pull Out，焦距变化用 Zoom Out） | `The camera pulls out with small amplitude at slow speed.` |
| 摇镜（左右） / pan | `The camera pans right with large amplitude at fast speed, revealing ...` |
| 移镜（横移） / truck | `The camera trucks left ...` |
| 俯仰 / tilt | `The camera tilts up ...` |
| 升降 / crane / pedestal | `The camera pedestals down ...` |
| 环绕 / orbit / arc | `The camera arcs around her clockwise ...` |
| 跟拍 / follow / tracking | `A tracking shot follows him through the alley.` |
| 固定机位 / static / 固定中景 | `The camera holds a static shot as ...` |
| 手持 / handheld | `handheld recording with subtle natural sway` |
| 第一人称 / POV / 主观视角 | `first-person POV` + 具体视线高度与朝向 |
| 甩镜 / whip pan | `The camera whips right into the next framing.` |
| 航拍 / aerial / drone | `an aerial drone view high above ...` |

### 3.2 机位/构图参数（数值保留）

距离（`约1米` → `roughly 1 meter from the lens`）、画幅占比（`全身占画面70%` → `her full body fills roughly 70 percent of the vertical frame`）、机位高度、景深、焦段感（`26mm phone lens`）、颗粒（`high ISO grain`）——这些是构图参数不是人物外观，必须保留。

### 3.3 模糊风格词展开

`cinematic shot` / `电影感` 这类词禁止原样照搬，展开为具体维度：

```text
❌ cinematic shot, a lighthouse in a storm
✅ Live-action, cinematic, a low wide-angle shot frames a stone lighthouse on a wave-battered promontory;
   deep focus keeps spray sharp in the foreground; storm light breaks in cold blue shafts through cloud cover.
```

展开素材库：镜头景别（wide/medium/close/extreme close-up）、角度（low/high/eye-level/overhead）、焦段感（24mm wide / 35mm / 85mm portrait / telephoto compression）、景深（shallow/deep focus, rack focus）、光线（方向+质感+色温）、运动（上表）、质感（film grain, anamorphic flare, mild HDR）。

---

## 4. Audio Splitting（声音拆分）

### 4.1 判别树

```
声音元素
├─ 台词/歌词（人物发出）→ 正文 integrated_multimodal_description 内
│    <d>[Language] 原文</d>，说话人 (Sx)，首次出现给音色锚定
├─ 角色听不到的音乐（BGM/配乐/score）
│    → non_diegetic_music:（配器、速度、节奏、力度；禁抽象情绪词）
├─ 角色能听到的音乐（收音机/现场演奏/手机外放）
│    → diegetic 事件，写进正文对应 Shot
├─ 环境声/音效/动作声/呼吸笑声
│    → overall_soundscape:（1–4 句连续段落）
└─ 无声请求
     → 两个声音字段都写 N/A
```

### 4.2 常见映射

| Seedance | H3 去处 |
|----------|--------|
| `背景音乐：钢琴曲` | `non_diegetic_music: Sparse solo piano at a slow tempo ...` |
| `BGM：电子乐，节奏强` | `non_diegetic_music: A modern electronic track with strong punchy beats ...` |
| `音效：风声、车流` | `overall_soundscape: High-altitude wind sweeps across the rooftop while distant traffic hums below.` |
| `台词：“风好大啊！”` | `She (S1) says: <d>[Mandarin Chinese] 风好大啊！</d>` |
| `环境音：安静室内` | `overall_soundscape: Quiet indoor room tone continues throughout.` |

### 4.3 注意

- `overall_soundscape` 不重复正文已写的对白/歌声/diegetic 音乐
- 音色锚定句（`a bright unprocessed speaking voice recorded at close handheld-phone distance`）属音频特征，放正文说话人首次出现处，不算外貌泄漏
- 音乐节拍对齐动作时在 non_diegetic_music 里写明对应关系：`every major beat lands exactly where a finger gesture occurs`

---

## 5. Action Enhancement（动作增强）

### 5.1 触发条件

输入动作过于简单（`人物跳舞`、`人物跑步`、`人物战斗`、`蛙跳`），不足以支撑生成质量时扩展。

### 5.2 五个增强轴

| 轴 | 扩展内容 | 示例（跳舞） |
|----|---------|-------------|
| 身体动作逻辑 | 发力顺序、关节链、重心转移 | 重心下沉 → 髋部发力 → 肩部波浪跟随 |
| 镜头响应 | 相机如何配合动作 | 推近至腰部以上捕捉躯干律动 |
| 动作节奏 | 拍点、快慢、停顿 | 每个 strong beat 完成一次完整动作循环 |
| 视觉反馈 | 衣料、头发、道具的响应 | 衣摆随转身扬起，发丝扫过肩线 |
| 物理效果 | 地面反作用、惯性、落地缓冲 | 落地屈膝缓冲，地板轻微震动声 |

### 5.3 边界（不可逾越）

1. **不改变原始创意**——舞种、情绪、方向、结果由原文决定
2. **不新增情节**——不加原文没有的事件、人物、场景切换
3. **不触碰身份规则**——增强只落在表演层，永不描写固定外貌
4. **不改时间结构**——除非用户要求，不增减镜头数
5. **保持可执行性**——每个增强必须是模型可实现的可视可听细节

---

## 6. Mode Detection Summary

完整启发式由 `scripts/detect_mode.py` 实现，此处为人工速查：

| 证据 | 结论 |
|------|------|
| 无任何图片引用 | T2VA |
| 恰好一个图引用且作开场画面 | I2VA |
| 首帧+尾帧两张关键帧（`首尾帧`、`first frame ... last frame`） | FL2VA |
| 仅尾帧一张（`最后一帧`、`ending frame`） | L2VA |
| ≥2 张图定义不同主体（角色+场景/服装），或分镜网格 | Ref2VA |

优先级：用户明确指定 > FL2VA/L2VA 关键词 > 图引用计数 > 默认 T2VA。
