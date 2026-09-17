# Anatomy of OpenArt's RSC Flight Payload

Reference for `openart-prompt-extractor`. Read this when extraction fails or when
OpenArt changes its page structure.

## Why plain scraping fails

OpenArt is a Next.js **App Router** site. The visible HTML contains almost no
content; the real data is streamed to the client as a **React Server Component
(RSC) flight payload**, injected as a series of script calls:

```html
<script>self.__next_f.push([1,"1a:{\"...json...\"}\n"])</script>
<script>self.__next_f.push([1,"2c:T1dc4,A realistic, casual selfie video..."])</script>
```

Each push argument is a **JSON string literal** (escaped `\"`, `\\`, `\n`).
Concatenating the decoded chunks in document order reconstructs one logical
stream - the flight payload.

## Row grammar

Each row is `<id>:<type><payload>` terminated by a newline.

| Type | Shape | Meaning |
|---|---|---|
| `T` | `2c:T1dc4,<text>` | Text chunk. `1dc4` is the **UTF-8 byte length in hex** of `<text>` |
| JSON | `20:[["$","$L29",null,{...}]]` | Element/model row, may be nested |
| `I` | `2e:I[876231,["/chunks/x.js"],"IconMark"]` | Client module reference |
| `E` | `4b:{"...json..."}` | Error row |

Key detail: **the length prefix counts UTF-8 bytes, not characters.** A 7554-char
English prompt can be 7620 bytes. Slicing by character count silently truncates
multi-byte content.

## Reference indirection

The template object does not contain the prompt string - it contains a
**reference**:

```json
{"id":"I8bZOcXiziZaKCTLQNFe","title":"Toon Scanner","promptTemplate":"$2c", ...}
```

`"$2c"` points at row id `2c`, whose `T` row holds the actual text. Resolution
algorithm:

1. Strip the leading `$` -> `2c`.
2. Regex the flight bytes for `(?:^|\n)2c:T([0-9a-fA-F]+),`.
3. `declared = int(hex, 16)`; slice `flight_bytes[end:end + declared]`.
4. `text = raw.decode('utf-8')`; assert `len(text.encode('utf-8')) == declared`.

The assertion is the whole point: it is the only proof the prompt was not
truncated at a chunk boundary.

## Worked example (Toon Scanner)

- URL: `https://openart.ai/suite/home/templates/I8bZOcXiziZaKCTLQNFe`
- Raw HTML: 339,088 chars
- Reassembled flight: 102,299 chars
- Template row contains `"promptTemplate":"$2c"`
- Row found: `2c:T1dc4,` -> declared `0x1dc4 = 7620` bytes
- Extracted: 7,554 chars / 7,620 UTF-8 bytes -> **verified**

## Template object field map

```json
{
  "id": "I8bZOcXiziZaKCTLQNFe",
  "title": "Toon Scanner",
  "description": "",
  "previewVideo": {"kind":"video","url":"https://cdn.openart.ai/...","width":1280,"height":720},
  "thumbnail":    {"kind":"image","url":"https://cdn.openart.ai/...","width":1280,"height":720},
  "titleGradientColor": "#95837a",
  "sourceKind": "seedance",
  "sourceLabel": "Seedance 2.5",
  "promptTemplate": "$2c",
  "sourceReferences": [
    {"id":"source-input-reference-...","kind":"image","sourceType":"upload",
     "url":"https://cdn.openart.ai/...","label":"image1"}
  ],
  "primitives": [
    {"id":"06296782-...","type":"character","title":"Character","required":true,
     "binding":{"sourceReferenceIds":["source-input-reference-..."]}}
  ],
  "handoff": {
    "type": "seedance",
    "formId": "byte-plus-seedance-2-5:text2video",
    "sourceSettings": {"videoCount":1,"duration":30,"aspectRatio":"16:9",
                       "resolution":"720p","generateAudio":true,"seed":-1}
  }
}
```

| Field | Use |
|---|---|
| `sourceKind` / `sourceLabel` | Model family + display name |
| `handoff.formId` | Exact backend form, e.g. `byte-plus-seedance-2-5:text2video` |
| `handoff.sourceSettings` | duration / aspectRatio / resolution / generateAudio / videoCount / seed |
| `sourceReferences` | Input assets (reference images) the template needs |
| `primitives` | Required user slots (character, product, ...) |
| `primitives[].required` | Whether the user must supply it |

## Listing pages

`/suite/home` embeds many template entries. Each has:

```
"detailHref":"/home/templates/<20-char-id>"
```

and a paired `"id":"<id>","title":"<title>"` sequence. Build the detail URL by
re-injecting the `/suite` prefix:

```
/home/templates/XXXX  ->  https://openart.ai/suite/home/templates/XXXX
```

Then run single-page extraction per id. Fetch sequentially, no concurrency.

### Reality check (verified 2026-09)

- `/suite/home` and `/suite/home/feed/viral-templates` both ship **skeletons
  only** (`data-testid="viral-template-skeleton"`). No ids, no `detailHref`,
  no `cdn.openart.ai/viral-template-assets/...` in the HTML.
- The grid is filled by:
  `GET /api/viral-templates?placement=director&pageSize=20&cursor=<cursor>`
  (found in chunk `675c0dffe77d57de.js`; `placement` also accepts `home`).
- Internal editor endpoints (not needed for extraction):
  `GET /api/internal/viral-templates/<id>`,
  `GET /api/internal/viral-templates/by-post/<postId>`,
  `POST /api/internal/viral-templates/source-context`.
- Direct scripted calls to any of these return **"连接被意外关闭" / connection
  closed**, with or without JSON/Referer/CORS headers. Treat them as
  browser-only.

**So: harvest ids with browser automation, then extract per template page.**
That per-page extraction is fully reliable because the detail page IS
server-rendered with the prompt inside the flight payload.

## Environment notes (CN Windows)

- `curl` inside a bash sandbox frequently returns exit code 7 / HTTP 000 even
  with `http_proxy` set - do not debug it, switch to PowerShell.
- PowerShell `Invoke-WebRequest -UseBasicParsing` works. Write the body to a file
  rather than relying on stdout (encoding + truncation issues).
- DNS for some domains resolves to wrong IPs; if the fetch log says
  `ERROR=... Unable to connect`, retry with a different network path.

## When the shape changes

1. Re-run with `--debug`; open `_flight.txt`.
2. Grep for `prompt`, `Prompt`, `T[0-9a-f]`, `detailHref`.
3. If `promptTemplate` moved under a new parent key, add it to `TEMPLATE_KEYS`
   in `extract_openart_prompt.py`.
4. If the row type is no longer `T`, adapt `resolve_ref()`.
5. Never ship an unverified extraction - report the mismatch instead.
