---
name: openart-prompt-extractor
description: Extracts the verbatim prompt text hidden inside OpenArt template/app pages (openart.ai), including the viral template library at openart.ai/suite/home. OpenArt is a Next.js App Router site, so prompts are not in the visible HTML - they live in the React Server Component (RSC) "flight" payload as length-prefixed text rows. This skill fetches the page, reassembles the flight payload, resolves the promptTemplate reference, and verifies extraction against the declared byte length. Use when the user shares an openart.ai link (especially /suite/home/templates/ID) and asks to get, extract, copy, reverse, or save the prompt; mentions 提示词提取, OpenArt 提示词, 模板提示词, template prompt; or wants to batch-dump prompts from the OpenArt template home feed.
metadata:
  author: Lucas
  version: 1.0.0
  category: workflow-automation
  tags: [openart, prompt-extraction, rsc-flight, nextjs, seedance, video-prompt]
allowed-tools: "Bash(python:*) Bash(powershell:*) Read Write Glob Grep"
---

# OpenArt Prompt Extractor

Recover the **complete, verbatim** prompt behind any OpenArt template/app page. The prompt is never rendered as plain text in the DOM - it is embedded in the RSC flight payload and referenced indirectly, which is why naive scraping and "view source + Ctrl+F" return nothing.

## Critical Rules

1. **Never invent or paraphrase a prompt.** If extraction fails, report failure with the diagnostics. A reconstructed "looks about right" prompt is worthless - the value is byte-exact fidelity.
2. **Always verify the declared length.** Flight text rows carry a hex byte length (`2c:T1dc4,` = 7620 UTF-8 bytes). The script checks it; if verification fails, the output is truncated or misaligned and must not be delivered as complete.
3. **Only read public template data.** No login, no cookie, no form submission, no generation runs. Do not click "Generate"/"创建" - it spends the user's credits.
4. **Fetch in this order:** urllib in the Python script -> PowerShell `Invoke-WebRequest` fallback. On many CN Windows machines `curl` in a bash sandbox cannot reach the internet at all (exit 7 / HTTP 000) while PowerShell can.

## Quick Start

Single template page:

```bash
python scripts/extract_openart_prompt.py "https://openart.ai/suite/home/templates/I8bZOcXiziZaKCTLQNFe" --out ./out
```

Also grab the template's example video + thumbnail (`--media` puts everything in
a per-template folder):

```bash
python scripts/extract_openart_prompt.py "<url>" --media --out ./out
# out/<slug>/<slug>-prompt.md
# out/<slug>/preview.mp4
# out/<slug>/thumbnail.webp
```

Batch from explicit template ids (the reliable path - see Harvesting ids):

```bash
python scripts/extract_openart_prompt.py "https://openart.ai/suite/home" --list \
  --ids "I8bZOcXiziZaKCTLQNFe,AbCdEfGhIjKlMnOpQrSt" --out ./out
```

Or from a file, one id or URL per line:

```bash
python scripts/extract_openart_prompt.py "https://openart.ai/suite/home" --list \
  --file ids.txt --out ./out
```

Auto-detect ids from a server-rendered listing page (works only if the flight
carries the grid data - the home feed does not):

```bash
python scripts/extract_openart_prompt.py "<listing-url>" --list --limit 10 --out ./out
```

Re-parse an already downloaded page (no network):

```bash
python scripts/extract_openart_prompt.py --html ./page.html --out ./out
```

Machine-readable summary (stdout):

```bash
python scripts/extract_openart_prompt.py "<url>" --json
```

## How It Works

### Step 1 - Fetch the HTML

`scripts/extract_openart_prompt.py` tries `urllib` first, then falls back to `scripts/fetch_page.ps1` (PowerShell `Invoke-WebRequest`) which writes the body to a temp file and a status line to a log file.

Expected success: `STATUS=200 LEN=339088` style line in the log, HTML > 50 KB.

### Step 2 - Reassemble the flight payload

OpenArt streams the RSC payload as a series of `self.__next_f.push([1,"<json-escaped chunk>"])` calls. The script regex-captures every chunk, `json.loads` each, and concatenates them into one logical stream (`flight.txt` when `--debug`).

### Step 3 - Resolve the prompt reference

Inside the flight, the template object looks like:

```
{"id":"I8bZOcXiziZaKCTLQNFe","title":"Toon Scanner","promptTemplate":"$2c", ...}
```

`"$2c"` is a **reference**, not the text. The real text is a separate row elsewhere in the stream:

```
2c:T1dc4,A realistic, casual selfie-style video of the person from the reference photo, ...
```

Format: `<ref>:T<hexLength>,<text>`. The script slices exactly `hexLength` **UTF-8 bytes**, decodes, and asserts the re-encoded length matches. If `promptTemplate` is absent it falls back to `promptText` / `prompt` JSON strings, then to the longest text row over 500 chars.

### Step 4 - Write the deliverable

Writes `<slug>-prompt.md` containing: source URL, template ID, title, model (`sourceLabel` / `handoff.formId`), generation settings (duration, aspect ratio, resolution, audio, seed), required input references (`primitives` / `sourceReferences`), and the full verbatim prompt.

With `--media`, output goes to `<out>/<slug>/` and `scripts/download_file.ps1`
also saves `preview.mp4` (from `template.previewVideo.url`) and
`thumbnail.webp` (from `template.thumbnail.url`). Preview videos are typically
20-30 MB, so batch runs take a while - do not abort them.

## Output Format

```
# OpenArt 模板提示词：<title>

- 来源：<url>
- 模板 ID：<id>
- 生成模型：<sourceLabel>（<handoff.formId>）
- 生成参数：…
- 输入：…

---

## 完整提示词（逐字提取）

<verbatim prompt>
```

Always also give the user a short structural breakdown in chat (scene / audio / mechanic / performance / timeline) plus reuse notes - that is usually what they actually act on.

## Harvesting Template Ids

`/suite/home` ships **skeletons only** - the grid is filled client-side, so the
flight payload of the home page contains zero template ids. Do not waste turns
trying to scrape them from the HTML. Use one of these instead:

1. **Browser automation (recommended).** Load `https://openart.ai/suite/home`
   (the `agent-browser` skill), scroll to load the grid, and collect every
   `/suite/home/templates/<id>` link. Feed them to `--file`.
2. **Let the user paste links.** Template cards are shareable; a handful of URLs
   is usually enough.
3. **Known feed endpoint (blocked for scripted clients).** The app calls
   `GET /api/viral-templates?placement=director&pageSize=20&cursor=<cursor>`.
   Direct requests from a non-browser client return "connection closed", so it
   only works from inside a real browser session - another reason to prefer
   option 1.

## Field Map

| Flight field | Meaning |
|---|---|
| `title` | Template name |
| `sourceKind` / `sourceLabel` | Underlying model family / display name (e.g. `seedance` / `Seedance 2.5`) |
| `handoff.formId` | Concrete backend form, e.g. `byte-plus-seedance-2-5:text2video` |
| `handoff.sourceSettings` | duration, aspectRatio, resolution, generateAudio, videoCount, seed |
| `sourceReferences` | Input assets the template needs (image/video refs) |
| `primitives` | Required slots (e.g. `character`, required: true) |
| `promptTemplate` | Reference to the prompt text row (`$XX`) |

See `references/rsc-payload-anatomy.md` for the full format spec and a worked byte-level example.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `HTTP 000` / exit code 7 from curl | bash sandbox has no outbound network | Do not fight it - use the PowerShell fallback (built in) |
| `urllib failed, powershell failed` | Proxy/DNS block or site down | Retry once; try `--html` with a browser "Save page as" file |
| `flight payload empty` | Page is client-only, or bot wall | Check `STATUS` in the fetch log; confirm HTML size > 50 KB |
| `promptTemplate ref not found` | Template object key changed | Run `--debug`, grep flight for `prompt` and `T` rows, update the key list |
| Length verification fails | Split row or multi-byte boundary bug | Never ship it; re-run `--debug` and slice from the raw bytes |
| Short/garbage prompt | Picked a UI string instead of the prompt row | Prefer the `promptTemplate` ref; only use the "longest row" fallback as last resort |
| `--list` finds 0 templates | Home feed is client-rendered | Use `--ids` / `--file`, or harvest links with browser automation |
| `verified: false` | Fell back to the longest text row | Re-run `--debug`, find the `promptTemplate` ref manually, fix `TEMPLATE_KEYS` |

## Examples

**Example 1 - single template**

User: "https://openart.ai/suite/home/templates/I8bZOcXiziZaKCTLQNFe 这里面的提示词找出来"

1. Run the extractor on the URL.
2. Verify length (7620 bytes for this template).
3. Write `toon-scanner-prompt.md`, present it, and summarize: model Seedance 2.5, 30s / 16:9 / 720p / audio on, 1 required character reference image, 9-paragraph prompt (scene consistency, AUDIO, THE WINDOW, THE PERFORMANCE, THE SCANNING GAME, 4 timeline beats).

**Example 2 - batch from the home feed**

User: "把 openart suite home 上这些模板的提示词都扒下来"

1. `--list --limit 20` to enumerate template ids + titles.
2. Fetch each detail page sequentially (no parallelism - be polite).
3. One markdown per template plus an index printed to stdout.

**Example 3 - offline re-parse**

User already saved the page; run with `--html` to skip the network entirely.
