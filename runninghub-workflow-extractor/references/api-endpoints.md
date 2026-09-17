# RunningHub API Endpoints Reference

All endpoints confirmed by grepping minified Nuxt chunks and live probing. Base hosts: `https://www.runninghub.ai` (international) and `https://www.runninghub.cn` (China). The two sites do NOT share data - an app published on .ai is invisible on .cn. All listed calls are POST with JSON bodies unless noted.

## AI App (webapp) Endpoints

| Endpoint | Body | Auth | Returns |
|---|---|---|---|
| `/api/webapp/detail` | `{"webappId":"..."}` | Anonymous OK | code 0; id, name, tags, description, inputNodes[] (each has nodeId + param name), publishAccess.owner. `workflowId` is null for everyone except the owner - server-side privacy control, NOT a missing-auth symptom. |
| `/task/webapp/create` | webappId + nodeInfoList | Bearer required | Submits an app run task. Costs credits on success. |
| `/api/webapp/validate` | webappId + inputs | Bearer required | validateAndGetNodes - validates inputs and returns node info. |
| `/task/openapi/ai-app/run` | webappId + apiKey | OpenAPI key | External run entry for API users. |

## Workflow Endpoints

| Endpoint | Body | Auth | Returns |
|---|---|---|---|
| `/api/workflow/copy` | `{"workflowId":"..."}` | Bearer required | GOLDEN CHANNEL: copies a public workflow into your space AND returns the complete workflowContent (`{"last_link_id":...,"nodes":[...],"links":[...]}`) plus the new copy id in the same response. This is what the site's "use this workflow" button calls. Leaves a test copy in your workspace - clean up afterwards. |
| `/api/portal/workflow/detail` | `{"workflowId":"..."}` | Anonymous OK | Metadata only: name, nodeCount, primitiveNodes, customNodes, usedModels. workflowContent is null here. Use for fingerprint candidate screening. |
| `/api/workflow/user/list` | `{"userId":"..."}` | Bearer recommended | List of that user's published workflows (id + workflowId rows). Feeds fingerprint matching. |
| `/api/workflow/getContent` | `{"workflowId":"..."}` | Owner only | Raw content. Anonymous returns TOKEN_MISSION; non-owner gets denied. Prefer copy. |
| `/api/workflow/getDetail` | `{"workflowId":"..."}` | Owner only | Workflow detail record. |
| `/api/workflow/export` | - | Owner only | Blob export. Rarely usable for third-party workflows. |

## Task / History Endpoints

| Endpoint | Body | Auth | Returns |
|---|---|---|---|
| `/task/list` | paging params | Bearer required | Task records. Records contain a workflowId field, but CANCELLED tasks are excluded from results - you cannot harvest a workflowId from a cancelled run. |
| `/api/output/v2/history` | paging params | Rh-Comfy-Auth (accessKey), NOT Bearer | Generation history. Bearer token yields TOKEN_INVALID or HTTP 412. |
| cheap validation e.g. cost-average endpoint | `{}` | Bearer required | code 0 proves the token works. Use before long pipelines. |

## Error Semantics

| Signal | Meaning | Fix |
|---|---|---|
| body contains `TOKEN_MISSION` (~34 bytes) or HTTP 403 | No credential attached | Add `Authorization: Bearer <Rh-Accesstoken>` |
| `TOKEN_INVALID` or HTTP 412 | Wrong credential system (needs ComfyUI accessKey) | Switch endpoint or obtain Rh-Comfy-Auth via the frontend comfyUI login call |
| `"应用Id不能为空"` / "must not be null" | Wrong parameter NAME (not value) | Capture one real browser postData instead of guessing |
| HTTP 401 on zh-cn page HTML | Anti-bot on localized shell path | Ignore; use English path for recon or go straight to APIs |

## Search Endpoint Caveat

The public search endpoint may ignore its keyword parameter and return a constant result set - do not rely on it to find a publisher's workflows. Use `/api/workflow/user/list` with the owner userId instead.
