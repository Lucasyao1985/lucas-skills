"""Create new CivitAI model from scratch - full wizard flow."""
import json, time, base64
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

TOKEN = "d9a510da50682610be097d7ba21d520b"

# ─── Config ───
DESC = open("C:/Users/Lucas/.claude/skills/civitai-publisher/新建 文本文档.txt", encoding="utf-8").read().strip()
ZIP_PATH = Path("C:/Users/Lucas/Desktop/workflow_new.zip")
COVER_GIF = Path("C:/Users/Lucas/Desktop/新建文件夹 (21)/Civitai自动发布技术总结/新建文件夹/WanVideo2_1_multitalk_00001_p81-audio_qjvxc_1777650084_5mb.gif")

MODEL_NAME = "AI Singing Digital Human Lip Sync - RCM + Infinite Talk"
MODEL_TYPE = "Workflows"
BASE_MODEL = "Other"

# ─── API helpers ───
def api_post(path, data):
    r = httpx.post(
        f"https://civitai.com/api/trpc/{path}?batch=1",
        json=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=30
    )
    return r.json()

def api_get(path, params):
    r = httpx.get(
        f"https://civitai.com/api/trpc/{path}",
        params=params,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30
    )
    return r.json()

# ─── Step 1: Create model (Draft) ───
print("[1/5] Creating model...")
result = api_post("model.upsert", {"0": {"json": {
    "name": MODEL_NAME,
    "type": MODEL_TYPE,
    "uploadType": "Created",
    "status": "Draft",
    "description": DESC,
    "tags": ["AI", "SINGING", "DIGITAL", "HUMAN", "LIP", "SYNC", "AVATAR", "VIDEO", "RCM", "INFINITE", "TALK"],
    "nsfw": False,
    "poi": False,
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
    "modelId": model_id,
    "name": "v1.0",
    "baseModel": BASE_MODEL,
    "files": []
}}})
version_id = result[0]["result"]["data"]["json"]["id"]
print(f"  Version ID: {version_id}")

# ─── Step 3: Browser upload ZIP + preview image ───
print("[3/5] Opening browser for file + image upload...")

zip_b64 = base64.b64encode(ZIP_PATH.read_bytes()).decode()
print(f"  ZIP: {len(zip_b64)} chars base64")

# Convert GIF first frame to JPG for upload (smaller)
from PIL import Image
img = Image.open(COVER_GIF)
if img.mode in ('RGBA', 'LA', 'P', 'PA'):
    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
    if img.mode == 'P':
        img = img.convert('RGBA')
    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
    img = rgb_img
elif img.mode != 'RGB':
    img = img.convert('RGB')
# Resize if too large (max 2K in any dimension)
max_dim = 2000
if img.size[0] > max_dim or img.size[1] > max_dim:
    ratio = max_dim / max(img.size)
    img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)), Image.LANCZOS)
jpg_path = Path("C:/Users/Lucas/Desktop/cover_upload.jpg")
img.save(jpg_path, 'JPEG', quality=93, subsampling='4:4:4')
jpg_b64 = base64.b64encode(jpg_path.read_bytes()).decode()
print(f"  Cover JPG: {jpg_path.stat().st_size/1024:.0f} KB, {len(jpg_b64)} chars base64, dims: {img.size}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960})
    page = ctx.new_page()

    # Auth
    def auth(route):
        h = dict(route.request.headers)
        h["Authorization"] = f"Bearer {TOKEN}"
        route.continue_(headers=h)
    page.route("**://civitai.com/**", auth)
    page.route("**://*.civitai.com/**", auth)

    # ─── Upload ZIP at wizard step 3 ───
    step3_url = f"https://civitai.com/models/{model_id}/wizard?step=3&versionId={version_id}"
    print(f"  Navigating to step 3: {step3_url}")
    page.goto(step3_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    print(f"  URL: {page.url}")

    # Upload ZIP via React fiber onDrop
    result = page.evaluate("""
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

                let fiber = dz[fk];
                for (let d = 0; d < 15 && fiber; d++) {
                    const p = fiber.memoizedProps;
                    if (p && typeof p.onDrop === 'function') {
                        try {
                            p.onDrop([file]);
                            return JSON.stringify({success: true, depth: d});
                        } catch(e) {
                            return JSON.stringify({error: e.message, depth: d});
                        }
                    }
                    fiber = fiber.return;
                }
            }
            return JSON.stringify({error: 'no Dropzone found'});
        }
    """, {"b64": zip_b64, "filename": "workflow.zip", "mimeType": "application/zip"})
    print(f"  ZIP upload: {result}")

    page.wait_for_timeout(10000)

    # Click Next to go to step 4
    next_btn = page.locator('button:has-text("Next")').first
    if next_btn.is_visible():
        print("  Clicking Next -> step 4...")
        next_btn.click()
        page.wait_for_timeout(8000)
        print(f"  URL after Next: {page.url}")
    else:
        print("  Next button not found, trying to navigate directly...")
        page.goto(f"https://civitai.com/models/{model_id}/wizard?step=4&versionId={version_id}",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(10000)

    page.screenshot(path="C:/Users/Lucas/Desktop/wizard_step4.png")
    print("  Screenshot: wizard_step4.png")

    # ─── Step 4: Upload cover image ───
    # Look for image dropzone at step 4
    dropzones_count = page.locator('[class*="m_d46a4834"]').count()
    print(f"  Step 4 dropzones: {dropzones_count}")

    if dropzones_count > 0:
        result = page.evaluate("""
            async ({b64, filename, mimeType}) => {
                const bs = atob(b64);
                const bytes = new Uint8Array(bs.length);
                for (let i = 0; i < bs.length; i++) bytes[i] = bs.charCodeAt(i);
                const file = new File([bytes], filename, {type: mimeType});

                const dropzoneRoots = document.querySelectorAll(
                    '[class*="m_d46a4834"], [class*="mantine-Dropzone-root"]'
                );
                let tried = [];

                for (const dz of dropzoneRoots) {
                    const visible = !!dz.offsetParent;
                    const accept = dz.closest('[class*="Dropzone"]')?.getAttribute('accept') || 'none';
                    tried.push({visible, accept});
                    if (!visible) continue;

                    const fk = Object.keys(dz).find(k => k.startsWith('__reactFiber$'));
                    if (!fk) continue;

                    let fiber = dz[fk];
                    for (let d = 0; d < 20 && fiber; d++) {
                        const p = fiber.memoizedProps;
                        if (p && typeof p.onDrop === 'function') {
                            try {
                                p.onDrop([file]);
                                tried[tried.length-1].result = 'called onDrop depth=' + d;
                            } catch(e) {
                                tried[tried.length-1].result = 'error: ' + e.message;
                            }
                            break;
                        }
                        fiber = fiber.return;
                    }
                }
                return JSON.stringify(tried);
            }
        """, {"b64": jpg_b64, "filename": "cover.jpg", "mimeType": "image/jpeg"})
        print(f"  Image upload attempt: {result}")
        page.wait_for_timeout(8000)
    else:
        print("  No dropzones at step 4, checking page content...")
        body = page.locator('body').inner_text()
        print(f"  Page text (first 500): {body[:500]}")

    # Try to find any image upload section
    all_text = page.locator('body').inner_text()
    if 'image' in all_text.lower() or 'cover' in all_text.lower() or 'photo' in all_text.lower() or 'preview' in all_text.lower():
        print("  Found image-related text on page")

    # Click through remaining steps
    for i in range(2):
        try:
            nxt = page.locator('button:has-text("Next")').first
            if nxt.is_visible():
                print(f"  Clicking Next ({i+1})...")
                nxt.click()
                page.wait_for_timeout(5000)
        except:
            break

    # Final screenshot
    page.screenshot(path="C:/Users/Lucas/Desktop/wizard_final.png")
    print("  Final screenshot: wizard_final.png")

    browser.close()

# ─── Step 5: Publish ───
print(f"\n[5/5] Publishing model {model_id} / version {version_id}...")
r1 = api_post("modelVersion.publish", {"0": {"json": {"id": version_id}}})
print(f"  Version publish: {json.dumps(r1, ensure_ascii=False)[:200]}")

r2 = api_post("model.publish", {"0": {"json": {"id": model_id}}})
print(f"  Model publish: {json.dumps(r2, ensure_ascii=False)[:200]}")

print(f"\n=== Done! ===")
print(f"https://civitai.com/models/{model_id}")
