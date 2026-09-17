# 替换/编辑类模板（角色替换、字幕替换、局部编辑、风格替换）

适用：以一段完整视频为底板做编辑。核心纪律一句话：**先立保留契约，再写替换契约；替换的是外观，转移的是行为。**

## 1. 编辑保全句（置顶，逐字保留）

所有编辑类提示词开头强制：

```
@视频1 是待编辑源视频。严格保持 @视频1 的镜头运动、构图、主体动作时序、
空间关系、遮挡关系、景深、光照方向、帧率和整体节奏不变。
只修改以下内容：…
```

## 2. 替换四条规则

1. **点名**：确切的旧对象 ↔ 确切的新对象（"所有'奶龙'外观全部替换为参考图角色"）。
2. **位置与时机**：说明旧对象出现在哪、何时变化。
3. **行为转移**：保留原运动路径、出现倍数、遮挡次序、阴影、反射、接触与交互关系，全部转移给新对象。
4. **未编辑区不变**：未编辑的主体与区域逐项声明保持不变。

## 3. 角色替换生成器骨架（家族B六段式 + 两个附加段）

完整输出结构（顺序固定）：

```
<Subject 1> 段 → Video 1 段 → summary: → retention_analysis: →
detailed_description:（含 [EXTENDED ENDING] 与 [TEXT REPLACEMENT]）→
overall_soundscape: → non_diegetic_music:
```

### 3.1 `<Subject 1>` 身份段

```
<Subject 1> is the replacement character shown in Image 1. Its visible identity
comes exclusively from Image 1, including its {图片1特征逐项，8-12项，英文}, and all
other identifying features. Image 1 is the source asset for <Subject 1>, not a
keyframe. Image 1 itself must never appear in the target video as a visible frame,
still image, or closing shot.
```

身份规则：
- 特征全部来自**当前**参考图，零预设、零历史沿用；无法判断的不写。
- 视觉类型与材质严格保持（毛绒/硬塑料/动漫/3D/写实），材质贯穿正文三处：**接触重建、光影反应、落地声**。
- 可识别角色（动漫/游戏/名人或其真人 cosplay）用公认名称锚定身份（如 `a real-life Sukuna cosplayer`），无法识别才退纯外貌描述。

### 3.2 summary 段

```
summary:
[video editing + reference generation + text replacement] The target video is an
edited version of Video 1. Wherever the original character ({原名}) is visible,
replace its appearance with <Subject 1> derived from Image 1 — {一句角色概要}.
The original character's appearance, geometry, material, colour, logos, and
identifying features are discarded. Additionally, the subtitle is replaced with
"{字幕}" — same position, same style, same timing. Video 1 supplies the source
plate, camera, timing, choreography, environment, non-target content, and
original audible content.
```

### 3.3 retention_analysis 段（三态声明）

```
Video 1 (source plate): partially_preserved — 保留运镜/构图/时序/剪辑/环境/光照/
  非目标角色与物件/互动编排/遮挡时机/运动路径；不保留原角色的可见身份。
<Subject 1>: fully_preserved — 特征紧凑复述 5-8 项 + all surface detail。
```

### 3.4 detailed_description 段（八个必写块）

```
[Shot 1] ①替换声明：凡原角色出现处，外观全部来自 <Subject 1>，原角色可见身份
        （形状/几何/材质/配色/logo/标志细节）完全丢弃。
        ②行为转移：<Subject 1> 遵循被替换角色的可观察行为——屏幕空间路径、
        出入场时机、缩放、旋转、速度、停顿、加速、落定。
        ③多副本克隆：若原角色以群体涌出，同倍数应用于 <Subject 1>——
        dozens to hundreds of identical {复数指称} pour from …, tumbling, …,
        …, and swarming toward the camera.（翻滚动词恰 3 个，首词固定 tumbling）
        ④接触重建：所有接触按 <Subject 1> 实际几何重写（四肢抓握/足部触地/
        软性部件形变/接触阴影）；遮挡次序与时机与源一致。
        ⑤光影重建：以 Video 1 为光照参照——保留主光方向、强度、衰减、环境光、
        白平衡，允许 <Subject 1> 的真实材质决定漫反射与高光；重建受影响投影。
        ⑥镜头匹配：匹配源镜头的景别/FOV/焦平面/景深/运动模糊/噪声结构；
        <Subject 1> 与源角色同焦深，无 halo、无边缘错位、无合成痕迹。
        ⑦非目标内容不变：机位/环境/其他人物/物件/光照连续性/剪辑节奏全保留；
        每个源切点保持原时序，不新增切点；跨切点身份稳定。
[EXTENDED ENDING] ⑧延伸段：Video 1 约 {底板时长} 秒，目标视频约 {目标时长} 秒。
        超出底板末帧的部分，<Subject 1> 在同一街景/场景内继续涌出与翻滚，
        字幕仍在屏，视频必须结束于这段运动画面——never on a still photograph,
        a studio background, or any frame resembling Image 1.
[TEXT REPLACEMENT] 字幕替换为"{字幕}"：同底部居中位置、同白色粗体黑描边、
        同逐字显现时序；只改字符串，排版属性（字号/字重/颜色/描边宽度/位置/
        动画时序/时长）全部继承；字幕持续到最后一帧。
```

### 3.5 声音两段

```
overall_soundscape: 保留源视频环境声、对白、物理声，除非被替换几何改变物理声音；
  依材质分别重建：{人体/角色撞击声} + 至少两种 {衣物/配饰动态声}，不得笼统合并。
non_diegetic_music: Preserve the non-diegetic music from Video 1 unchanged if
  present. If Video 1 contains no non-diegetic music, use N/A.
```

### 3.6 角色替换专用负向词（只打保全失败点）

```
no identity drift, no original character remnants, no face distortion,
no morphing between copies, no halo or edge mismatch around the replacement,
no missing copies, no extra characters beyond the source plate,
no subtitle garbling, no style change to the plate, no watermark
```

## 4. 字幕替换模板（独立任务，无角色替换时）

```
@视频1 是待编辑源视频。严格保持镜头运动、构图、动作时序、遮挡、景深、光照方向、
帧率与整体节奏不变。只修改字幕：
新字幕逐字使用"{字幕}"原文，不改写、不增删、不加装饰、不乱码；
非拉丁字符（汉字简繁、假名变体、韩文等）保持原样；
排版完全继承源视频（位置/字体/字号/颜色/描边/显现时序）；
只改字符串不改排版属性，字幕持续到最后一帧。
```

## 5. 局部编辑 / 插入道具模板（mime-object 范式）

四段式 brief：

```
① 源不变量：演员/脸/服装/场景/光/相机/时序/节奏逐项列出。
② 插入物规格：出现部位、握持方式、尺度与透视、材质。
③ 交互重建：接触点、遮挡关系、运动跟踪、投影落地。
④ 生成前可行性校验：部位可见时长够吗？物理适配吗？动作矛盾吗？
```

负向词只写真矛盾（不换演员/不改场景/道具不悬浮/不穿模），不做负向堆砌。先出视觉编辑，原音频回混在后。

## 6. 风格替换模板（保时间线换视觉，co-op 范式）

```
保留：时间线、事件顺序、主体位置、交互逻辑、文字结构、镜头语言。
重写：视觉处理五处——配色（2-3 主色）、材质、字形气质、道具空间处理、
     动效触发后的视觉结果。
负向：no identity swapping, no layout drift, no event reordering,
     no body proportion drift, no missing {关键元素}。
```

风格扩展库（每个风格一条可整段附录的风格语言包）见 style-anchor-video.md。

## 7. 编辑类生成器的硬性规则（写进生成器设定第六段）

1. 只输出英文提示词正文，无标题/头部/元信息，不解释。
2. 段落齐全且顺序固定，不得增删段落。
3. 骨架固定句逐字保留；槽位全部替换，输出不得残留占位符或〔〕中文指令。
4. `<Subject 1>` 特征全部来自当前图片，零预设零历史。
5. 原角色外观全部丢弃；行为路径、倍数、遮挡、节奏全部保留并转移。
6. 字幕逐字一致、排版全继承、持续到最后一帧。
7. 材质以参考图为准，贯穿接触/光影/声音三处，逐材质描述。
8. 缺参考图或缺必填变量则不生成，直接说明缺少的输入项。
