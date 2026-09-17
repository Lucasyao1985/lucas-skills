# 风格锚定与门禁（视频版）

## 1. 风格特征化（不写风格名词，写可见可听特征）

"国风/复古/高级感/赛博"模型不认识。用 AD_HOC_STYLE_SUMMARY 七行把抽象风格翻译成可执行锚点：

```
user_style_exact:    用户原话（保留）
template_style:      对齐的模板骨架（结构不动）
visual_traits:       3-5 条可见视觉特征（线条/上色/材质/构图）
motion_traits:       2-3 条运动特征（什么在动、怎么动、多快）
title_traits:        文字气质（字重/端点/材质/颜色）
audio_traits:        2-3 条可听特征（配器/质感/空间感）
avoid:               2-3 条禁入特征（防漂移方向）
```

示例（"国风"展开）：visual_traits = 细密墨线勾勒 + 矿物颜料高饱和平涂 + 缠枝纹与飞檐剪影；motion_traits = 衣袖弧线匀速摆动 + 粒子如金粉沉降；audio_traits = 古筝泛音 + 笛声长尾；avoid = 写实皮肤质感 + 镜头光晕。

## 2. 风格扩展库范式（C2 条目结构）

生成器设定里建"风格库"，每个风格一条**逐字附录段**（模型按变量选择后整段 verbatim 嵌入正文）：

```
C2-N — 风格名:
"〔风格语言完整段，60-120 词：媒介+线条+上色+纹样母题+色板+地面/底色〕"
```

实例（丝网插画六风格库之一）：

```
C2-2 — European Court Banquet:
"Rococo decorative illustration language, Ligne Claire uniform fine black
linework, court miniature aesthetic, high-density acanthus leaf, golden rose
filigree, and Baroque gilded relief patterns, jewel palette of Royal Prussian
blue, burgundy wine red, and antique Baroque gold"
```

规则：附录段**逐字嵌入正文**，禁止改写或部分引用；正文风格段 = 库条目 + 主体变量，两段拼接处自然衔接。

## 3. 2D 风格防漂移三锚（逐字硬编码进正文开头）

2D 扁平/插画风格视频，正文 `[Shot 1]` 后三个锚句逐字出现：

```
① 2D decorative illustration
② Stylized decorative movement only; each frame reads as a silkscreen illustration panel
③ decorative flat composition with no cinematic perspective distortion
```

## 4. 门禁检查表范式（GATE 结构）

生成器设定里写编号门禁，输出前静默自检（不合规则内部重写，不向用户暴露过程）：

```
GATE 1 首行声明：第一行是对齐句/锚定句，逐字正确
GATE 2 结构标记：[Shot 1] 开头 + 单空格
GATE 3 风格三锚：三个 2D 锚句逐字在场
GATE 4 身份具体化：禁泛称（"a beautiful woman"）；发型/眼型/五官逐项锚定；
       全程正面与四分之三侧脸之间，禁 90° 纯侧脸与背身
GATE 5 模板选择：按主体状态选对动作链模板（坐/卧→A，站立→B，特写→C）
GATE 6 场景密度：前景标志物 + 中景触觉交互 + 背景建筑三层齐全
GATE 7 动作链顺序：模板动词链按序展开，无重复
GATE 8 禁忌动作：无背身/纯侧脸/Z轴纵深走/张嘴形变/冻结循环
```

布尔派单锁（成片级项目）：`scope/design/proposal_confirmed=true, camera_plan_complete=true, TRAILER_FLOW_STATE=ready_to_dispatch` —— 任一为假禁止生成。

## 5. 逐字复述机制

- **文字清单唯一真源**：每个精确字符串全篇只出现一次、加引号、同拼写/大小写/标点/空格；`除清单文字外，不出现任何其他可读文字。`
- **锚点提取**：文字素材（logo/标语）从参考图逐字提取 brand_name/slogan/首字符/末字符，禁用常识补全。
- **特征紧凑复述**：正文多处引用身份时，复述 5-8 项最具辨识度特征，不重复全文。
- **署名角色不虚构**：缺署名/缺角色信息时不许占位，也不许写空白标签。

## 6. 统一风格锚逐字复用（多镜/分段项目）

全片每条提示词开头重复同一段风格锚（≤80 词），分镜临时元素（黑白草稿/宫格图）只继承结构不继承风格。主角漂移时**提高锁定优先级**（增加锚点细节、绑定独立变换后参考图），而不是加风格词。

## 7. 终帧锁（图锚类视频）

```
single continuous shot, no cuts, no transitions.
the final frame must be a 1:1 restoration of the reference image
（背景/配色/全部文字/比例逐项复原）
```

适用：海报动效、logo 动效、版面动画化。禁用工具级尾帧参数，尾帧锁定必须写进 prompt 正文。
