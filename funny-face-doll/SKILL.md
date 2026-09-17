---
name: funny-face-doll
description: Generate MiniMax H3 I2VA video prompts for "鬼脸娃娃" (Funny Face Doll) style — 8-second jump-cut videos where a real or anime character alternates between their normal face and exaggerated cartoon expression morphs, optionally with a giant prop at the end. Use when the user uploads a portrait photo and asks for a funny-face / funny-pose / expression-morph video prompt.
---

# Funny Face Doll (鬼脸娃娃) — MiniMax H3 I2VA Prompt Generator

## What This Skill Does

Takes a single portrait image (real person or anime character) and generates a complete MiniMax H3 I2VA prompt for an ~8-second vertical video with:

- **13 jump-cut shots** at strict timecodes (0.00s → 00:07.500)
- **Fixed camera** throughout (static shot, no movement)
- **AI face-morph effects** on even-numbered shots (cartoon head, stretched face, Maruko-chan expressions, etc.)
- **Real face** on odd-numbered "recovery" shots (returning to the person's actual appearance)
- **Optional giant prop** in the final 3 shots (rose, whale, cigarette, etc.)
- **Upbeat electronic BGM** with jump-cut-synced accents
- **No dialogue** — only ambient sound and non-diegetic music

## Workflow

1. **Analyze the input image** — identify gender, hairstyle, glasses/accessories, clothing, setting/background, props in hand, and overall mood.
2. **Read `references/template-cn.txt`** for the Chinese prompt template structure.
3. **Read `references/template-en.txt`** for the English prompt structure (this is the primary output format for the H3 model).
4. **Read `references/expression-library.md`** to select 6+ cartoon expressions appropriate for the character's hairstyle and vibe.
5. **Read `references/prop-library.md`** if the user wants a giant prop in the ending.
6. **Read `references/examples.md`** for complete worked examples (muscular man, short-haired woman, Maruko-chan variant).
7. **Generate the prompt** by:
   - Filling Shot 1 with an exact description of the image (first-frame anchor)
   - Choosing 6 cartoon expressions from the library that match the character
   - Filling the ending prop shots (Shot 11-13) if requested
   - Writing `overall_soundscape` matching the setting
   - Writing `non_diegetic_music` as upbeat electronic-pop
8. **Output both Chinese and English versions** unless the user specifies only one.

## Key Rules

- **Shot timing is fixed**: 0.00, 01.000, 01.500, 02.000, 02.500, 03.000, 03.500, 04.000, 04.500, 05.000, 06.500, 07.000, 07.500. All within 8 seconds.
- **Camera is always static** — no pan, tilt, zoom, or tracking.
- **Shot 1 is the first-frame anchor** — must describe the image exactly (appearance, clothing, setting, objects, pose).
- **Cartoon shots preserve real hair and accessories** — only the facial features morph; glasses, hair, clothing stay in place.
- **Odd shots (1, 3, 5, 7, 9, 11, 13)** = real face or prop interaction.
- **Even shots (2, 4, 6, 8, 10)** = cartoon expression morphs (the "funny face" shots).
- **Shot 10** = calm recovery moment (arms open, blissful).
- **Shots 11-13** = prop introduction and final pose (if prop is requested).
- **No speaker IDs or dialogue** — only ambient sound and BGM.
- **overall_soundscape** = setting-appropriate ambient + fabric rustle + one laugh.
- **non_diegetic_music** = upbeat electronic-pop, four-on-the-floor beat, synth hooks.

## Output Format

Both Chinese and English versions use the same H3 I2VA structure:

```
● [First-frame instruction line]

integrated_multimodal_description: [Shot 1] ... [Shot 2] ... [Shot 13] ...

overall_soundscape: ...

non_diegetic_music: ...

要点说明：
- ...
```

## Chinese vs English Differences

| Element | Chinese Version | English Version |
|---|---|---|
| Shot descriptions | 中文描述 | English description |
| Expression labels | 生气脸、哭脸、惊喜脸 | angry face, crying face, surprise face |
| Sound descriptions | 木质地板吱嘎声、蝉鸣 | creaks of wooden floor, cicada chirps |
| Props | 巨型香烟道具 | oversized cartoon cigarette prop |
| Notes section | 要点说明 | Key notes |

The structure, timecodes, shot count, and overall format remain identical.

## Prop Design Rules

When the user requests a prop (道具):

1. **Size**: Proportional to the character — roughly forearm-length or torso-sized depending on pose (standing vs seated).
2. **Style**: Cartoon / plush / exaggerated — not realistic.
3. **Color**: Should complement the character's outfit color palette.
4. **Placement**: Enters from bottom-left corner in Shot 11, character reacts with surprise.
5. **Final pose (Shot 13)**: Character interacts with the prop in a funny/extreme way.

## Character Type Adaptations

| Character Type | Hair Retention | Accessory Behavior | Expression Style |
|---|---|---|---|
| Short bob + bangs | Preserve exact silhouette | Glasses tilt during mouth-pull | Maruko-chan style recommended |
| Long hair | Preserve length and flow | Earrings stay | Generic cartoon child head |
| Male with short hair | Preserve hairline | Glasses stay or push up | Generic cartoon child head |
| Anime character | Preserve art style hair | Preserve accessories | Match anime art style |
| Bald / no hair | N/A | N/A | Extra-large cartoon head compensates |
