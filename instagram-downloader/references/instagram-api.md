# Instagram API Reference

## Authentication

Instagram's internal web API requires:
- Session cookies (obtained by visiting the homepage)
- `X-IG-App-ID: 936619743392459` header
- `X-Requested-With: XMLHttpRequest` header

No login required for public profiles.

## Endpoints

### Get User Info
```
GET /api/v1/users/web_profile_info/?username={username}
```
Returns user profile data including user ID and post count.

### Get User Feed (Posts)
```
GET /api/v1/feed/user/{user_id}/
GET /api/v1/feed/user/{user_id}/?max_id={max_id}
```
Returns paginated list of posts. `max_id` is from previous response's `next_max_id`.

### Response Structure

#### Feed Response
```json
{
  "items": [...],
  "more_available": true,
  "next_max_id": "3913489815862109758_1440536967"
}
```

#### Item (Post) Structure
```json
{
  "pk": 1234567890,
  "code": "SHORTCODE",
  "media_type": 1,          // 1=image, 2=video, 8=carousel
  "image_versions2": {
    "candidates": [
      {
        "width": 1080,
        "height": 1350,
        "url": "https://..."
      }
    ]
  },
  "video_versions": [...]    // Only for video posts
  "carousel_media": [...]    // Only for carousel posts
}
```

#### Media Types
| Type | Value | Description |
|------|-------|-------------|
| Image | 1 | Single image post |
| Video | 2 | Single video post |
| Carousel | 8 | Album/multi-image post |

## Rate Limiting

- Instagram may return 429 (Too Many Requests) if too many requests are made
- Recommended: 1 second delay between page fetches, 0.3 seconds between image downloads
- If rate limited, increase delays to 2-3 seconds

## TLS Fingerprinting

Instagram detects automated requests by TLS fingerprint. Use `curl_cffi` with `impersonate='chrome120'` to simulate a real browser.

## Common Issues

1. **401 Unauthorized**: Session cookies expired; re-visit homepage
2. **Empty candidates**: Post may be a video-only post
3. **Private profile**: API returns limited data; cannot download
4. **Encoding errors on Windows**: Use `sys.stdout.reconfigure(encoding='utf-8')`
