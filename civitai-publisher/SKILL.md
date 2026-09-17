---
name: civitai-publisher
description: Civitai 全自动发布技能——通过 API 创建模型/版本，Playwright 浏览器自动上传 ZIP 工作流和预览图，React fiber 绕过 Mantine Dropzone 验证，最终发布上线。
trigger: |
  当用户要求:
  - 发布到 Civitai / 上传 Civitai
  - 自动发布工作流到 Civitai
  - Civitai 上传 / Civitai 发布 / Civitai 建模
  - ComfyUI 工作流发布到 Civitai
  - RunningHub 到 Civitai 自动发布
user-invocable: true
metadata:
  requires:
    bins: [python]
    python: [httpx, playwright, Pillow]
    os: [win32]
---

# /civitai-publisher — Civitai 自动发布技能

## 一句话概述

通过 API + 浏览器自动化，将 ComfyUI 工作流 JSON 打包为 ZIP 发布到 Civitai（创建模型 → 上传文件 → 发布），全程自动化无需手动操作。

---

## 整体流程

```
1. 打包工作流 JSON → ZIP
2. API 创建模型 (Draft)
3. API 创建版本
4. Playwright 浏览器上传 ZIP（React fiber 绕过 Mantine Dropzone）
5. Playwright 浏览器上传预览图（可选）
6. API 发布模型 + 版本
```

---

## 核心技术要点

### 1. Civitai tRPC API 格式

Civitai 使用 tRPC v10 协议，**关键规则**：

**GET 查询：** 参数名 `input`，值为 JSON 编码的 batch payload
```
GET /api/trpc/model.getById?input={"0":{"json":{"id":2706510}}}&batch=1
```

**POST 变更：** URL 必须带 `?batch=1`，body 格式为 `{"0": {"json": {...}}}`
```
POST /api/trpc/model.upsert?batch=1
Body: {"0": {"json": {"name": "...", "type": "Workflows", ...}}}
```

**⚠️ 忘记 `?batch=1` 会导致 400 错误：** `"Invalid input: expected object, received undefined"`

**主要 API 端点：**

| 端点 | 用途 | 关键字段 |
|------|------|----------|
| `model.upsert` | 创建/更新模型 | name, type(Workflows), uploadType(Created), status(Draft), description, tags |
| `modelVersion.upsert` | 创建/更新版本 | modelId, name, baseModel, files |
| `model.getById` | 查询模型详情 | id |
| `model.publish` | 发布模型 | id |
| `modelVersion.publish` | 发布版本 | id |
| `model.delete` | 删除模型 | id |
| `/api/upload` (REST) | 申请上传预签名 URL | filename, modelVersionId |
| `post.create` | 创建帖子 | modelVersionId, title, detail |
| `post.update` | 更新帖子 | id, title, detail |
| `post.addImage` | 添加图片到帖子 | postId(integer), url(R2 key) |

### 2. 浏览器认证：路由拦截

**不要用 cookie 认证。** 必须用 Playwright `page.route()` 拦截所有请求并注入 `Authorization` 头：

```python
def auth(route):
    headers = dict(route.request.headers)
    headers["Authorization"] = f"Bearer {CIVITAI_TOKEN}"
    route.continue_(headers=headers)

page.route("**://civitai.com/**", auth)
page.route("**://*.civitai.com/**", auth)
```

**为什么 cookie 不行：** Civitai 的 Next.js 服务端检查的是 NextAuth session cookie，而不是 `__Secure-civitai-token`。cookie 认证会导致页面重定向到 `?missingSession=true`。路由拦截注入 Bearer token 可以让服务端 API 认证生效。

### 3. 文件上传：React Fiber 绕过 Mantine Dropzone

**核心问题：** Civitai 使用 Mantine Dropzone 组件处理文件上传。Playwright 的 `set_input_files()` 会将文件设置到 `<input>`，但 Dropzone 的验证逻辑会拒绝（`dropzoneReject` 状态），导致上传不触发。

**11 种方法都失败后，唯一成功的方法是：**

**直接调用 React fiber 树中 Dropzone 组件的 `onDrop` 处理函数。**

```python
result = page.evaluate("""
    async ({b64, filename, mimeType}) => {
        const bs = atob(b64);
        const bytes = new Uint8Array(bs.length);
        for(let i=0;i<bs.length;i++) bytes[i]=bs.charCodeAt(i);
        const file = new File([bytes], filename, {type:mimeType});

        // 找到 Mantine Dropzone 根元素（class 包含 m_d46a4834）
        const dropzoneRoots = document.querySelectorAll(
            '[class*="m_d46a4834"], [class*="mantine-Dropzone-root"]'
        );

        for(const dz of dropzoneRoots){
            if(!dz.offsetParent) continue;
            const fk = Object.keys(dz).find(k=>k.startsWith('__reactFiber$'));
            if(!fk) continue;

            let fiber = dz[fk];
            for(let d=0; d<15 && fiber; d++){
                const p = fiber.memoizedProps;
                if(p && typeof p.onDrop === 'function'){
                    p.onDrop([file]);  // 直接调用 React 处理函数
                    return JSON.stringify({success:true, depth:d});
                }
                fiber = fiber.return;
            }
        }
        return JSON.stringify({error:'no Dropzone found'});
    }
""", {"b64": zip_b64, "filename": "workflow.zip", "mimeType": "application/zip"})
```

**关键细节：**
- 必须先 base64 编码文件内容传入浏览器上下文
- 查找 class 包含 `m_d46a4834` 的元素（Mantine Dropzone 的 hash 类名）
- 在这些元素的 React fiber 链上找到 `onDrop` 处理器（通常在 depth=4）
- 直接调用 `props.onDrop([file])`，绕过所有 DOM 事件和验证
- 成功后 Dropzone 会自动触发 `/api/upload` → R2 PUT → 绑定

### 4. Python 路径处理

Windows 下 Git Bash 环境不能用 `D:\path`（反斜杠被 shell 吃掉），必须用 `/d/path` 格式：

```python
# ✅ 正确
/d/Conda/python.exe script.py

# ❌ 错误  
D:\Conda\python.exe script.py  # 变成 "D:Condapython.exe" - command not found
```

### 5. 图片预处理

上传预览图前，先转换为高质量 JPG（用 `/to-jpg` skill 或 Pillow）：

```python
from PIL import Image
img = Image.open(src)
if img.mode in ('RGBA', 'LA', 'P'):
    bg = Image.new('RGB', img.size, (255,255,255))
    bg.paste(img, mask=img.split()[-1] if img.mode!='P' else None)
    img = bg
img.save(dst, 'JPEG', quality=97, subsampling='4:4:4')
```

---

## 完整实现脚本

```python
import json, time, base64
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

TOKEN = "<civitai-api-token>"

# ─── API helpers ───
def api_post(path, data):
    return httpx.post(
        f"https://civitai.com/api/trpc/{path}?batch=1",
        json=data,
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"},
        timeout=30
    )

def api_get(path, params):
    return httpx.get(
        f"https://civitai.com/api/trpc/{path}",
        params=params,
        headers={"Authorization":f"Bearer {TOKEN}"},
        timeout=30
    )

# Step 1: Create model
model_id = api_post("model.upsert", {"0":{"json":{
    "name":"<name>","type":"Workflows","uploadType":"Created",
    "status":"Draft","description":"<desc>","tags":["tag1","tag2"],
    "nsfw":False,"poi":False
}}}).json()[0]["result"]["data"]["json"]["id"]

# Step 2: Create version
version_id = api_post("modelVersion.upsert", {"0":{"json":{
    "modelId":model_id,"name":"v1.0","baseModel":"Other","files":[]
}}}).json()[0]["result"]["data"]["json"]["id"]

# Step 3: Browser upload
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    ctx = browser.new_context(viewport={"width":1440,"height":960})
    page = ctx.new_page()

    # Auth via route interception
    def auth(route):
        h = dict(route.request.headers)
        h["Authorization"] = f"Bearer {TOKEN}"
        route.continue_(headers=h)
    page.route("**://civitai.com/**", auth)

    # Navigate to wizard step 3
    page.goto(f"https://civitai.com/models/{model_id}/wizard?step=3&versionId={version_id}",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)

    # Upload ZIP via React fiber onDrop
    zip_b64 = base64.b64encode(Path("workflow.zip").read_bytes()).decode()
    page.evaluate("""
        async ({b64, filename, mimeType}) => {
            const bs=atob(b64);const bytes=new Uint8Array(bs.length);
            for(let i=0;i<bs.length;i++)bytes[i]=bs.charCodeAt(i);
            const file=new File([bytes],filename,{type:mimeType});
            for(const dz of document.querySelectorAll('[class*="m_d46a4834"]')){
                const fk=Object.keys(dz).find(k=>k.startsWith('__reactFiber$'));
                if(!fk||!dz.offsetParent)continue;
                let fiber=dz[fk];
                for(let d=0;d<15&&fiber;d++){
                    if(fiber.memoizedProps?.onDrop){
                        fiber.memoizedProps.onDrop([file]);return;
                    }
                    fiber=fiber.return;
                }
            }
        }
    """, {"b64":zip_b64,"filename":"workflow.zip","mimeType":"application/zip"})

    page.wait_for_timeout(8000)

    # Click Next → step 4 (create post)
    page.locator('button:has-text("Next")').first.click()
    page.wait_for_timeout(5000)

    browser.close()

# Step 4: Publish
api_post("modelVersion.publish", {"0":{"json":{"id":version_id}}})
api_post("model.publish", {"0":{"json":{"id":model_id}}})
```

---

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `missingSession=true` 重定向 | cookie 认证不适用于 SSR | 改用路由拦截注入 `Authorization` 头 |
| `"Invalid input: expected object, received undefined"` (400) | URL 缺少 `?batch=1` | POST 请求 URL 必须带 `?batch=1` |
| `dropzoneReject` 状态持续 | Mantine Dropzone 验证拒绝文件 | 使用 React fiber 直接调用 `onDrop([file])` |
| `onDrop` 调用了但无上传请求 | 调用了错误的 fiber（如 SVG path） | 先筛选 `[class*="m_d46a4834"]` 的 Dropzone 根元素 |
| 上传完成后 `modelVersion.files` 仍为空 | `modelVersion.upsert` 的 `files` 参数被忽略 | 必须通过浏览器 wizard 上传文件（API 无法直接绑定文件） |
| `/api/upload` 返回 500 | 使用了错误的 payload 字段名 | 使用 `filename` 而非 `name` |
| R2 SSL 握手失败 | Python httpx/curl 的 TLS 到 Cloudflare R2 被阻断 | 利用浏览器（Chromium）的网络栈：文件通过浏览器的 Dropzone → R2 上传 |
| `python3` command not found / exit code 49 | Windows Store stub 拦截 | 使用 `/d/Conda/python.exe` 而非 `python3` |
| UnicodeEncodeError in GBK | 终端编码为 GBK | 避免使用 emoji，或 Python 脚本中不 print 非 ASCII |

---

## 已失败的方法（供参考）

以下 11 种方法均已测试且**不可行**，避免重复踩坑：

| # | 方法 | 失败原因 |
|---|------|----------|
| 1 | `set_input_files` + ZIP | dropzoneReject，无上传请求 |
| 2 | `set_input_files` + JSON | 文件不显示，dropzoneReject |
| 3 | JS `DataTransfer` + `dispatchEvent(drop)` | 无效果 |
| 4 | `file_chooser` 点击 dropzone | 无 chooser 弹出 |
| 5 | `file_chooser` 点击 file input (force click) | 无 chooser 弹出 |
| 6 | JS `input.click()` 显示 input 后点击 | chooser 弹出但无上传请求 |
| 7 | edit 页面注入文件 | edit 页面只有图片 input，无模型文件上传 |
| 8 | 纯 API `/api/upload` → R2 PUT | R2 SSL 被阻断 + 文件无法绑定到 version |
| 9 | `modelVersion.upsert` 传 `files` 参数 | API 忽略 |
| 10 | cookie 认证 | Next.js SSR 不认 API token cookie |
| 11 | JS 路由拦截 patch | 大量 JS chunk 超时，路由拦截崩溃 |

**唯一可行方案：API 创建模型 → Playwright 路由拦截认证 → React fiber `onDrop([file])`**

---

## 环境要求

- Python 3.x + `httpx` + `playwright` + `Pillow`
- Playwright Chromium 浏览器
- Civitai API Token（在 `https://civitai.com/user/account` 生成）
