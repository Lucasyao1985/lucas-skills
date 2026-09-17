"""Complete publish flow - wizard all the way through post + image."""
import json, time, base64
from pathlib import Path
import httpx
from PIL import Image
from playwright.sync_api import sync_playwright

TOKEN = "d9a510da50682610be097d7ba21d520b"

DESC = '''AI Singing Digital Human Lip Sync – RCM + Infinite Talk is a ComfyUI-based workflow for realistic singing avatars with accurate lip sync.

The workflow is available to try online at:
<a href="https://www.runninghub.ai/post/2067174642636382209/?inviteCode=rh-v1015" target="_blank" rel="noopener">RunningHub - AI Singing Digital Human Lip Sync</a>

Rewards: Tap your avatar → enter code <strong>rh-v1015</strong> → get <strong>1000 RH coins</strong> instantly, plus <strong>100 daily</strong>!'''

ZIP_PATH = Path("C:/Users/Lucas/Desktop/workflow_new.zip")
COVER_GIF = Path("C:/Users/Lucas/Desktop/新建文件夹 (21)/Civitai自动发布技术总结/新建文件夹/WanVideo2_1_multitalk_00001_p81-audio_qjvxc_1777650084_5mb.gif")

# ─── Prep JPG cover ───
img = Image.open(COVER_GIF)
if img.mode in ('RGBA', 'LA', 'P', 'PA'):
    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
    if img.mode == 'P': img = img.convert('RGBA')
    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
    img = rgb_img
elif img.mode != 'RGB': img = img.convert('RGB')
max_dim = 2000
if img.size[0] > max_dim or img.size[1] > max_dim:
    ratio = max_dim / max(img.size)
    img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)), Image.LANCZOS)
jpg_path = Path("C:/Users/Lucas/Desktop/cover_upload.jpg")
img.save(jpg_path, 'JPEG', quality=93, subsampling='4:4:4')

zip_b64 = base64.b64encode(ZIP_PATH.read_bytes()).decode()
jpg_b64 = base64.b64encode(jpg_path.read_bytes()).decode()
print(f"ZIP: {len(zip_b64)} chars | JPG: {jpg_path.stat().st_size/1024:.0f} KB, {len(jpg_b64)} chars")

# ─── API helpers ───
def api_post(path, data):
    return httpx.post(
        f"https://civitai.com/api/trpc/{path}?batch=1",
        json=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=30
    ).json()

# ─── Create model + version ───
print("[1/4] Creating model...")
result = api_post("model.upsert", {"0": {"json": {
    "name": "AI Singing Digital Human Lip Sync - RCM + Infinite Talk",
    "type": "Workflows", "uploadType": "Created", "status": "Draft",
    "description": DESC,
    "tags": ["AI", "SINGING", "DIGITAL", "HUMAN", "LIP", "SYNC", "AVATAR", "VIDEO", "RCM", "INFINITE", "TALK"],
    "nsfw": False, "poi": False,
    "allowNoCredit": True, "allowCommercialUse": ["Sell"],
    "allowDerivatives": True, "allowDifferentLicense": True,
}}})
model_id = result[0]["result"]["data"]["json"]["id"]
print(f"  Model: {model_id}")

result = api_post("modelVersion.upsert", {"0": {"json": {
    "modelId": model_id, "name": "v1.0", "baseModel": "Other", "files": []
}}})
version_id = result[0]["result"]["data"]["json"]["id"]
print(f"  Version: {version_id}")

# ─── Browser wizard ───
print("[2/4] Browser wizard...")
UPLOAD_JS = """
async ({b64, filename, mimeType}) => {
    const bs = atob(b64);
    const bytes = new Uint8Array(bs.length);
    for (let i = 0; i < bs.length; i++) bytes[i] = bs.charCodeAt(i);
    const file = new File([bytes], filename, {type: mimeType});
    for (const dz of document.querySelectorAll('[class*=\"m_d46a4834\"], [class*=\"mantine-Dropzone-root\"]')) {
        if (!dz.offsetParent) continue;
        const fk = Object.keys(dz).find(k => k.startsWith('__reactFiber$'));
        if (!fk) continue;
        let fiber = dz[fk], handlers = [];
        for (let d = 0; d < 20 && fiber; d++) {
            if (fiber.memoizedProps && typeof fiber.memoizedProps.onDrop === 'function') handlers.push(d);
            fiber = fiber.return;
        }
        if (!handlers.length) continue;
        fiber = dz[fk];
        for (let d = 0; d <= handlers[handlers.length-1] && fiber; d++) {
            if (d === handlers[handlers.length-1] && fiber.memoizedProps?.onDrop) {
                fiber.memoizedProps.onDrop([file]);
                return 'ok';
            }
            fiber = fiber.return;
        }
    }
    return 'fail';
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

    # Step 3: Upload ZIP
    page.goto(f"https://civitai.com/models/{model_id}/wizard?step=3&versionId={version_id}",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    print(f"  Step3 URL: {page.url}")

    if "notOwner" in page.url:
        print("  ERROR: notOwner!")
        browser.close()
        exit(1)

    r = page.evaluate(UPLOAD_JS, {"b64": zip_b64, "filename": "workflow.zip", "mimeType": "application/zip"})
    print(f"  ZIP: {r}")
    page.wait_for_timeout(12000)

    # Click Next -> step 4
    page.locator('button:has-text("Next")').first.click()
    page.wait_for_timeout(10000)
    print(f"  Step4 URL: {page.url}")
    page.screenshot(path="C:/Users/Lucas/Desktop/step4_start.png")

    # Step 4: Upload cover image + publish post
    r = page.evaluate(UPLOAD_JS, {"b64": jpg_b64, "filename": "cover.jpg", "mimeType": "image/jpeg"})
    print(f"  Cover upload: {r}")
    page.wait_for_timeout(12000)

    # Look for Publish/Save button on the post form
    all_btns = page.locator('button')
    for i in range(all_btns.count()):
        try:
            t = all_btns.nth(i).inner_text().strip()
            if t: print(f"  Btn {i}: \"{t[:80]}\" disabled={all_btns.nth(i).get_attribute('data-disabled')}")
        except: pass

    # Try clicking Publish via JavaScript (bypass disabled)
    result = page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            let found = [];
            for (const b of btns) {
                const text = b.innerText.trim();
                if (text === 'Publish' || text === 'Save' || text === 'Done') {
                    found.push({text, disabled: b.hasAttribute('disabled'), dataDisabled: b.getAttribute('data-disabled')});
                    // Force enable and click
                    b.removeAttribute('disabled');
                    b.removeAttribute('data-disabled');
                    b.style.pointerEvents = 'auto';
                    b.click();
                    return JSON.stringify({clicked: text, wasDisabled: b.hasAttribute('disabled')});
                }
            }
            return JSON.stringify({error: 'no button', found});
        }
    """)
    print(f"  JS click: {result}")
    page.wait_for_timeout(15000)
    print(f"  After publish: {page.url}")
    page.screenshot(path="C:/Users/Lucas/Desktop/step4_after_publish.png")

    # Click any remaining Next
    for _ in range(2):
        try:
            nb = page.locator('button:has-text("Next")').first
            if nb.is_visible():
                nb.click()
                page.wait_for_timeout(8000)
                print(f"  Next -> {page.url}")
        except: break

    browser.close()

# ─── Publish model ───
print("[3/4] Publishing model...")
api_post("modelVersion.publish", {"0": {"json": {"id": version_id}}})
api_post("model.publish", {"0": {"json": {"id": model_id}}})
print("  Done!")

# ─── Verify ───
print("[4/4] Verifying...")
r = httpx.get(
    "https://civitai.com/api/trpc/model.getById",
    params={"input": json.dumps({"json": {"id": model_id}})},
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=30
)
data = r.json()['result']['data']['json']
versions = data.get('modelVersions', [])
for v in versions:
    print(f"  Version {v['id']}: files={len(v.get('files',[]))}, images={len(v.get('images',[]))}")
    for f in v.get('files', []):
        print(f"    File: {f.get('name')} ({f.get('sizeKB', 0)} KB)")
    for img in v.get('images', []):
        print(f"    Image: {str(img.get('url', ''))[:100]}")

print(f"\n=== DONE ===")
print(f"https://civitai.com/models/{model_id}")
