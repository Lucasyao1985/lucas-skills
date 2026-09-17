---
name: line-sticker-set-prompt
description: Builds copy-paste image-generation prompts that turn one character reference image into a 16-piece LINE-style sticker sheet (a single 4x4 grid, pure white background, short trendy Chinese captions). Use when the user uploads or names a character image and asks for 表情包 / 贴纸 / sticker set / LINE 风 / 斗图素材, or asks to write, adapt or expand a sticker-generation prompt for a scene such as 打工人、学生党、旅行、情侣、怼人、发疯文学. Also use to re-theme an existing sticker set to a new scene by swapping the caption list.
license: MIT
metadata:
  author: Lucas
  version: 1.0.0
  category: creative
  tags: [sticker, emoji, prompt, image-generation, line-style]
  source: https://www.xiaohongshu.com/explore/6a0ef0f90000000008032573
---

# LINE Sticker Set Prompt Builder

## What This Skill Does

Takes **one character reference image** and produces a copy-paste prompt that makes an
image model output **one square image containing a 4x4 grid of 16 LINE-style stickers**
for a given everyday scene (场景).

Verified output shape, observed from a real published set (reference images in
`assets/` description below — 8 scene sheets, 1254x1254 each):

| Property | Value |
|---|---|
| Output | **ONE** 1:1 image, 1254x1254, 4 columns x 4 rows = 16 cells |
| Background | pure white |
| Per cell | one die-cut style figure + its own speech bubble / ribbon / badge |
| Caption | **Chinese, 2-6 characters**, trendy internet wording |
| Identity | face, hairstyle and outfit **locked identical** across all 16 cells |
| Variety | pose, prop, camera angle and caption layout all differ; no two cells alike |

The character in the published set was a girl with dark twin braids and a green knit
sweater — that exact combination repeated in all 128 cells across 8 scenes. **The identity
lock is the single most important thing to get right.**

## Workflow

1. **Lock the character.** From the user's image, name the 4-6 features that must not
   change: hair style + colour, outfit + colour, accessories, art style, body type.
   Write them into the prompt explicitly. Do not say "the character" alone.
2. **Get the 场景.** If the user named one, use it. If not, offer three from
   `references/scene-caption-library.md` and let them pick.
3. **Pick 16 captions.** Read `references/scene-caption-library.md`. If the scene is
   already there, use that verified list. If it is new, write 16 in the same style:
   2-6 Chinese characters, current internet slang, everyday-chat usable, no duplicates.
4. **Fill the template.** Read `references/prompt-templates.md` and fill the
   `<SCENE>` and caption slots. Keep the English scaffold — it is what the model
   responded to in the original set.
5. **Self-check.** Read `references/quality-checklist.md` and run every item.
6. **Deliver.** Output the finished prompt in a fenced code block (copy-paste ready),
   then list the 16 captions as a numbered list so the user can swap individual ones.

## Key Rules

- **16 captions exactly.** Never 12, never 20. No duplicates, no near-duplicates
  (换两个字不算新的一张).
- **One image, not sixteen.** State explicitly that the output is a single 4x4 grid.
  Left unstated, models often emit 16 separate images or a 3x3 grid.
- **Pure white background** (`#FFFFFF`), no gradients, no scene backgrounds behind
  the cells. Individual cells may contain a small prop, but the page stays white.
- **Captions in Chinese only**, even when the prompt scaffold is English.
- **Identity lock before style.** Describe the character's fixed features before any
  pose or prop instruction, or the model will drift between cells.
- **Preserve the original art style** — if the reference is a photo, say "cute stylized
  illustrated version"; if it is already anime/chibi, say "keep the existing art style".
- **Don't invent captions when a verified list exists** for that scene — the 8 lists in
  the reference file are real published sets and are tuned for chat usability.

## Output Format

````
```
<one-paragraph identity lock: hair, outfit, accessories, art style>

Reference the character in the uploaded image and transform it into a cute stylized
version. Design 16 different LINE-style stickers arranged in a 4x4 grid in a single
square image, with a pure white background.
Create varied poses, props and text layouts to form a diverse sticker set, making sure
no two stickers look similar.
All dialogue text should be in Chinese, using popular and trendy wording. The
background should be pure white.
Create a sticker set that is easy to use in everyday "<SCENE>" conversations.
The 16 captions are: <caption 1>, <caption 2>, ... <caption 16>.
```
````

Then a numbered caption list, then one line naming the scene and the character features
that were locked.

## Common Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Only 9 or 12 stickers | grid size not stated | say "4x4 grid", "exactly 16 cells" |
| 16 separate images | grid not stated | say "in a single square image" |
| Character changes between cells | no identity lock | spell out hair + outfit in the prompt |
| Captions in English | instruction buried | repeat "Chinese captions" twice |
| Grey / gradient background | "pure white" dropped | write `pure white (#FFFFFF) background` |
| Captions duplicated | list not checked | run the checklist in `references/quality-checklist.md` |

## References

- `references/prompt-templates.md` — the verbatim base prompt, a strengthened version,
  a Chinese version, and variants for no-reference-image and multi-character cases.
- `references/scene-caption-library.md` — 8 verified scenes x 16 captions each.
- `references/quality-checklist.md` — pre-delivery self-check.
- `scripts/validate_skill.py` — packaging validator. Run it after editing this skill:

  ```bash
  python scripts/validate_skill.py .
  ```

  It checks folder naming, SKILL.md casing, frontmatter delimiters, the reserved-name rule,
  angle brackets, description length and the WHAT/WHEN requirement. Exit code 0 means clean.

