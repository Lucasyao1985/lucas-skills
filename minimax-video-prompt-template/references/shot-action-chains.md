# 单镜动作链、运镜与表演设计

## 1. 单镜八段骨架

```
① 参数声明 → ② 对齐首行 → ③ 风格特征句 → ④ 主体身份锚点 + 起始状态
⑤ 动作链（First… Then… Mid-sequence… The action resolves as…）
⑥ 运镜声明（一个主运镜 + 速度 + 幅度）
⑦ overall_soundscape → ⑧ non_diegetic_music + Negative prompt
```

常用固定句：`The sequence unfolds as a single continuous 8-second shot rendered as a moving decorative print.` / 收束：`The continuous action resolves as {主体} halts …, holding the final balanced frame.`

## 2. 动作链四拍（每镜必齐）

```
开始(蓄力) → 发展(发力轨迹) → 收束(到位定格) → 承接(交给下一镜/收在静止)
```

因果节拍六件套（信息密度高的镜头逐拍展开）：
`触发 → 主响应 → 次响应 → 相机响应 → 过渡桥 → 落定`

推进判定：每段必须新增信息（新行动/证据/阻碍/关系/尺度/悬念）；**只换景别、走路、看奇观不算推进**。

## 3. 运镜速查

| 类别 | 词表 |
|---|---|
| 推拉 | push-in, pull-back, dolly in/out |
| 横移 | lateral tracking, truck left/right |
| 环绕 | orbit 180°, arc around the subject |
| 升降 | crane up/down, pedestal |
| 手持 | handheld shake, breathing camera |
| 特殊 | FPV dive, whip pan, dutch-shift, top-down follow |

- 速度曲线 8 词：`linear / ease-in / ease-out / ease-in-out / burst-stop / stop-burst / peak-mid / impact-freeze`
- 常用幅度+速度组合：`with small amplitude at slow speed` / `high-speed camera passes through`
- **一镜只给一个主运镜**；多运镜 = 摇摆 = 画面失控。
- 相机永远慢半拍原则（跟随类）：主体出画后才摇。

## 4. 微表情四拍（5-7s 特写镜头）

```
基线(常态) → 泄露(情绪一闪) → 压回(克制) → 余态(残留痕迹)
```

- 5-7s 需 4-7 个时码节拍；动词用"短促/半拍后/立刻压回"，禁"慢慢/逐渐"铺满。
- 自然眨眼层：特写/对白/情绪镜 ≤3s 必眨一次，眨眼放在动作节点上。
- 情绪用肌肉动作描述（嘴角单侧微抬 2mm、下颌收紧、眼睑压下 1/3），不用抽象词。

## 5. 能量曲线（15s 单片）

```
0-1.5s 钩子 → 1.5-4s 揭示 → 4-7s 交互 → 7-10s 变形 → 10.5-13s wow揭示 → 13.3-15s 收束定格 0.6-1s
```

## 6. 元素进场序列律（图转动效/poster-motion 型）

- 结构：全局氛围段(≤300字) → N 个时间戳段 → 锁帧约束段 → 音频段。
- 进场顺序固定：`背景 → 视觉锚 → 主标题 → 辅助信息 → settle → 呼吸微动`。
- 前一元素稳定 ≥0.5s 才进下一个；同刻只一个元素主动入场；锚点须**主动入场**禁慢显；文本落位后完全静止。
- 必配：`single continuous shot, no cuts, no transitions`；终帧与参考图 1:1 锁定。
- 动效术语库 16 词：Jelly Pop / Scale&Bounce / Kinetic Typography / Typewriter / Scroll Unroll / Card Slide-in / Paper Breakout / Light Sweep / Brush Stroke / Slice Reassembly / Parallax Push-in / Orbital Display / Particle Reconstruction / Breathing Pulse / Lens Flare Blink / Material Shift。

## 7. 禁止动作清单（人物类视频通用，写进生成器刚性约束）

```
- 转身背对镜头（180° 背身或露出后脑）
- 转成 90° 纯侧脸（2D 风格会崩五官几何）
- 沿 Z 轴纵深走向远离镜头
- 快速张嘴或夸张面部形变
- 静止冻结帧、原地绕圈、重复循环走动
- 无因方向反转、瞬移、动作跳变
```

替换词表：要转身 → `turns gently into an elegant three-quarter profile`；要离开 → `exits laterally across the frame`。

## 8. 收束锁帧

- 终态定格 0.6-2s：`holds the final pose / freeze on the settled composition`。
- 文字类：落位后完全静止。
- 终帧锚定类（海报动效/logo 动效）：`the final frame must be a 1:1 restoration of the reference image`。
- 干净尾帧：临时辅助元素（圆环/轨迹线/路径图）在收束前全部清除。
