# Format Rules

## File Naming Convention

```
{Mode}_{Description}_{Duration}.txt
```

Examples:
- `I2VA_Natsume_精灵秋叶原_12秒.txt`
- `Ref2VA_卡脖子_比心互动6秒.txt`
- `FL2VA_萌化协议_写实变Q版_12秒.txt`

## Folder Naming Convention

```
{Mode}_{Description}_{Duration}/
```

Each folder contains:
- `[输入+结果]_{Mode}_{Description}_{Duration}.txt` — the prompt file
- Reference images (.jpg, .png, .webp)
- Generated videos (.mp4)

## File Content Structure

```
{Mode} 提示词 - {Theme}
{Equals Line}

【原始输入】
账号：{Account}
角色：{Character Type}
推文内容：{Raw Content}
需求：{Requirements}
主题建议：{Theme Suggestion}（如有）

---

【生成结果】
主题名：{Theme Name}
时长：{Duration}
格式：MiniMax H3 {Mode}
版本：{Version}

---

{Complete H3 Prompt}

---

图片映射：
- Picture 1：{Description}

台词汇总：
1. "{Dialogue}" — {Speaker}，{Language}，{Tone}

镜头结构：
- Shot 1（{TimeRange}）：{Description}
```

## Mode Abbreviations

| Mode | Full Name | Description |
|------|-----------|-------------|
| T2VA | Text to Video | Pure text to video |
| I2VA | Image to Video | Single image as first frame |
| FL2VA | First-Last to Video | First + last frame keyframes |
| L2VA | Last to Video | Single last frame reference |
| Ref2VA | Reference to Video | Multiple reference images |

## Version Types

| Version | Description |
|---------|-------------|
| 纯委托 | Body text has zero appearance words, all delegated to Picture |
| 标准 | Standard format with appearance descriptions allowed |
| 自定义 | Custom version with specific requirements |
