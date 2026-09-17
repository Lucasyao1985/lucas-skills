# Case Study: MiniMax H3 AI App (2026-08-25)

Condensed end-to-end record of the extraction this skill was built from. Target: https://www.runninghub.ai/zh-cn/ai-detail/2086649152448098305 ("MiniMax H3 开源版-ComfyUI官方-多图参考生视频-支持音频输入").

## Timeline of What Worked and What Did Not

| # | Action | Result |
|---|---|---|
| 1 | GET zh-cn page | 401; English path 200 with SEO-only HTML |
| 2 | Inspect __NUXT_DATA__ | ~407-byte shell; client-side rendering confirmed |
| 3 | Grep Nuxt chunks | Found full API surface + auth model (Rh-Accesstoken -> Bearer) |
| 4 | Anonymous webapp/detail | code 0; inputNodes(16) present; workflowId null. First attempt used wrong param name - fixed by capturing real browser postData (`webappId`) |
| 5 | Playwright automated login | Blocked by risk control ("无法登入") - abandoned quickly |
| 6 | User-supplied cookie export | Rh-Accesstoken JWT obtained; validated via cost-average endpoint (code 0) |
| 7 | Authenticated webapp/detail | workflowId STILL null -> server-side privacy, not auth issue |
| 8 | Clicked 立即运行 in automation | Accidentally submitted task (2091942895496265729); cancelled immediately; cancelled tasks invisible in task/list so no free workflowId |
| 9 | portal/workflow/detail + user/list | Publisher's 10 public workflows enumerated |
| 10 | workflow/copy on candidate "Dasiwa V1-SLA加速-MiniMax H3" | FULL content returned: 42 nodes / 38 links |
| 11 | Fingerprint comparison | Partial overlap -> BASE VERSION; app wrapper (ImpactSwitch x2, LoadAudio, easy boolean x2, anythingIndexSwitch, renumbered core node 79) is private |
| 12 | runninghub.cn cross-check | App not published there; dead end |

## Deliverables

- `Dasiwa_V1_SLA加速_MiniMaxH3_工作流.json` - publisher's source graph via copy API
- `video_minimax_h3_r2v.json` - ComfyUI official R2V template (29 nodes) as reference baseline

## Why the Wrapper Stays Hidden

The webapp-to-workflowId mapping is enforced server-side for all non-owners across detail/copy/search surfaces. The only known exposure path is a completed (paid) run whose task record carries the workflowId. This is a business paywall, not a technical dead end.

## Mojibake Repair (post-extraction)

The delivered JSON had UTF-8-as-Latin-1 double encoding: all Chinese text corrupted (user noticed nodes 162/177, full scan found 135 mojibake chars across 9 strings - 4 node titles/widgets + 5 group titles). Repaired purely locally:

1. Backup .bak first.
2. Recursive scan of every string value for pattern: extended-latin lead chars followed by U+0080-U+00BF range chars.
3. Reverse per string: latin-1 encode back to bytes, decode as UTF-8 ("æ\u0085¢" -> E6 85 A2 -> "慢").
4. Targeted replace in raw text, each match exactly once.
5. Verify: no U+FFFD, fluent Chinese output, JSON integrity unchanged (42/38), byte-diff shows only those 9 strings.

First repair attempt silently collected 0 pairs due to a PSCustomObject-vs-IEnumerable type-check bug - always assert replaced-count == scanned-count.
