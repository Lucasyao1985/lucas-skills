# Output Quality Checklist（输出质量检查）

生成最终 Prompt 前逐项过检。`python scripts/validate_h3.py output.txt --mode auto --duration N` 覆盖其中可程序化判定的部分；其余人工核对。

## Gate 1 — 结构完整性

- [ ] 基础模式：`integrated_multimodal_description:` → `overall_soundscape:` → `non_diegetic_music:` 三段齐全、顺序正确
- [ ] Ref2VA：`subject_definitions:` → `summary:` → `retention_analysis:` → `detailed_description:` → 两个声音字段，六段齐全
- [ ] 字段名拼写逐字符正确，冒号为英文半角

**失败修复**：对照 `templates/` 对应模板重排段落顺序。

## Gate 2 — 首行对齐指令

- [ ] I2VA 首行 = `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- [ ] FL2VA/L2VA 首行含正确的 Picture 编号与秒数标记；FL2VA 的尾帧秒数 = 总时长
- [ ] T2VA / Ref2VA 无对齐行
- [ ] 对齐行后空一行再进字段

**失败修复**：从 `references/h3-format-guide.md` 第 2 节复制原文，只替换编号与秒数。

## Gate 3 — 人物重复描述

- [ ] 同一角色的身份委托句全篇只出现一次
- [ ] 后续镜头用 `the same woman/man/character` 回指
- [ ] 没有把委托句在多个 Shot 里整段复读

**失败修复**：保留首次出现处的完整委托，其余替换为回指短语。

## Gate 4 — 图片身份一致性

- [ ] `<Picture N>` 存在时，禁用词表（脸型/五官/发型发色/肤色/身材/固定服装）零命中
- [ ] 委托句使用标准形式 `the person/character shown in <Picture N>`
- [ ] 换装例外已按协议标注"唯一换装"并向用户提示风险

**失败修复**：定位泄漏词 → 删除或改写为表演层描述 → 身份归图片。

## Gate 5 — 时间轴

- [ ] `[Shot N]` 从 1 连续编号，无跳号
- [ ] 时间戳格式 `At MM:SS.mmm`（毫秒三位）
- [ ] 全片切点严格递增且 ≤ 总时长
- [ ] Seedance 每个时间段都有对应 Shot，无遗漏无合并（用户要求合并除外）
- [ ] 结尾淡出写 `by MM:SS.mmm`

**失败修复**：`python scripts/convert_time.py "原时间段列表" --style h3` 重算全部切点。

## Gate 6 — 声音字段

- [ ] 两个字段都存在且非空（全程静音时均写 `N/A`）
- [ ] `overall_soundscape` 为 1–4 句连续英文段落，不含对白/歌曲
- [ ] `non_diegetic_music` 为 1–3 句，写配器/速度/律动，无抽象情绪词
- [ ] 角色可闻的音乐已移入正文（diegetic）

**失败修复**：按 `references/mapping-rules.md` 第 4 节判别树重新归类。

## Gate 7 — Seedance 残留清零

- [ ] 无 `0-3s` 式时间段写法
- [ ] 无 `主体：/场景：/动作：/镜头：/运镜：/光线：/氛围：/音效：/BGM：/台词：/时长：` 字段标签
- [ ] 无 `@图1`、`<图片1>`、`@Image 1` 原始引用（应已转 `<Picture N>` 或 Subject 定义）
- [ ] 无 storyboard grid / 宫格 / panels 版式指令残留

**失败修复**：删除标签行，内容并入对应英文段落后删除原行。

## Gate 8 — 台词与说话人格式

- [ ] 每段台词包裹于 `<d>[Language] ...</d>`，语言标签如实标注
- [ ] 台词原文逐字保留（不翻译、不改写、不增删标点以外的内容）
- [ ] 出声者带 `(Sx)` 稳定 ID，同一人全程同号；首次出现有音色锚定
- [ ] `<d>` 标签开闭配对完整

**失败修复**：对照 `references/h3-format-guide.md` 第 7 节示例重写该句。

---

## Final Human Pass（脚本测不出的三项）

1. **创意保真**：Seedance 九要素是否全部落位？有没有悄悄丢掉光线设计或摄影参数？
2. **增强越界**：动作增强是否引入了原文没有的情节？
3. **整体语感**：相机运动是自然英语句子还是标签堆叠？读起来像不像一条可执行的拍摄指令？
