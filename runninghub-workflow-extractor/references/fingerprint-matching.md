# WorkflowId Fingerprint Matching

When `/api/webapp/detail` hides `workflowId` (it does, even authenticated), recover the underlying workflow by matching the app's exposed node IDs against the publisher's public workflows.

## Fingerprint Source

The anonymous-friendly webapp detail returns `inputNodes`: ~10-20 objects, each with a nodeId and parameter name. Example real fingerprint:

```text
14 LoadImage          118 129 LoadImage x2      142 86 ImpactSwitch x2
32 33 easy boolean    115 easy anythingIndexSwitch   110 LoadAudio
157 93 162 158 159 ...   79 MiniMaxH3ReferenceToVideo : prompt
```

These nodeIds belong to the INTERNAL graph, so they identify it like a signature.

## Matching Procedure

1. Owner userId: take from the detail response (publishAccess owner field) or decode from your own JWT only if you ARE the owner; otherwise use the value from the detail payload.
2. `POST /api/workflow/user/list {"userId":"..."}` - list the publisher's public workflows (id + workflowId rows).
3. For each row: `POST /api/portal/workflow/detail {"workflowId":"..."}` and screen cheaply:
   - name similarity to the app title / form options;
   - nodeCount vs expected scale;
   - customNodes containing the app's core class (e.g. MiniMaxH3ReferenceToVideo).
4. Shortlist 1-3 candidates; copy each (`/api/workflow/copy`) and compare content node IDs against the fingerprint.

## Interpreting Overlap

| Result | Meaning | Action |
|---|---|---|
| All inputNodes IDs present, count equal | FULL MATCH - this IS the internal workflow | Deliver |
| Core subset present (LoadImage/base nodes), app-only IDs missing (ImpactSwitch, LoadAudio, extra LoadImages, renumbered core node) | BASE VERSION - publisher's public ancestor graph; the app adds a private wrapper layer | Deliver as best free result; document the delta |
| Few or zero shared IDs | UNRELATED | Discard candidate |

Also cross-check semantic anchors: LoRA/model names inside the copied JSON must match the app's form dropdown labels (e.g. model "Dasiwa V1", mode "SLA加速"). Name+parameter agreement is strong evidence even before ID comparison.

## Worked Example 2: Renumbered graph (Action Transfer 4-in-1, 2026-08-25)

App: "Action Transfer 4-in-1 - Subject Replacement - Background Replacement - Action Imitation" (same publisher). Fingerprint had 18 IDs (232 VHS_LoadVideo, 655/179 LoadImage, easy int x4, easy boolean x4, ImpactSwitch x4, easy string x2, easy float) - all high numbers (163..1082), a red flag for a renumbered/extended internal graph.

Copying all 10 public candidates gave near-zero ID overlap for every one. A naive "pick the highest" auto-selection chose an UNRELATED LTX-2.5 lip-sync workflow (2/18 IDs) - a false positive.

Correct procedure - class-level fallback:
1. Compare inputNodes nodeName values against each candidate's node type inventory.
2. Animate2 (WanAnimate2ToVideo motion transfer, 99 nodes) contains VHS_LoadVideo + LoadImage + easy int -> thematically and structurally the base.
3. Classes present in the app but NOT in Animate2 (ImpactSwitch x4, easy boolean x4, easy string x2, easy float) are exactly the private wrapper: the 4-in-1 mode switching and extra inputs.
Verdict: BASE VERSION with fully renumbered IDs; full wrapper only obtainable via a paid run.

Lesson baked into rh_extract.py: never auto-save without the confidence gate (full ID match, ID overlap >= max(3, 50%), or class match >= 60%).

## Worked Example 1

App: "MiniMax H3 开源版-ComfyUI官方-多图参考生视频-支持音频输入".
Fingerprint had 16 IDs. Publisher list returned 10 workflows. Candidate "Dasiwa V1-SLA加速-MiniMax H3" matched form labels exactly; its copied content (42 nodes / 38 links) contained IDs 14, 162, 158, 159 but lacked 118, 129, 142, 86, 79 -> verdict BASE VERSION. Conclusion: the app wraps this public base with multi-image switching (ImpactSwitch), audio input (LoadAudio), and boolean toggles; that wrapper is server-side private and only obtainable via a paid successful run whose task record exposes the real workflowId.
