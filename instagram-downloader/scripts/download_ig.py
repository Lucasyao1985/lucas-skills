#!/usr/bin/env python3
"""
Instagram Profile Image Downloader
Downloads all images from a public Instagram profile using curl_cffi.
"""
import sys
import os
import re
import json
import time
import argparse
from urllib.parse import urlparse

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import curl_cffi.requests as requests
except ImportError:
    print("Error: curl_cffi not installed. Run: pip install curl_cffi")
    sys.exit(1)


def get_user_info(session, username, headers):
    """Resolve username to user ID and get post count."""
    resp = session.get(
        f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
        headers=headers
    )
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch user info: HTTP {resp.status_code}")
    
    data = resp.json()
    user = data.get('data', {}).get('user')
    if not user:
        raise Exception(f"User '{username}' not found or profile is private")
    
    return {
        'id': user['id'],
        'username': user['username'],
        'post_count': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
        'is_private': user.get('is_private', False),
    }


def fetch_all_posts(session, user_id, headers):
    """Fetch all posts using the v1 feed API with pagination."""
    all_items = []
    max_id = ''
    page = 0
    
    while True:
        page += 1
        url = f'https://www.instagram.com/api/v1/feed/user/{user_id}/'
        if max_id:
            url += f'?max_id={max_id}'
        
        resp = session.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"  Page {page} error: HTTP {resp.status_code}")
            break
        
        data = resp.json()
        items = data.get('items', [])
        more = data.get('more_available', False)
        max_id = data.get('next_max_id', '')
        
        print(f"  Page {page}: {len(items)} posts")
        all_items.extend(items)
        
        if not more or not max_id:
            break
        time.sleep(1)
    
    return all_items


def download_image(session, url, filename, save_dir):
    """Download a single image file."""
    filepath = os.path.join(save_dir, filename)
    if os.path.exists(filepath):
        return False, 0  # Already exists
    
    try:
        r = session.get(url)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return True, len(r.content)
        return False, 0
    except Exception as e:
        print(f"    Error downloading {filename}: {e}")
        return False, 0


def download_video(session, url, filename, save_dir):
    """Download a single video file."""
    filepath = os.path.join(save_dir, filename)
    if os.path.exists(filepath):
        return False, 0
    
    try:
        r = session.get(url)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return True, len(r.content)
        return False, 0
    except Exception as e:
        print(f"    Error downloading {filename}: {e}")
        return False, 0


def extract_username(url):
    """Extract username from Instagram URL."""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    # Handle various URL formats
    if path.startswith('p/'):
        return None  # Single post URL
    username = path.split('/')[0]
    # Remove query params
    username = username.split('?')[0]
    return username


def main():
    parser = argparse.ArgumentParser(description='Download all images from an Instagram profile')
    parser.add_argument('url', help='Instagram profile URL (e.g., https://www.instagram.com/username/)')
    parser.add_argument('save_dir', help='Directory to save images')
    parser.add_argument('--prefix', default='', help='Filename prefix (optional)')
    parser.add_argument('--videos', action='store_true', help='Also download videos (default: skip)')
    parser.add_argument('--no-images', action='store_true', help='Skip images, only download videos')
    args = parser.parse_args()
    
    username = extract_username(args.url)
    if not username:
        print("Error: Please provide a profile URL, not a single post URL")
        sys.exit(1)
    
    save_dir = args.save_dir
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Instagram Downloader - @{username}")
    print(f"Save to: {save_dir}")
    print()
    
    # Initialize session
    session = requests.Session(impersonate='chrome120')
    session.get('https://www.instagram.com/')
    
    headers = {
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    # Get user info
    print("Fetching user info...")
    user = get_user_info(session, username, headers)
    print(f"  User: @{user['username']}")
    print(f"  Posts: {user['post_count']}")
    
    if user['is_private']:
        print("\nError: This profile is private. Cannot download.")
        sys.exit(1)
    
    # Fetch all posts
    print("\nFetching posts...")
    posts = fetch_all_posts(session, user['id'], headers)
    print(f"  Total: {len(posts)} posts fetched")
    
    # Download
    print("\nDownloading...")
    downloaded = 0
    skipped = 0
    errors = 0
    total_bytes = 0
    
    for item in posts:
        code = item.get('code', '')
        media_type = item.get('media_type', 0)
        prefix = args.prefix
        
        if media_type == 8:  # Carousel/Album
            carousel = item.get('carousel_media', [])
            for idx, car in enumerate(carousel):
                car_type = car.get('media_type', 0)
                
                if car_type == 2:  # Video in carousel
                    if args.videos:
                        vs = car.get('video_versions', [])
                        if vs:
                            best_v = max(vs, key=lambda x: x.get('width', 0) * x.get('height', 0))
                            url = best_v['url']
                            filename = f'{prefix}{code}_v{idx}.mp4'
                            ok, size = download_video(session, url, filename, save_dir)
                            if ok:
                                downloaded += 1
                                total_bytes += size
                                print(f"  {filename} ({size // 1024}KB)")
                            else:
                                skipped += 1
                            time.sleep(0.3)
                    else:
                        skipped += 1
                    continue
                
                # Image in carousel
                if args.no_images:
                    skipped += 1
                    continue
                
                candidates = car.get('image_versions2', {}).get('candidates', [])
                if not candidates:
                    skipped += 1
                    continue
                
                best = max(candidates, key=lambda x: x.get('width', 0) * x.get('height', 0))
                filename = f'{prefix}{code}_{idx}.jpg'
                ok, size = download_image(session, best['url'], filename, save_dir)
                if ok:
                    downloaded += 1
                    total_bytes += size
                    print(f"  {filename} ({size // 1024}KB)")
                else:
                    skipped += 1
                time.sleep(0.3)
        
        elif media_type == 1:  # Single image
            if args.no_images:
                skipped += 1
                continue
            
            candidates = item.get('image_versions2', {}).get('candidates', [])
            if not candidates:
                skipped += 1
                continue
            
            best = max(candidates, key=lambda x: x.get('width', 0) * x.get('height', 0))
            filename = f'{prefix}{code}.jpg'
            ok, size = download_image(session, best['url'], filename, save_dir)
            if ok:
                downloaded += 1
                total_bytes += size
                print(f"  {filename} ({size // 1024}KB)")
            else:
                skipped += 1
            time.sleep(0.3)
        
        elif media_type == 2:  # Video
            if args.videos:
                vs = item.get('video_versions', [])
                if vs:
                    best_v = max(vs, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    url = best_v['url']
                    filename = f'{prefix}{code}.mp4'
                    ok, size = download_video(session, url, filename, save_dir)
                    if ok:
                        downloaded += 1
                        total_bytes += size
                        print(f"  {filename} ({size // 1024}KB)")
                    else:
                        skipped += 1
                    time.sleep(0.3)
            else:
                skipped += 1
        
        else:
            skipped += 1
    
    # Summary
    size_str = f"{total_bytes // (1024*1024)} MB" if total_bytes > 1024*1024 else f"{total_bytes // 1024} KB"
    print(f"\n{'='*40}")
    print(f"Done!")
    print(f"  Downloaded: {downloaded} files")
    print(f"  Skipped: {skipped}")
    print(f"  Total size: {size_str}")
    print(f"  Saved to: {save_dir}")


if __name__ == '__main__':
    main()
