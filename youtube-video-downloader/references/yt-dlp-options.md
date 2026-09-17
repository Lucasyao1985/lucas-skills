# yt-dlp Format Selection Reference

## Format Selection Syntax

```
-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
```

- `bestvideo[ext=mp4]` — highest quality video stream in MP4 format
- `bestaudio[ext=m4a]` — highest quality audio stream in M4A format
- `/best[ext=mp4]` — fallback to best single-file MP4 if separate streams unavailable
- `+` merges video and audio into a single MP4 output

## Common Presets

| Preset | Command Fragment |
|--------|-----------------|
| Best MP4 (default) | `bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]` |
| Best available | `bestvideo+bestaudio/best` |
| 1080p MP4 | `bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]` |
| 720p MP4 | `bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]` |

## Useful Options

| Option | Purpose |
|--------|---------|
| `--merge-output-format mp4` | Force MP4 output after merge |
| `--no-playlist` | Download single video only |
| `--geo-bypass` | Bypass geographic restrictions |

## Platform Support

- YouTube (videos, Shorts, live streams)
- Vimeo, Dailymotion, Twitter/X, Instagram, TikTok, and 1000+ sites
