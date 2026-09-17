---
name: instagram-downloader
description: '下载 Instagram 用户的全部图片/视频。使用 curl_cffi 绕过反爬，通过 Instagram API 分页获取全部帖子，下载最高质量图片。Trigger: "下载Instagram" "Instagram下载" "instagram download" "ig下载" "下载ig" "instagram图片下载" "instagram全套下载"'
license: MIT
metadata:
  version: 1.0.0
  author: Lucas
  requires:
    bins:
      - python
    pip_packages:
      - curl_cffi
    os:
      - win32
      - darwin
      - linux
---

# Instagram Downloader

Downloads all images (and optionally videos) from an Instagram profile using `curl_cffi` to bypass bot detection, accessing Instagram's internal API directly.

## Environment Requirements

- Python 3.8+ (system Python: `D:\Conda\python.exe`)
- `curl_cffi` package (`pip install curl_cffi`)
- Default save location: user-specified directory

## Why curl_cffi

Instagram blocks standard HTTP clients and headless browsers with bot detection. `curl_cffi` simulates real browser TLS fingerprints (Chrome 120), allowing direct access to Instagram's internal API without login.

## How It Works

1. Initialize a `curl_cffi` session with Chrome 120 fingerprint
2. Visit Instagram homepage to obtain session cookies
3. Use `/api/v1/feed/user/{user_id}/` endpoint to paginate through all posts
4. For each post, extract image URLs from `image_versions2.candidates` (highest resolution)
5. For carousel posts, download each image separately
6. Download and save as JPG files

## Workflow

### Step 1: Get User ID

First, resolve the username to a user ID:

```python
import curl_cffi.requests as requests

session = requests.Session(impersonate='chrome120')
session.get('https://www.instagram.com/')

headers = {
    'X-IG-App-ID': '936619743392459',
    'X-Requested-With': 'XMLHttpRequest',
}

resp = session.get(
    'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
    headers=headers
)
user = resp.json()['data']['user']
user_id = user['id']
post_count = user['edge_owner_to_timeline_media']['count']
```

### Step 2: Paginate Through All Posts

```python
all_items = []
max_id = ''

while True:
    url = f'https://www.instagram.com/api/v1/feed/user/{user_id}/'
    if max_id:
        url += f'?max_id={max_id}'
    
    resp = session.get(url, headers=headers)
    data = resp.json()
    items = data.get('items', [])
    more = data.get('more_available', False)
    max_id = data.get('next_max_id', '')
    
    all_items.extend(items)
    
    if not more or not max_id:
        break
    time.sleep(1)  # Rate limiting
```

### Step 3: Extract and Download Images

For each post, determine type and download:

- **Single image** (`media_type == 1`): Download `image_versions2.candidates` highest resolution
- **Carousel/Album** (`media_type == 8`): Download each `carousel_media` item's image
- **Video** (`media_type == 2`): Skip (or download if `--videos` flag)

```python
for item in all_items:
    code = item.get('code', '')
    media_type = item.get('media_type', 0)
    
    if media_type == 1:  # Single image
        candidates = item.get('image_versions2', {}).get('candidates', [])
        best = max(candidates, key=lambda x: x.get('width', 0) * x.get('height', 0))
        download_image(session, best['url'], f'{code}.jpg', save_dir)
    
    elif media_type == 8:  # Carousel
        for idx, car in enumerate(item.get('carousel_media', [])):
            if car.get('media_type') == 2:
                continue  # Skip videos in carousel
            candidates = car.get('image_versions2', {}).get('candidates', [])
            best = max(candidates, key=lambda x: x.get('width', 0) * x.get('height', 0))
            download_image(session, best['url'], f'{code}_{idx}.jpg', save_dir)
```

### Step 4: Verify and Report

```python
image_files = [f for f in os.listdir(save_dir) if f.endswith('.jpg')]
total_size = sum(os.path.getsize(os.path.join(save_dir, f)) for f in image_files)
```

## Usage

```bash
# Download all images from a profile
python scripts/download_ig.py https://www.instagram.com/username/ /path/to/save

# Download with custom filename prefix
python scripts/download_ig.py https://www.instagram.com/username/ /path/to/save --prefix "ig_"

# Download images only (default, skip videos)
python scripts/download_ig.py https://www.instagram.com/username/ /path/to/save
```

## Output Format

```
✅ Instagram 下载完成
- 用户：@{username}
- 帖子数：{total_posts}
- 下载图片：{downloaded} 张
- 跳过视频：{skipped} 个
- 总大小：{total_size}
- 保存位置：{save_dir}
```

## Error Handling

| Error | Handling |
|-------|----------|
| 401 Unauthorized | Instagram may require login; try refreshing session cookies |
| Rate limiting (429) | Increase sleep between requests to 2-3 seconds |
| curl_cffi not installed | `pip install curl_cffi` |
| Private profile | Report that profile is private and cannot be downloaded |
| No posts found | Verify username is correct and profile is public |
| Network timeout | Retry once with longer timeout |
| GBK encoding error | Use `sys.stdout.reconfigure(encoding='utf-8')` on Windows |

## Supported URL Formats

- `https://www.instagram.com/username/`
- `https://www.instagram.com/username/?g=5`
- `https://www.instagram.com/p/SHORTCODE/` (single post)

## Limitations

- **Public profiles only** — Private profiles require authenticated session
- **No login required** — Uses unauthenticated API access
- **Videos skipped by default** — Use `--videos` flag to include video download
- **Rate limiting** — Instagram may throttle requests; script includes 1s delay between pages

## References

- `references/instagram-api.md` — Instagram API endpoints and parameters
