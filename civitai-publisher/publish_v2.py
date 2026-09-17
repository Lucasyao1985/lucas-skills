"""Create new CivitAI model — fixed fiber traversal for onDrop."""
import json, time, base64
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

TOKEN = "d9a510da50682610be097d7ba21d520b"

DESC = open("C:/Users/Lucas/.claude/skills/civitai-publisher/新建 文本文档.txt", encoding="utf-8").read().strip()
ZIP_PATH = Path("C:/Users/Lucas/Desktop/workflow_new.zip")
COVER_GIF = Path("C:/Users/Lucas/Desktop/新建文件夹 (21)/Civitai自动发布技术总结/新建文件夹/WanVideo2_1_multitalk_00001_p81-audio_qjvxc_1777650084_5mb.gif")

MODEL_NAME = "AI Singing Digital Human Lip Sync - RCM + Infinite Talk"

# ─── Helpers ───
def api_post(path, data):
    return httpx.post(
        f"https://civitai.com/api/trpc/{path}?batch=1",
        json=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=30
    ).json()

# ─── Step 1: Create model ───
print("[1/5] Creating model (Draft)...")
result = api_post("model.upsert", {"0": {"json": {
    "name": MODEL_NAME,
    "type": "Workflows",
    "uploadType": "Created",
    "status": "Draft",
    "description": DESC,
    "tags": ["AI", "SINGING", "DIGITAL", "HUMAN", "LIP", "SYNC", "AVATAR", "VIDEO", "RCM", "INFINITE", "TALK"],
    "nsfw": False, "poi": False,
    "allowNoCredit": True,
    "allowCommercialUse": ["Sell"],
    "allowDerivatives": True,
    "allowDifferentLicense": True,
}}})
model_id = result[0]["result"]["data"]["json"]["id"]
print(f"  Model ID: {model_id}")

# ─── Step 2: Create version ───
print("[2/5] Creating version...")
result = api_post("modelVersion.upsert", {"0": {"json": {
    "modelId": model_id, "name": "v1.0", "baseModel": "Other", "files": []
}}})
version_id = result[0]["result"]["data"]["json"]["id"]
print(f"  Version ID: {version_id}")

# ─── Step 3: Browser upload ───
print("[3/5] Browser upload...")

zip_b64 = base64.b64encode(ZIP_PATH.read_bytes()).decode()
print(f"  ZIP base64: {len(zip_b64)} chars")

# Prepare cover JPG
from PIL import Image
img = Image.open(COVER_GIF)
if img.mode in ('RGBA', 'LA', 'P', 'PA'):
    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
    if img.mode == 'P': img = img.convert('RGBA')
    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
    img = rgb_img
elif img.mode != 'RGB':
    img = img.convert('RGB')
max_dim = 2000
if img.size[0] > max_dim or img.size[1] > max_dim:
    ratio = max_dim / max(img.size)
    img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)), Image.LANCZOS)
jpg_path = Path("C:/Users/Lucas/Desktop/cover_upload.jpg")
img.save(jpg_path, 'JPEG', quality=93, subsampling='4:4:4')
jpg_b64 = base64.b64encode(jpg_path.read_bytes()).decode()
print(f"  Cover JPG: {jpg_path.stat().st_size/1024:.0f} KB")

# JS function to upload file using the CORRECT (deepest) fiber handler
UPLOAD_JS = """
async ({b64, filename, mimeType}) => {
    const bs = atob(b64);
    const bytes = new Uint8Array(bs.length);
    for (let i = 0; i < bs.length; i++) bytes[i] = bs.charCodeAt(i);
    const file = new File([bytes], filename, {type: mimeType});

    const dropzoneRoots = document.querySelectorAll(
        '[class*="m_d46a4834"], [class*="mantine-Dropzone-root"]'
    );

    for (const dz of dropzoneRoots) {
        if (!dz.offsetParent) continue;
        const fk = Object.keys(dz).find(k => k.startsWith('__reactFiber$'));
        if (!fk) continue;

        // Collect ALL onDrop handlers across fiber chain
        let fiber = dz[fk];
        const handlers = [];
        for (let d = 0; d < 20 && fiber; d++) {
            if (fiber.memoizedProps && typeof fiber.memoizedProps.onDrop === 'function') {
                const t = typeof fiber.type === 'string' ? fiber.type :
                    (fiber.type?.displayName || fiber.type?.name || '?');
                handlers.push({depth: d, type: t, accept: fiber.memoizedProps.accept});
            }
            fiber = fiber.return;
        }

        if (handlers.length === 0) continue;

        // Use the DEEPEST handler (Mantine component, not DOM div)
        const best = handlers[handlers.length - 1];

        // Traverse to the best handler and call it
        fiber = dz[fk];
        for (let d = 0; d <= best.depth && fiber; d++) {
            if (d === best.depth && fiber.memoizedProps?.onDrop) {
                fiber.memoizedProps.onDrop([file]);
                return JSON.stringify({
                    success: true, used: best, allHandlers: handlers
                });
            }
            fiber = fiber.return;
        }
    }
    return JSON.stringify({error: 'no handler found'});
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960})
    page = ctx.new_page()

    def auth(route):
        h = dict(route.request.headers)
        h["Authorization"] = f"Bearer {TOKEN}"
        route.continue_(headers=h)
    page.route("**://civitai.com/**", auth)
    page.route("**://*.civitai.com/**", auth)

    # Navigate to wizard step 3
    page.goto(f"https://civitai.com/models/{model_id}/wizard?step=3&versionId={version_id}",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    print(f"  Step 3 URL: {page.url}")

    # Upload ZIP using fixed handler
    result = page.evaluate(UPLOAD_JS, {"b64": zip_b64, "filename": "workflow.zip", "mimeType": "application/zip"})
    print(f"  ZIP upload: {result[:300]}")
    page.wait_for_timeout(10000)
    page.screenshot(path="C:/Users/Lucas/Desktop/step3_after_zip.png")

    # Click Next -> step 4
    next_btn = page.locator('button:has-text("Next")').first
    if next_btn.is_visible():
        next_btn.click()
        page.wait_for_timeout(8000)
        print(f"  After Next: {page.url}")

    # Upload cover image at step 4 (if dropzones exist)
    dropzones_count = page.locator('[class*="m_d46a4834"]').count()
    print(f"  Step 4 dropzones: {dropzones_count}")

    if dropzones_count > 0:
        img_result = page.evaluate(UPLOAD_JS, {"b64": jpg_b64, "filename": "cover.jpg", "mimeType": "image/jpeg"})
        print(f"  Image upload: {img_result[:300]}")
        page.wait_for_timeout(8000)
        page.screenshot(path="C:/Users/Lucas/Desktop/step4_after_image.png")

    # Click through any remaining Next buttons
    for i in range(2):
        try:
            nxt = page.locator('button:has-text("Next")').first
            if nxt.is_visible():
                print(f"  Clicking Next ({i+1})...")
                nxt.click()
                page.wait_for_timeout(5000)
        except:
            break

    print(f"  Final URL: {page.url}")
    browser.close()

# ─── Step 5: Publish ───
print("\n[5/5] Publishing...")
r1 = api_post("modelVersion.publish", {"0": {"json": {"id": version_id}}})
print(f"  Version: {json.dumps(r1, ensure_ascii=False)[:150]}")
r2 = api_post("model.publish", {"0": {"json": {"id": model_id}}})
print(f"  Model: {json.dumps(r2, ensure_ascii=False)[:150]}")

print(f"\n=== Published! ===")
print(f"https://civitai.com/models/{model_id}")
