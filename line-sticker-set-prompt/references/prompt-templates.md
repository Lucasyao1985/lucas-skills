# Prompt Templates

## 1. The original base prompt (verbatim)

This is the exact prompt published with the reference set. It works as-is — treat it as the
floor, not the ceiling. `【场景】` is the only slot the original author intended users to change.

```
Reference the character in the uploaded image and transform it into a cute stylized version. Design 16 different LINE-style stickers.
Create varied poses and text layouts to form a diverse sticker set, making sure no two stickers look similar.
All dialogue text should be in Chinese, using popular and trendy wording. The background should be pure white.
Create a sticker set that is easy to use in everyday "【场景】" conversations.
```

## 2. Strengthened English template (recommended default)

The base prompt omits the grid, the cell count per row, and the identity lock — all three
cause visible failures. This version adds them.

```
The character must stay identical in all 16 stickers: <HAIR: e.g. dark brown hair in twin braids>,
<OUTFIT: e.g. sage-green knit sweater>, <ACCESSORY: e.g. small pink hair clip>,
<ART STYLE: e.g. cute semi-realistic chibi illustration>. Only the pose, expression, prop and
caption change between cells.

Reference the character in the uploaded image and transform it into a cute stylized version.
Design 16 different LINE-style stickers arranged in a 4x4 grid inside ONE single square image,
on a pure white (#FFFFFF) background with no gradient and no scenery behind the cells.

Create varied poses, props, camera angles and text layouts to form a diverse sticker set,
making sure no two stickers look similar — vary the body language, not just the words.

All dialogue text must be in Chinese, using popular and trendy wording, 2 to 6 characters per
sticker, each in its own speech bubble, ribbon or badge with a distinct shape and colour.

Create a sticker set that is easy to use in everyday "<SCENE>" conversations.

The 16 captions, in reading order (left to right, top to bottom), are:
1. <caption> ... 16. <caption>
```

## 3. Chinese version

```
角色在 16 张贴纸中必须完全一致：<发型>、<服装>、<配饰>、<画风>。只改变动作、表情、道具和文字。

参考上传图片中的角色，把它转换成可爱的风格化版本。设计 16 张不同的 LINE 风贴纸，
排成 4 行 4 列，放在同一张正方形图里，背景为纯白色（#FFFFFF），不要渐变、不要场景背景。

动作、道具、镜头角度和文字排版都要有变化，保证没有两张看起来相似——变的是肢体语言，不只是换几个字。

所有文字必须是中文，用当下流行的网络用语，每张 2-6 个字，各自放在形状和颜色都不同的气泡、
横幅或标牌里。

做一套方便日常「<场景>」聊天使用的表情包。

16 条文案，按从左到右、从上到下的顺序：
1. <文案> …… 16. <文案>
```

## 4. Variant — user has no reference image

Ask for a text description first, then lock it the same way. Do not skip the identity lock.

```
The character must stay identical in all 16 stickers: <describe from the user's text>.
... [rest identical to template 2] ...
```

## 5. Variant — multi-character (e.g. 情侣 with two people)

Two-character sets still fit the same 4x4 grid, but you must pin down who appears where.

```
The two characters must stay identical in all 16 stickers.
Character A: <features>. Character B: <features>.
Both appear together in at least 8 of the 16 stickers; the remaining cells may feature
either one alone. Keep their relative height and their outfit colours consistent.
... [rest identical to template 2] ...
```

## 6. Variant — re-theme an existing set

To move a working set to a new scene, **change only the caption list and the scene word.**
Do not re-describe the character — that is what makes the re-theme cheap.

```
[keep the entire existing prompt]
Create a sticker set that is easy to use in everyday "<NEW SCENE>" conversations.
The 16 captions, in reading order, are: <16 new captions>
```

## 7. Slot reference

| Slot | Required | Notes |
|---|---|---|
| `HAIR` | yes | style **and** colour, e.g. `dark brown twin braids` |
| `OUTFIT` | yes | garment **and** colour, e.g. `sage-green knit sweater` |
| `ACCESSORY` | if present | omit the line if the reference has none |
| `ART STYLE` | yes | `cute chibi illustration` / `keep the existing anime style` |
| `SCENE` | yes | drives the caption list, e.g. `打工人` |
| `caption 1..16` | yes | Chinese, 2-6 chars, no duplicates |
