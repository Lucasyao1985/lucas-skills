"""Update CivitAI model 2706885: description + cover image."""
import json, time, base64, sys
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

TOKEN = "d9a510da50682610be097d7ba21d520b"
MODEL_ID = 2706885
VERSION_ID = 3040285

# File paths
DESC_FILE = Path("C:/Users/Lucas/.claude/skills/civitai-publisher/新建 文本文档.txt")
COVER_GIF = Path("C:/Users/Lucas/Desktop/openclaw-zero-token-main/WanVideo2_1_multitalk_00001_p81-audio_qjvxc_1777650084_5mb.gif")

# Read new description
new_description = DESC_FILE.read_text(encoding="utf-8").strip()
print(f"=== New Description ({len(new_description)} chars) ===")
print(new_description[:300])

print(f"\n=== Cover GIF: {COVER_GIF} ({COVER_GIF.stat().st_size / 1024:.0f} KB) ===")

# ─── Step 1: Update model description via API ───
print("\n[Step 1] Updating model description via API...")

r = httpx.post(
    f"https://civitai.com/api/trpc/model.upsert?batch=1",
    json={"0": {"json": {
        "id": MODEL_ID,
        "name": "AI Singing Digital Human Lip Sync - RCM + Infinite Talk",
        "type": "Workflows",
        "uploadType": "Created",
        "status": "Published",
        "description": new_description,
        "nsfw": False,
        "poi": False,
        "allowNoCredit": True,
        "allowCommercialUse": ["Sell"],
        "allowDerivatives": True,
        "allowDifferentLicense": True,
    }}},
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    timeout=30
)
print(f"Status: {r.status_code}")
result = r.json()
print(f"Result: {json.dumps(result, ensure_ascii=False)[:500]}")

# ─── Step 2: Upload cover image via browser ───
print("\n[Step 2] Uploading cover image via browser...")

# Read GIF as base64
gif_bytes = COVER_GIF.read_bytes()
gif_b64 = base64.b64encode(gif_bytes).decode()
print(f"GIF base64 length: {len(gif_b64)}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960})
    page = ctx.new_page()

    # Auth via route interception
    def auth(route):
        h = dict(route.request.headers)
        h["Authorization"] = f"Bearer {TOKEN}"
        route.continue_(headers=h)

    page.route("**://civitai.com/**", auth)
    page.route("**://*.civitai.com/**", auth)

    # Navigate to model edit page (step 3 = media/images)
    edit_url = f"https://civitai.com/models/{MODEL_ID}/wizard?step=3&versionId={VERSION_ID}"
    print(f"Navigating to: {edit_url}")
    page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)

    # Check page state
    print(f"Page title: {page.title()}")
    print(f"Current URL: {page.url}")

    # Look for image upload dropzone
    # Try to find the image upload area and upload the GIF
    result = page.evaluate("""
        async ({b64, filename, mimeType}) => {
            const bs = atob(b64);
            const bytes = new Uint8Array(bs.length);
            for (let i = 0; i < bs.length; i++) bytes[i] = bs.charCodeAt(i);
            const file = new File([bytes], filename, {type: mimeType});

            // Find ALL Mantine Dropzone roots
            const dropzoneRoots = document.querySelectorAll(
                '[class*="m_d46a4834"], [class*="mantine-Dropzone-root"]'
            );
            const results = [];

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
                            results.push({success: true, depth: d, className: dz.className});
                        } catch(e) {
                            results.push({error: e.message, depth: d});
                        }
                        break;
                    }
                    fiber = fiber.return;
                }
            }
            return JSON.stringify(results);
        }
    """, {"b64": gif_b64, "filename": "cover.gif", "mimeType": "image/gif"})

    print(f"Upload result: {result}")
    page.wait_for_timeout(10000)

    # Try to click Next/Save if available
    try:
        next_btn = page.locator('button:has-text("Next")').first
        if next_btn.is_visible():
            print("Clicking Next...")
            next_btn.click()
            page.wait_for_timeout(5000)

            # Step 4 - maybe another Next
            next_btn2 = page.locator('button:has-text("Next")').first
            if next_btn2.is_visible():
                print("Clicking Next again...")
                next_btn2.click()
                page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Next button handling: {e}")

    # Take screenshot for debugging
    page.screenshot(path="C:/Users/Lucas/Desktop/civitai_update_screenshot.png")
    print("Screenshot saved to Desktop")

    browser.close()

print("\n=== Done! ===")
print(f"Check: https://civitai.com/models/{MODEL_ID}")
