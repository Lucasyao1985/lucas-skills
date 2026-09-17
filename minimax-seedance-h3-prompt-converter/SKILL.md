---
name: minimax-seedance-h3-prompt-converter
description: Convert Seedance 2.0 / Seedance 2.5 / Seedance video prompts into production-ready MiniMax H3 prompts (T2VA, I2VA, FL2VA, L2VA, Ref2VA). Parses multi-shot timelines such as 0-3s and 3-6s blocks, delegates character identity to picture references instead of re-describing faces, hairstyles, or outfits, maps Seedance camera and audio language onto integrated_multimodal_description, overall_soundscape, and non_diegetic_music. Use when the user provides a Seedance prompt, 即梦提示词, Seedance 视频提示词, 多镜头时间轴提示词, 图片参考视频提示词, or asks to convert, rewrite, or adapt any Seedance prompt for MiniMax H3.
license: MIT
compatibility: Requires Python 3 (the three scripts in scripts/ use the standard library only). Runs on Claude.ai, Claude Code and the API. No network access needed.
metadata:
  version: 1.0.0
  author: Lucas
  source_model: Seedance 2.0 / Seedance 2.5
  target_model: MiniMax H3
  requires:
    bins:
      - python
---

# Seedance → MiniMax H3 Prompt Converter

将 Seedance 2.0 / Seedance 2.5 提示词转换为 MiniMax H3 标准格式。**只改变表达结构，不改变原始创意**：主体设定、场景设计、镜头语言、动作逻辑、时间轴、摄影参数、光线设计、氛围、声音设计全部保留。

## When to Use

触发条件：
- 用户给出 Seedance 2.0 / 2.5 / Seedance Video Prompt，要求转换或改写为 MiniMax H3 格式
- 输入包含图片引用标记（`@图1`、`<Picture 1>`、`@Image 1`）或多镜头时间轴（`0-3s`、`3-6s`、`(0:00–0:03)`）
- 用户说 "seedance 转 h3"、"转成 H3 格式"、"convert this seedance prompt"、"rewrite for minimax"
- 用户给出简单动作描述（"人物跳舞"）并要求输出可用的视频提示词

不适用：
- 没有 Seedance 输入、直接从零写 H3 提示词 → 改用 `minimax-h3-prompt-writing`
- 用户要生成/编辑视频文件本身

## Workflow

### Step 1 — 解析 Seedance 输入

通读输入，抽取九项创意要素并记录在案（后续逐步映射，不得丢失）：

| # | 要素 | Seedance 常见载体 |
|---|------|------------------|
| 1 | 主体设定 | `主体：` 字段、`@图N` 引用、人物名词 |
| 2 | 场景设计 | `场景：`、地点描写 |
| 3 | 镜头语言 | `镜头：`、推拉摇移跟、`cinematic shot` 等风格词 |
| 4 | 动作逻辑 | `动作：`、时间段内的行为描述 |
| 5 | 时间轴 | `0-3s`、`(0:00–0:01.8)`、分镜编号 |
| 6 | 摄影参数 | 焦段、画幅、景深、机位高度、胶片感等 |
| 7 | 光线设计 | `光线：`、逆光、霓虹、黄金时刻等 |
| 8 | 氛围 | `氛围：`、风格标签（电影感、赛博朋克…） |
| 9 | 声音设计 | `音效：`、`BGM：`、`台词：`、环境声 |

解析细则见 `references/seedance-patterns.md`。字段式与自然语言式都要覆盖；中文冒号 `：` 与英文冒号等价处理。

### Step 2 — 自动判断 MiniMax 模式

按下表自动选择模式；用户明确指定时以用户为准：

| 模式 | 判定条件 |
|------|---------|
| T2VA | 无任何图片引用，纯文字描述 |
| I2VA | 恰好一张图作为首帧/主角参考 |
| FL2VA | 首帧 + 尾帧两张关键帧（首尾帧、first/last frame） |
| L2VA | 仅一张尾帧参考 |
| Ref2VA | 多张图片定义角色/场景/服装，或分镜网格图（storyboard grid） |

可用脚本辅助判定：`python scripts/detect_mode.py input.txt --json`

### Step 3 — 人物身份一致性处理（CRITICAL）

只要输入含 `<Picture N>` / `@图N` 或用户声明上传了人物参考图：

**禁止重新描述人物外貌**——脸型、五官、发型、发色、肤色、身材比例、固定服装一律不写。

统一改为委托句：
- 真人：`The person shown in <Picture 1>` / `the young woman shown in <Picture 1>`
- 二次元：`The character shown in <Picture 1>`（动漫人物、游戏角色、插画角色、卡通角色同规则）

人物身份、外貌、服装、角色设计全部由图片决定。允许描述的只有表演层：动作、姿态、表情变化、视线、在画面中的位置与占比。

完整禁用词表、白名单句式、唯一例外协议（换装镜头）见 `references/mapping-rules.md` 第 1 节。

### Step 4 — 时间轴转换

Seedance 时间段 → H3 时间戳：

```
Seedance:   0-3s        3-6s        6-10s
H3:         At 00:00.000    At 00:03.000    At 00:06.000
```

规则：
- `[Shot N]` 分镜编号连续；每个 Seedance 时间段对应一个 Shot
- 时间戳格式严格为 `At MM:SS.mmm`；全片时间戳严格递增且不超过总时长
- 结尾淡出写 `... by MM:SS.mmm`
- 首镜零锚点策略与官方省略写法的取舍见 `references/mapping-rules.md` 第 2 节

批量换算用脚本：`python scripts/convert_time.py "0-3s, 3-6s, 6-10s" --style h3`

### Step 5 — 摄影语言与动作重建

- 把 Seedance 镜头术语映射为 H3 自然英语相机运动（运动类型 + 幅度 + 速度），如 推镜 → `The camera pushes in with small amplitude at slow speed`。完整对照表见 `references/mapping-rules.md` 第 3 节。
- 风格词展开：`cinematic shot` 等模糊词必须展开为具体镜头、构图、焦段、光线、焦点描述。
- 动作增强：对简单动作（跳舞/跑步/战斗/跳跃）沿五个轴扩展——身体动作逻辑、镜头响应、节奏、视觉反馈、物理效果。边界：不得新增情节、不得改动创意方向、不得触碰身份规则。见 `references/mapping-rules.md` 第 5 节。

### Step 6 — 声音拆分

| Seedance 来源 | H3 去处 |
|--------------|--------|
| 台词 / 歌词 | 正文内 `<d>[Language] ...</d>`，说话人标 `(S1)` `(S2)`，原文逐字保留不翻译 |
| 环境声 / 音效 / 动作声 | `overall_soundscape:`（1–4 句） |
| 背景音乐 BGM（角色听不到） | `non_diegetic_music:`（1–3 句，写配器、速度、律动，不写抽象情绪词） |
| 角色能听到的音乐（收音机、现场演奏） | 属 diegetic，写进正文 |

无声请求两个字段都写 `N/A`。判别树见 `references/mapping-rules.md` 第 4 节。

### Step 7 — 按模板组装输出

按 Step 2 判定的模式读取模板骨架，填充后成稿：

- T2VA → `templates/t2va-template.txt`
- I2VA → `templates/i2va-template.txt`（首行必须是 `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`）
- FL2VA → `templates/fl2va-template.txt`
- L2VA → `templates/l2va-template.txt`
- Ref2VA → `templates/ref2va-template.txt`（六段结构）

完整格式规范（字段顺序、分镜衔接动词、说话人规则、字数基准）：`references/h3-format-guide.md`

### Step 8 — 质量检查（输出前强制执行）

运行验证脚本：

```bash
python scripts/validate_h3.py output.txt --mode auto --duration 10
```

八道检查门，任何 ERROR 必须修复后再交付：

1. 四段结构完整且顺序正确（Ref2VA 为六段）
2. 首行对齐指令与模式匹配（T2VA 不得有对齐行）
3. 无人物重复描述——同一人物的身份委托只出现一次
4. 未破坏图片身份一致性——无禁用外貌词泄漏
5. 时间轴存在、格式正确、严格递增、不超时长
6. `overall_soundscape:` 与 `non_diegetic_music:` 齐全（无声用 N/A）
7. 无 Seedance 格式残留（`0-3s` 写法、`主体：` 字段、`@图1` 标记等）
8. 台词格式正确——`(Sx)` 编号 + `<d>[Language] ...</d>` 配对

检查项细节与修复方法见 `references/quality-checklist.md`。

### Step 9 — 交付

输出最终 Prompt（代码块包裹），附简要转换报告：检测到的模式、身份处理方式、时间轴映射表、声音拆分结果、所做的动作增强。报告模板：`templates/conversion-report.md`。

成品范例（按需逐个打开，不要一次全读）：

| 文件 | 演示 |
|------|------|
| `examples/example-01-i2va-rooftop.md` | 字段式 + `@图1` → I2VA |
| `examples/example-02-ref2va-anime.md` | 多图角色设定（二次元）→ Ref2VA |
| `examples/example-03-t2va-lighthouse.md` | 关键词堆叠 → T2VA（`cinematic shot` 模糊词展开） |
| `examples/example-04-fl2va-coffee.md` | 首尾帧 → FL2VA |

仓库级说明（安装、脚本用法、版本管理）见 `references/development-notes.md`；跨平台接口元数据见 `agents/openai.yaml`。

## Output Rules

- 正文用英文重写；台词、歌词、画面内可见文字保留原语言逐字不动
- 输出中不得出现任何中文字符（除 <d>[Chinese] ... </d> 台词标签内）
- 所有字段名（`integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music` 等）、`<Picture N>`、`[Shot N]`、`At MM:SS.mmm`、`(Sx)` 标记保持英文原样，永不翻译
- 不输出剧情梗概代替镜头描述；每个 Shot 都要有可视可听的细节
- 参考图角色存在时，正文中该角色的外貌词出现次数必须为零（委托句除外）

### 中文正文变体（仅当用户显式要求「中文版」时）

用户要求中文正文时，上述「正文用英文」规则让位于用户指令。**除正文叙述语言改为中文外，其余全部不变**，混合写法按此清单执行：

| 元素 | 中文版处理 |
|------|-----------|
| 首行对齐指令 | 保持英文逐字原文（Gate 2 逐字匹配，改中文即 FAIL） |
| 三个字段名 | 保持英文原样 |
| `<Picture N>` / `[Shot N]` / `At MM:SS.mmm` / `(Sx)` / `<d>[Language]` | 保持英文原样 |
| 画面内可见文字 | 保留原语言，用英文双引号包裹 |
| 身份委托句 | 必须内嵌英文锚点 `the character shown in <Picture 1>`（或 `the person shown in`），可在其后用中文补充说明 |

⚠️ **校验器限制**：`scripts/validate_h3.py` 的委托句正则 `(?:shown in|defined by)\s*<\s*Picture` 与禁用词表均为英文。中文正文会误报
`[identity] no standard identity delegation`；且中文外貌词无法被 `APPEARANCE_RE` 捕获，需人工核对身份规则。
→ 修复：委托句内嵌英文锚点（见上表），即可通过全部八门。

建议交付方式：`中英对照双份`——英文版直接投喂 H3，中文版便于阅读修改。

## Troubleshooting

| 症状 | 原因 | 处理 |
|------|------|------|
| validate 报 identity leak | 外貌词未委托给图片 | 定位泄漏词所在 Shot，改为 `shown in <Picture N>` 委托句或删除 |
| validate 报 timestamp error | 时间戳乱序/超时长/格式错 | 用 convert_time.py 重新换算全部切点 |
| validate 报 residue | Seedance 字段残留 | 删除中文字段标签，把内容并入对应英文段落 |
| 模式判定摇摆 | 输入同时含单图与网格描述 | 问用户图片实际用途；无法确认时默认 I2VA 并说明理由 |
| 简单动作扩不动 | 增强越界改了创意 | 回读五轴清单，只加身体/镜头/节奏/反馈/物理，不加情节 |

## Performance Notes

- 转换质量优先于速度：逐项核对九要素是否全部落位再交付
- 宁可向用户确认图片用途，也不要猜错模式后整篇返工
- 身份规则是硬约束：即使 Seedance 原文写了外貌，也要剥离并委托给图片
