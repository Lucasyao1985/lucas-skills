---
name: runninghub-workflow-extractor
description: Analyzes RunningHub AI App pages and extracts the hidden ComfyUI workflow JSON behind them. Probes webapp/workflow APIs, handles Rh-Accesstoken auth, recovers hidden workflowIds via node fingerprint matching, copies workflows through the workflow copy API, validates node graphs, repairs mojibake JSON, and writes an analysis report. Use when user shares a runninghub.ai or runninghub.cn link (ai-detail or workflow-detail) and asks to download, extract, export, or reverse the workflow; mentions 隐藏工作流, 工作流提取, AI App 工作流下载; or asks how a RunningHub app relates to its underlying ComfyUI workflow.
metadata:
  author: Lucas
  version: 1.0.0
  category: workflow-automation
  tags: [runninghub, comfyui, workflow-extraction, api-analysis]
---

# RunningHub Workflow Extractor

Extract the real ComfyUI workflow JSON hidden behind a RunningHub AI App page. A RunningHub "AI App" is only a form wrapper around an internal workflow; this skill recovers that workflow even when its ID is server-side hidden.

## Critical Rules

1. NEVER click run/submit buttons ("立即运行" etc.) without explicit user consent - running costs account credits.
2. Treat user tokens and cookies as secrets: use them for API calls only, never print full values into reports or save them to disk unencrypted.
3. Write API response bodies to disk as raw text. Never re-serialize JSON through PowerShell ConvertTo-Json (it corrupts structure).
4. If a task record exposes a workflowId only after a paid successful run, ask before spending anything.

## Page Type Decision Tree

| URL pattern | Type | Path |
|---|---|---|
| `runninghub.ai/ai-detail/<id>` | AI App (form wrapper) | Full pipeline below |
| `runninghub.ai/workflow-detail/<id>` | Public workflow | Skip to Step 6 (copy directly) |
| Title ends with "RunningHub AI Apps" | AI App confirmation | Full pipeline |

## Instructions

### Step 1: Anonymous Recon

Fetch the page HTML with a browser-like User-Agent. Expect only SEO metadata - Nuxt sites render client-side, `__NUXT_DATA__` is a tiny shell payload with no workflow data. Record the app title and confirm page type from the decision tree.

Note: the zh-cn path may return 401 anonymously while the English path returns 200. This only affects the HTML shell; business data always comes from APIs.

### Step 2: Frontend API Discovery

The frontend JS chunks are the API dictionary. Download all chunk URLs referenced by the page into a temp folder, then grep for:

```text
webapp/(detail|run|workflow)          workflow/(detail|info|json|get|copy|user/list)
getContent|getDetail|createCanvasRes  TOKEN_MISSION|Rh-Token|Authorization
localStorage\.getItem\("Rh-           accessKey|expire_in
```

Key facts established by this analysis:
- Auth model: localStorage key `Rh-Accesstoken` holds a JWT; the axios interceptor sends it as header `Authorization: Bearer <token>`. Cookies mirror the same names (`Rh-Accesstoken`, `Rh-Refreshtoken`, `Rh-Identify`). Team features add `X-Team-Id`.
- A separate ComfyUI credential (`Rh-Comfy-Auth`, an accessKey from the frontend comfyUI login call) exists for history/output endpoints - a Bearer token will NOT work there.
- The copy endpoint appears in the call chain of the site's "use this workflow" button - it returns full content. See `references/api-endpoints.md`.

### Step 3: Obtain Authentication

Automated browser login is usually blocked by anti-bot risk control. Do not retry it repeatedly. Instead ask the user to deliver credentials from their own browser, either:
- Console command `localStorage.getItem('Rh-Accesstoken')`, paste back the JWT starting with eyJ; or
- Export the full cookie set (Cookie-Editor style JSON) containing `Rh-Accesstoken` / `Rh-Refreshtoken` / `Rh-Identify`.

Validate any token before relying on it by calling a cheap authenticated endpoint (e.g. cost average) and checking for code 0. See `references/auth-and-cookies.md`.

### Step 4: Probe the App Detail API

Call `POST /api/webapp/detail` with body `{"webappId":"<id>"}`. Parameter-name rules:
- If you must guess parameter names, first capture one real request body via Playwright request interception instead of brute-forcing.
- Anonymous access works and returns id/name/tags/description/inputNodes, but `workflowId` is null.
- With a valid Bearer token, `workflowId` is STILL null for non-owners - the webapp-to-workflow mapping is private server-side.

Save the `inputNodes` array: its node IDs are the fingerprint used in Step 5.

### Step 5: Recover the Hidden workflowId

Try in order of cost:

**Method A - Fingerprint matching (free, preferred)**
1. Take the owner userId from the detail response (publishAccess owner field).
2. Call `POST /api/workflow/user/list {"userId":...}` to list the publisher's public workflows.
3. For each candidate call `POST /api/portal/workflow/detail {"workflowId":...}` and compare metadata (name, nodeCount, customNodes) against the app form options (model name, acceleration mode, etc.).
4. Copy the best candidates (Step 6) and rank them by node-ID overlap with the inputNodes fingerprint. Partial overlap means a base version; missing IDs are the app's private wrapper nodes.
5. CONFIDENCE GATE - raw IDs fail when the app graph was renumbered or heavily extended (overlap near zero even against the true base). Fall back to CLASS-level matching: compare inputNodes nodeName values against each candidate's node types. A candidate with ~0 ID overlap but most classes present is a BASE VERSION; low on BOTH is UNRELATED and must never be saved as the result. Only auto-select candidates passing the confidence gate; otherwise report "no confident match" and inspect the closest candidate manually.

**Method B - Paid run (fallback, needs consent)**
A real successful app run creates a task whose record exposes the underlying workflowId, which can then be copied. Cancelled tasks do NOT appear in task lists, so this cannot be done for free. Get explicit user approval and use minimal parameters.

### Step 6: Extract the Content

Call `POST /api/workflow/copy {"workflowId":"..."}` with the Bearer token. This is the golden channel - it copies the workflow into the caller's space AND returns the complete `workflowContent` (last_link_id, nodes, links) in the same response. Save the raw content text directly to file.

For already-public workflows (workflow-detail pages), start here using the URL's own ID.

### Step 7: Validate

Run `python scripts/rh_validate.py <workflow.json>` (or validate inline):
- JSON parses; count nodes and links.
- Core class present (e.g. the model-specific node such as MiniMaxH3ReferenceToVideo).
- Fingerprint verdict: FULL MATCH (all inputNodes IDs present), BASE VERSION (partial), or UNRELATED.
- Workflow parameters match the app form options (LoRA names, mode labels).

### Step 8: Post-process and Deliver

If node titles/prompts show mojibake (extended-latin characters like ae/c-cedilla sequences), repair with `python scripts/fix_mojibake.py <file.json>` - it reverses UTF-8-as-Latin-1 double encoding locally with no network reference needed. Then write a markdown report: page type, endpoints tried with results, auth path, workflowId recovery method, fingerprint comparison table, final files, and what remains inaccessible plus why.

## Examples

Example 1: AI App with hidden workflow
User says: "下载这个工作流 https://www.runninghub.ai/zh-cn/ai-detail/2086649152448098305"
Actions: classify as AI App, recon page, grep chunks, get token from user, probe webapp/detail (workflowId null), fingerprint-match against publisher list, copy best match, validate, fix mojibake, report.
Result: base-version workflow JSON saved + report explaining the private wrapper layer.

Example 2: Public workflow
User says: "提取 https://www.runninghub.ai/workflow-detail/123456 的 JSON"
Actions: skip to Step 6 with the URL's own ID, copy, validate, save.

## Troubleshooting

Error: TOKEN_MISSION (or HTTP 403 with ~34-byte body)
Cause: no credential attached. Solution: add Authorization Bearer header from Rh-Accesstoken.

Error: TOKEN_INVALID or HTTP 412 on history endpoints
Cause: wrong credential system - those endpoints need Rh-Comfy-Auth accessKey, not the Bearer JWT. Solution: switch to equivalent endpoints that accept Bearer (e.g. use copy instead of getContent).

Error: "应用Id不能为空"
Cause: wrong parameter name. Solution: capture the browser's real postData once instead of guessing.

Error: Playwright fails to launch (browser build mismatch)
Solution: launch with explicit executablePath pointing at an existing ms-playwright chromium folder.

Error: saved JSON won't parse after PowerShell processing
Cause: ConvertTo-Json re-serialization. Solution: re-fetch and write raw text.

Cancelled run invisible in task list
Cause: cancelled tasks are excluded. Solution: free recovery is impossible; a completed run requires consent.

Cookie auth alone does not work on API calls
Cause: the JSON APIs check the Authorization header, not cookies. Solution: send `Authorization: Bearer` with the Rh-Accesstoken value; cookies are only a fallback for page navigation.

All candidates show near-zero ID overlap but one matches by node classes
Cause: app graph was renumbered/extended from its public base (e.g. Action Transfer 4-in-1 built on Animate2). Solution: use class-level matching and deliver the base version with the private-wrapper delta documented - never save an unrelated candidate just because it ranked first.

## Performance Notes

- Do every step thoroughly; skipping validation has produced false matches before.
- Always compare node fingerprints rather than trusting filename or title similarity alone.
- Consult the reference files below before improvising new endpoint guesses.

## References

- `references/api-endpoints.md` - full endpoint table with params and observed behaviors
- `references/auth-and-cookies.md` - token acquisition, header model, cookie fields
- `references/frontend-analysis.md` - chunk download and grep patterns, postData capture snippets
- `references/fingerprint-matching.md` - node-ID matching method with worked example
- `references/case-study-minimax-h3.md` - complete condensed case study including mojibake repair
