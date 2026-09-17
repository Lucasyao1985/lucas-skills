# Quality Checklist

Run every item before delivering a prompt. Items marked **BLOCKING** cause a visibly broken
output if missed — do not ship with a blocking item failing.

## Frontmatter and packaging (for the skill itself, not the prompt)

- [ ] Folder name is kebab-case, no spaces, no underscores, no capitals
- [ ] File is exactly `SKILL.md`, case-sensitive
- [ ] Frontmatter opens and closes with `---`
- [ ] `name` matches the folder name and is kebab-case
- [ ] `description` states both **what it does** and **when to use it**
- [ ] `description` is under 1024 characters
- [ ] No `<` or `>` anywhere in the frontmatter
- [ ] Name contains neither `claude` nor `anthropic`
- [ ] No `README.md` inside the skill folder

## The prompt itself

- [ ] **BLOCKING** Output is stated as **one single square image**
- [ ] **BLOCKING** Grid is stated as **4x4** and **exactly 16** stickers
- [ ] **BLOCKING** Background is stated as **pure white / #FFFFFF**
- [ ] **BLOCKING** Character identity lock lists hair, outfit, and art style explicitly
- [ ] **BLOCKING** Exactly 16 captions are listed, in reading order
- [ ] Captions are all Chinese
- [ ] Captions are 2-6 characters each
- [ ] No duplicate or near-duplicate captions
- [ ] "Chinese" appears twice (once for wording, once for the caption list) — models drop it
- [ ] Variety instruction mentions **poses and props**, not just text layout
- [ ] The scene word appears in the final "everyday conversations" line
- [ ] No reference to the character as just "the character" without the feature list

## Caption-list sanity

- [ ] Count is exactly 16 — recount, do not eyeball
- [ ] Reading order is stated so the model can map captions to cells
- [ ] Each caption has an obvious visual counterpart (prop, gesture, or expression)
- [ ] The set covers an arc, not 16 synonyms of one emotion
- [ ] The final caption is a soft closing beat
- [ ] Tone is consistent across all 16 — do not mix polite and 阴阳怪气 in one set

## Delivery

- [ ] Prompt is in a fenced code block, copy-paste ready, no placeholders left unfilled
- [ ] The 16 captions are also given as a numbered list for easy per-cell swapping
- [ ] The locked character features are named in one line below the prompt
- [ ] If a verified scene list was used, it was used **verbatim**, not paraphrased

## Quick regression test

Paste the prompt into the target model once and check the single output against:

1. Is it one image? 2. Is it 4x4 with 16 cells? 3. Is the background white?
4. Is the character the same in all 16 cells? 5. Are all 16 captions present, distinct,
and Chinese?

If any answer is no, the corresponding **BLOCKING** line above was dropped — restore it and
regenerate rather than patching the output by hand.
