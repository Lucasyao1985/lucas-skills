---
name: h3-prompt-formatter
description: Format MiniMax H3 video generation prompts into a unified structure with 【原始输入】(original input) and 【生成结果】(generated output). Use when the user provides raw text content (tweet, request, character description) and wants it organized into a standardized format with image mapping, dialogue summary, and shot structure. Triggers on "整理格式", "统一格式", "format prompt", "原始输入+生成结果", or when the user provides raw content that needs to be structured into the standard H3 prompt file format.
license: MIT
metadata:
  version: 1.0.0
  author: Lucas
  target_model: MiniMax H3
---

# H3 Prompt Formatter

将原始文本内容整理为 MiniMax H3 提示词的标准统一格式。**只改变表达结构，不改变原始创意**。

## When to Use

触发条件：
- 用户给出原始文本内容（推文、需求、角色描述），要求整理为规范格式
- 用户说 "整理格式"、"统一格式"、"format prompt"、"原始输入+生成结果"
- 用户提供散乱的提示词内容，需要按统一结构重新组织
- 用户要求将多个版本的提示词合并为一个规范文件

不适用：
- 用户要从零写 H3 提示词 → 改用 `minimax-h3-prompt-writing`
- 用户要转换 Seedance 格式 → 改用 `minimax-seedance-h3-prompt-converter`
- 用户要下载视频 → 改用 `x-video-downloader`

## Unified File Format

所有输出文件必须遵循以下统一格式：

```
{Mode} 提示词 - {Theme}
{Equals Line}

【原始输入】
账号：{Account}
角色：{Character}
推文内容：{Tweet/Source Content}
需求：{Requirements}
主题建议：{Theme Suggestion}（如有）

---

【生成结果】
主题名：{Theme Name}
时长：{Duration}
格式：MiniMax H3 {Mode}
版本：{Version}

---

{Complete H3 Prompt Content}

---

图片映射：
- Picture 1：{Description}
- Picture 2：{Description}

台词汇总：
1. "{Dialogue}" — {Speaker}，{Language}，{Tone}

镜头结构：
- Shot 1（{TimeRange}）：{Description}
- Shot 2（{TimeRange}）：{Description}
```

## Workflow

### Step 1 — 解析原始输入

从用户提供的内容中提取以下要素：

| # | 要素 | 来源 |
|---|------|------|
| 1 | 账号 | @username、推文作者 |
| 2 | 角色 | 人物描述、Cosplay 角色 |
| 3 | 推文内容 | 原始推文文本 |
| 4 | 需求 | 模式（T2VA/I2VA/FL2VA/L2VA/Ref2VA）、时长、特殊要求 |
| 5 | 参考图 | 上传的图片、图片描述 |
| 6 | 台词 | 推文中的对话、台词内容 |
| 7 | 版本 | 用户指定的版本（纯委托/外貌描述等） |

### Step 2 — 自动判断模式

| 模式 | 判定条件 |
|------|---------|
| T2VA | 无任何图片引用，纯文字描述 |
| I2VA | 恰好一张图作为首帧/主角参考 |
| FL2VA | 首帧 + 尾帧两张关键帧 |
| L2VA | 仅一张尾帧参考 |
| Ref2VA | 多张图片定义角色/场景/服装 |

### Step 3 — 人物身份一致性处理（CRITICAL）

只要输入含 `<Picture N>` 或用户声明上传了人物参考图：

**禁止重新描述人物外貌**——脸型、五官、发型、发色、肤色、身材比例、固定服装一律不写。

统一改为委托句：
- 真人：`The person shown in <Picture 1>` / `the young woman shown in <Picture 1>`
- 二次元：`The character shown in <Picture 1>`

人物身份、外貌、服装、角色设计全部由图片决定。

### Step 4 — 组装【原始输入】区块

格式：
```
【原始输入】
账号：{Account}
角色：{Character Description - 不泄露外貌，只写角色类型}
推文内容：{Raw Tweet/Source Content}
需求：{Mode} 模式，{Duration}，{Special Requirements}
主题建议：{Theme Suggestion}（如有）
```

规则：
- 推文内容逐字保留，不翻译、不改写
- 角色描述不泄露外貌，只写角色类型（如"银发精灵 Cosplay"、"女骑士"）
- 需求部分包含模式、时长、特殊要求

### Step 5 — 组装【生成结果】区块

格式：
```
【生成结果】
主题名：{Theme Name}
时长：{Duration}
格式：MiniMax H3 {Mode}
版本：{Version - 纯委托/标准等}
```

规则：
- 主题名简洁有力（如"萌化协议"、"比心互动"）
- 时长精确到秒
- 版本标注是否为纯委托（正文零外貌词）

### Step 6 — 插入完整提示词

将原始提示词内容插入【生成结果】下方，保持原始格式不变。

规则：
- 保留所有 H3 标准字段（subject_definitions、summary、retention_analysis、detailed_description、overall_soundscape、non_diegetic_music）
- 保留所有 `<Picture N>`、`[Shot N]`、`At MM:SS.mmm`、`(Sx)` 标记
- 保留所有 `<d>[Language] ...</d>` 台词标签

### Step 7 — 组装图片映射

格式：
```
图片映射：
- Picture 1：{Description}
- Picture 2：{Description}
```

规则：
- 按 Picture 编号顺序列出
- 描述简洁，不泄露外貌（如"上传的 cos 角色参考图"、"浓雾草原场景"）
- 如有 Picture 无对应图片，标注"无"

### Step 8 — 组装台词汇总

格式：
```
台词汇总：
1. "{Dialogue}" — {Speaker}，{Language}，{Tone}
```

规则：
- 逐字保留原始台词（不翻译）
- 标注说话人、语言、语气
- 如无台词，标注"无台词（纯动作+音效）"

### Step 9 — 组装镜头结构

格式：
```
镜头结构：
- Shot 1（{TimeRange}）：{Description}
- Shot 2（{TimeRange}）：{Description}
```

规则：
- 按时间顺序列出
- 标注时间段和核心动作
- 如为单镜头，标注整体时间段

### Step 10 — 质量检查（输出前强制执行）

八道检查门，任何问题必须修复后再交付：

1. 【原始输入】区块完整（账号、角色、推文内容、需求）
2. 【生成结果】区块完整（主题名、时长、格式、版本）
3. 提示词内容完整（所有 H3 字段齐全）
4. 图片映射完整（所有 Picture 编号都有描述）
5. 台词汇总完整（所有 `<d>` 标签都有对应条目）
6. 镜头结构完整（所有 `[Shot N]` 都有对应条目）
7. 无外貌泄露（正文中外貌词出现次数为零，委托句除外）
8. 文件命名符合 `{Mode}_{Description}_{Duration}.txt` 格式

## Output Rules

- 正文用英文；台词、歌词保留原语言逐字不动
- 输出中不得出现任何中文字符（除 `<d>[Chinese] ... </d>` 台词标签内）
- 所有字段名保持英文原样，永不翻译
- 不输出剧情梗概代替镜头描述
- 参考图角色存在时，正文中该角色的外貌词出现次数必须为零（委托句除外）
- 文件命名统一为 `{Mode}_{Description}_{Duration}.txt`
- 文件夹命名统一为 `{Mode}_{Description}_{Duration}/`

## Troubleshooting

| 症状 | 原因 | 处理 |
|------|------|------|
| 原始输入区块不完整 | 部分要素未提取 | 重新扫描原始内容，补全缺失字段 |
| 外貌词泄露 | 正文中重写了人物外貌 | 定位泄漏词，改为 `shown in <Picture N>` 委托句或删除 |
| 台词格式错误 | 缺少 `<d>` 标签或 `(Sx)` 编号 | 补全标签和编号 |
| 镜头结构不完整 | 部分 Shot 未列出 | 扫描正文所有 `[Shot N]`，补全条目 |
| 文件命名不符合规范 | 未按统一格式命名 | 重命名为 `{Mode}_{Description}_{Duration}.txt` |
