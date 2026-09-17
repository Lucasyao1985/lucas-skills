# Frontend Analysis Reference

RunningHub is a Nuxt SPA. The HTML shell and `__NUXT_DATA__` contain no workflow data - all business data arrives via XHR. The minified JS chunks are the authoritative source for endpoint paths, parameter names, and auth logic.

## Chunk Harvesting

1. From the page HTML, collect every script/module URL under `/_nuxt/`.
2. Download them into one temp folder (they are plain text despite the .js hash names).
3. Grep the folder - do not read chunks manually.

## Grep Patterns That Paid Off

```text
# API path definitions
webapp/(detail|run|workflow|copy|validate)
workflow/(detail|info|json|get|copy|export|user/list)
portal/workflow|task/webapp|task/openapi
getContent|getDetail|createCanvasRes

# Auth model
TOKEN_MISSION
Rh-Token|rh-token|Authorization
localStorage\.getItem\("Rh-
Rh-Accesstoken|Rh-Refreshtoken|Rh-Comfy-Auth|Rh-Identify|Rh-Expire-In
accessKey|expire_in|X-Team-Id

# Storage keys and routes
localStorage\.setItem
WorkflowView|ai-detail|canvas\?webappId
```

Context trick: when grep hits are too noisy, extract 150-350 chars around each match of the keyword to see the surrounding function (e.g. how Rh-Accesstoken is placed into headers).

## Parameter Name Discovery

Guessing parameter names wastes turns (`"应用Id不能为空"`, `"must not be null"`). Instead capture ONE real request from the live site with Playwright:

```js
page.on('request', req => {
  if (req.url().includes('/api/') && req.method() === 'POST') {
    console.log(req.url(), req.postData());
  }
});
```

This yields exact param names in seconds (e.g. webapp/detail takes `webappId`, portal/workflow/detail takes `workflowId`).

## Playwright Notes

- Version mismatch error ("needs chromium_headless_shell-XXXX") - fix by launching with an explicit existing executable:
  `chromium.launch({ headless:false, executablePath: '.../ms-playwright/chromium-NNNN/chrome-win64/chrome.exe' })`
- Passive capture pattern: listen on `response`, keep bodies whose text contains both `"nodes"` and `"links"` - that is how you catch any response carrying a ComfyUI graph, as a safety net while driving the UI.
- SPA routes (/WorkflowView etc.) return 404 to direct HTTP requests; navigate inside a real browser context instead.
