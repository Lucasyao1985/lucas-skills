---
name: minimax-h3-character-replacement
description: '使用 MiniMax H3 将参考图片中的人物替换到参考视频中。输入参考图片（新人物身份）+ 参考视频（动作/运镜来源），自动生成 Ref2VA 完整提示词，确保人物身份完全来自图片、服装配饰来自图片、面部稳定不崩坏、肢体贴合原始动作。Trigger: "人物替换" "换脸视频" "face swap" "character replacement" "把图片人物放视频里" "reference character video"'
license: MIT
metadata:
  version: 1.0.0
  author: Lucas
  minimax_model: H3
  mode: Ref2VA
  requires:
    bins:
      - python
    os:
      - win32
      - darwin
      - linux
---

# MiniMax H3 Character Replacement Video Generator

使用 Ref2VA（Full-Reference Mode）将参考图片中的人物完整替换到参考视频中，保留原视频的运镜、动作、场景、构图。

## When to Use

触发条件：
- 用户提供参考图片 + 参考视频，要求"把图片人物放到视频里"
- 用户要求"人物替换"、"换脸视频"、"face swap"、"character replacement"
- 用户要求"保留原视频动作/运镜，替换人物身份"
- 用户说"把这张图片的人放到那段视频里"

## Input Requirements

| 输入 | 要求 | 说明 |
|------|------|------|
| `<Picture 1>` | 1 张人物参考图 | 锁定新人物的完整身份（脸、发型、发色、肤色、五官、身体外貌、服装、配饰） |
| `<Video 1>` | 1 段参考视频 | 提供运镜、肢体动作、场景环境、构图关系 |
| 用户描述 | 可选 | 补充动作细节、情绪、场景说明 |

## Workflow

### Step 1: 确认输入

从用户消息中提取：
- 参考图片路径 → `<Picture 1>`
- 参考视频路径 → `<Video 1>`
- 用户补充描述 → 记录为动作/情绪补充

### Step 2: 定义 subject_definitions

读取 `references/replacement-rules.md`，按照替换规则定义所有 reference labels：

```
<Subject 1> is the person in <Picture 1>, with [detailed identity description].
<Picture 1> is the character reference image for <Subject 1>, showing [what the image shows].
<Video 1> is the motion reference video providing [camera movement, action, scene].
```

关键约束：
- `<Subject 1>` 的身份描述必须**完整且详细**，覆盖：面部五官、脸型、发型、发色、肤色、身体外貌、服装、配饰、整体形象
- `<Video 1>` 的描述**不包含**原视频人物的脸、发型、身体外貌、服装、配饰

### Step 3: 写 summary

```
[reference generation] The target video replaces the original character in <Video 1> with <Subject 1> from <Picture 1>, preserving all camera movement, action, scene environment, and composition from <Video 1>.
```

### Step 4: 写 retention_analysis

按照 `references/replacement-rules.md` 中的保留规则：

```
<Subject 1> (appears in [Shot 1], fully_preserved): facial features, hairstyle, hair color, skin tone, body appearance, clothing, and accessories from <Picture 1> are fully preserved.
<Picture 1> ([Shot 1] identity anchor): fully_preserved - locks the complete identity of <Subject 1>.
<Video 1> (camera movement, action, scene, composition): fully_preserved - all camera movement, action choreography, scene environment, and composition are retained.
<Video 1> (original character): excluded - the original person's face, hairstyle, body appearance, clothing, and accessories are completely replaced by <Subject 1>.
```

### Step 5: 写 detailed_description

#### 5.1 风格声明

在 `[Shot 1]` 之前，用 1-2 句英文声明整体风格：

```
The target video matches the photographic style, lighting quality, color grading, and visual texture of <Video 1>.
```

#### 5.2 Shot 1 主体声明

```
[Shot 1] <Subject 1> (S1) appears in the exact pose, camera framing, and scene environment carried over from <Video 1>, with [brief action description from Video 1].
```

关键要求：
- 人物的服装必须**明确声明来自 `<Picture 1>`**
- 人物的面部/发型/配饰必须**明确声明来自 `<Picture 1>`**
- 动作必须**明确声明来自 `<Video 1>`**
- 场景/运镜必须**明确声明来自 `<Video 1>`**

#### 5.3 全段约束检查

写完后，对照 `references/replacement-rules.md` 中的"硬性约束清单"逐项检查，确保：
- 没有继承 `<Video 1>` 中人物的脸部特征
- 没有继承 `<Video 1>` 中人物的服装特征
- 没有继承 `<Video 1>` 中人物的配饰
- 服装颜色、材质、款式与 `<Picture 1>` 一致
- 面部全程稳定，不漂移、不变化、不崩坏
- 肢体贴合原始动作，自然匹配人物比例
- 画面风格、摄影质感、环境光照与原视频统一

### Step 6: 写 overall_soundscape

从 `<Video 1>` 提取环境音、动作音效、物理声音。如果用户没有提供音频信息，写 `N/A`。

### Step 7: 写 non_diegetic_music

从 `<Video 1>` 提取背景音乐信息。如果原视频无音乐，写 `N/A`。

## Hard Constraints（强制）

这些约束**必须在 detailed_description 中显式体现**，不能省略：

| # | 约束 | 检查方法 |
|---|------|----------|
| 1 | 人物身份完整来自 `<Picture 1>`（脸、发型、发色、肤色、五官、身体、服装、配饰） | retention_analysis 中 fully_preserved |
| 2 | `<Video 1>` 中人物的脸/发型/身体/服装/配饰完全不保留 | retention_analysis 中 excluded |
| 3 | 服装来自 `<Picture 1>`，不来自 `<Video 1>` | detailed_description 中显式声明 |
| 4 | 面部全程稳定，不漂移、不变化、不崩坏 | detailed_description 中声明 |
| 5 | 肢体贴合 `<Video 1>` 原始动作 | detailed_description 中声明 |
| 6 | 场景/运镜/构图完全来自 `<Video 1>` | retention_analysis 中 fully_preserved |
| 7 | 画面风格/摄影质感/光照与 `<Video 1>` 统一 | detailed_description 开头声明 |
| 8 | 无穿模、无身份混合、无错误肢体 | detailed_description 中声明 |

## Output Format

最终输出必须严格遵循 Ref2VA 六段式，按顺序：

```
subject_definitions:

summary:

retention_analysis:

detailed_description:

overall_soundscape:

non_diegetic_music:
```

## References

- `references/replacement-rules.md` — 人物替换完整约束清单、label 定义规则、检查清单
- `references/ref-en.txt` — Ref2VA 六段式标准格式（subject_definitions → non_diegetic_music）

## Examples

**Example 1: 基本人物替换**

用户说："把这张图片的人放到这段视频里"

1. 提取 `<Picture 1>` = 用户提供的图片
2. 提取 `<Video 1>` = 用户提供的视频
3. 按照本 skill 的 workflow 生成完整 Ref2VA 提示词
4. 确保 detailed_description 中显式声明所有硬性约束
