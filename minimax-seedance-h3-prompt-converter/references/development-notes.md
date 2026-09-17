# minimax-seedance-h3-prompt-converter

> Seedance 2.0 / 2.5 提示词 → MiniMax H3 标准格式 专业转换器（Claude Code Skill）

把 Seedance 提示词无损转换为 MiniMax H3 视频生成格式：**只改变表达结构，不改变原始创意**。

```text
Seedance 输入                          MiniMax H3 输出
─────────────────                      ─────────────────
@图1 女生站在城市天台…                  For the target video, at 0.00 seconds into the
0-3s 固定中景，她背对镜头                target video, <Picture 1> (from [Shot 1]) is fully referenced.
3-6s 推镜至近景，她说："风好大啊！"
6-10s 环绕半圈…                        integrated_multimodal_description: [Shot 1] Live-action,
BGM：轻柔钢琴曲                           cinematic, the young woman shown in <Picture 1> ...
音效：高空风声                          ... [Shot 2] At 00:03.000, the camera pushes in ...
                                   　  ... [Shot 3] At 00:06.000, the camera arcs ...

                                       overall_soundscape: High-altitude wind sweeps ...
                                       non_diegetic_music: Sparse soft piano notes ...
```

## 核心能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | 创意保真 | 九要素逐项落位：主体、场景、镜头语言、动作逻辑、时间轴、摄影参数、光线、氛围、声音 |
| 2 | 结构转换 | 自动生成 `[Shot N]` 分镜 + `At MM:SS.mmm` 时间轴 + 四段/六段字段结构 |
| 3 | 身份一致性 | 图片角色零外貌重述——真人/二次元统一委托 `the person/character shown in <Picture N>` |
| 4 | 模式自动判定 | T2VA / I2VA / FL2VA / L2VA / Ref2VA 按输入特征自动选择 |
| 5 | 动作增强 | 简单动作沿五轴扩展（身体逻辑/镜头响应/节奏/视觉反馈/物理），不越创意边界 |
| 6 | 摄影语言映射 | 推拉摇移跟 → H3 运动类型+幅度+速度自然英语；`cinematic shot` 展开为具体镜头描述 |
| 7 | 音频严格拆分 | diegetic（环境/音效→overall_soundscape）与 non-diegetic（BGM→non_diegetic_music）分流 |
| 8 | 质量门禁 | 八道检查门 + 可执行验证脚本，Seedance 残留清零后才交付 |

## 安装

```bash
# 已就位于 Claude Code 技能目录：
C:\Users\Lucas\.claude\skills\minimax-seedance-h3-prompt-converter
```

## 使用

在 Claude Code 中：

```
/minimax-seedance-h3-prompt-converter 把这段 Seedance 提示词转成 H3：<粘贴提示词>
```

或自然语言触发："把这个 Seedance prompt 转成 MiniMax H3 格式"、"seedance 转 h3"。

### 脚本工具（独立可用）

```bash
# 时间轴换算：0-3s/3-6s/6-10s → H3 时间戳
python scripts/convert_time.py "0-3s, 3-6s, 6-10s" --style h3
python scripts/convert_time.py "(0:00-0:01.8), 第1.8秒到2.8秒" --strict-base   # 首镜省略写法

# 模式检测
python scripts/detect_mode.py input.txt --json

# 输出八门验证（交付前强制）
python scripts/validate_h3.py output.txt --mode auto --duration 10 --json
```

## 目录结构

```
minimax-seedance-h3-prompt-converter/
├── SKILL.md                     # 核心工作流（渐进式披露第二层：frontmatter 触发后加载）
├── agents/openai.yaml           # 跨平台接口元数据
├── references/
│   ├── h3-format-guide.md       # H3 目标格式规范（五模式/首行指令/相机词汇/说话人规则）
│   ├── seedance-patterns.md     # Seedance 输入解析指南（六种风格/九要素/残留标记）
│   ├── mapping-rules.md         # 转换核心规则库（身份/时间轴/摄影/声音/动作增强/模式判定）
│   ├── quality-checklist.md     # 八道质量检查门 + 修复方法
│   └── development-notes.md     # 本文件（仓库级文档）
├── templates/
│   ├── t2va-template.txt        # 各模式输出骨架
│   ├── i2va-template.txt
│   ├── fl2va-template.txt
│   ├── l2va-template.txt
│   ├── ref2va-template.txt      # 六段结构骨架
│   └── conversion-report.md     # 交付用转换报告模板
├── examples/
│   ├── example-01-i2va-rooftop.md    # 字段式+@图1 → I2VA
│   ├── example-02-ref2va-anime.md    # 多图角色设定(二次元) → Ref2VA
│   ├── example-03-t2va-lighthouse.md # 关键词堆叠 → T2VA（模糊词展开）
│   └── example-04-fl2va-coffee.md    # 首尾帧 → FL2VA
└── scripts/
    ├── convert_time.py          # Seedance 时间段 → H3 时间戳（确定性）
    ├── detect_mode.py           # 模式启发式判定
    └── validate_h3.py           # 八道质量门验证器（exit code 可集成 CI）
```

## 设计原则

- **渐进式披露**：frontmatter 触发词 → SKILL.md 工作流 → references 深层规范，按需加载省 token
- **确定性优于语言约束**：时间换算、模式判定、质量验证全部脚本化（代码不会误解规则）
- **硬约束前置**：身份一致性规则在任何步骤都不可绕过；即使 Seedance 原文写了外貌也要剥离委托给图
- **可溯源**：默认零锚点策略让每个 Seedance 时间段与输出 Shot 一一对应

## 与 minimax-h3-prompt-writing 的关系

`minimax-h3-prompt-writing` 是 H3 格式的**编写**技能（从零写）；本 Skill 是 **转换**技能（以 Seedance 提示词为源）。两者共享同一套 H3 格式底层规范（见 `references/h3-format-guide.md` 的提炼来源），但本 Skill 额外内置 Seedance 解析、身份委托协议、动作增强边界与残留清洗。没有 Seedance 源文本时请直接使用前者。

## 版本管理

- 主仓库：本目录内 git 仓库
- 备份同步：`F:\新建文件夹 (4)\skills\skills\`
- License: MIT · Author: Lucas · Version: 1.0.0
