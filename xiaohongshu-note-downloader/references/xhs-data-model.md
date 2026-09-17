# Xiaohongshu `__INITIAL_STATE__` Data Model

Everything comes from one object embedded in the note page HTML:

```python
raw = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', html, re.S).group(1)
raw = re.sub(r'\bundefined\b', 'null', raw)     # REQUIRED: XHS emits bare `undefined`
state = json.loads(raw)
```

Skipping the `undefined` substitution raises `json.JSONDecodeError`. That is the single most
common parse failure.

## Where the note lives

```
state
└── note
    └── noteDetailMap
        └── "<noteId>"          # 24 hex chars
            ├── note            # the payload you want
            ├── comments        # comment list (first page only)
            ├── currentTime
            └── seoRobots
```

```python
detail = state["note"]["noteDetailMap"]
note_id = next(iter(detail))
note = detail[note_id]["note"]
```

Note: `noteDetailMap` is **empty** when the note is not accessible. Treat that as a hard error,
not as "a note with no content".

## Note object fields

| Field | Type | Notes |
|---|---|---|
| `noteId` | str | 24 hex chars, same as the map key |
| `type` | str | `"normal"` = image note, `"video"` = video note |
| `title` | str | may be empty; fall back to `desc` |
| `desc` | str | body text, `\n` and `\t` separated |
| `time` | int | publish time, **milliseconds** |
| `lastUpdateTime` | int | milliseconds |
| `user` | obj | `userId`, `nickname`, `avatar`, `xsecToken` |
| `interactInfo` | obj | `likedCount`, `collectedCount`, `commentCount`, `shareCount` |
| `tagList` | list | `[{id, name, type}]`, `type` is usually `"topic"` |
| `imageList` | list | images, or a single cover frame on video notes |
| `video` | obj | **only on `type == "video"`** |
| `xsecToken` | str | the note's own token |
| `shareInfo` | obj | share link metadata |

## `imageList[i]`

```json
{
  "fileId": "spectrum/1040g0k0320e8r84llk005prkofb63o2l8kap6co",
  "width": 1086,
  "height": 1448,
  "url": "",
  "urlPre":    "http://sns-webpic-qc.xhscdn.com/<ts>/<hash>/spectrum/<id>!nd_prv_wlteh_webp_3",
  "urlDefault":"http://sns-webpic-qc.xhscdn.com/<ts>/<hash>/spectrum/<id>!nd_dft_wlteh_webp_3",
  "infoList": [{"imageScene": "WB_PRV", "url": "..."}, {"imageScene": "WB_DFT", "url": "..."}],
  "livePhoto": false,
  "stream": {}
}
```

- `urlPre` / `urlDefault` / `infoList[].url` are all **watermarked thumbnails** (measured 376 KB
  for an image whose original is 2.4 MB).
- `fileId` is the only field you need: `https://sns-img-qc.xhscdn.com/<fileId>` returns the
  original, un-watermarked file. Confirmed working mirrors: `sns-img-bd.xhscdn.com`,
  `ci.xiaohongshu.com`.
- `sns-webpic-qc.xhscdn.com/<fileId>` (fileId with no timestamp prefix) returns **403**.
- `width`/`height` here are the thumbnail's dimensions and can be smaller than the original.
  Read the real size from the downloaded file instead.

## `video` (video notes only)

Top-level keys: `capa`, `media`, `mediaV2`, `image`.

```
note.video
├── capa            {"duration": 22}
├── image           {"thumbnailFileid": "frame/110/0/<hash>_0.webp"}
├── mediaV2         JSON *string* (not an object) — video_id, biz_name, duration, md5,
│                   width, height, stream_types[], opaque1{...}
└── media
    ├── videoId
    ├── video
    └── stream
        ├── h264  [ ... ]
        ├── h265  [ ... ]
        ├── h266  [ ]      often empty
        └── av1   [ ]      often empty
```

`mediaV2` is a **string**; you must `json.loads` it again. It is metadata only — the playable
URLs are in `media.stream`.

### `media.stream.<codec>[]` entries

```json
{
  "masterUrl":  "http://sns-video-qc.xhscdn.com/stream/1/110/109/<hash>_109.mp4?sign=<sig>&t=6aa9b5dc",
  "backupUrls": ["http://sns-bak-v6.xhscdn.com/stream/1/110/109/<hash>_109.mp4"],
  "width": 2160, "height": 3840,
  "duration": 22756, "videoDuration": 22755,
  "size": 10522017,
  "videoCodec": "hevc",       // "h264" for the h264 bucket
  "audioCodec": "aac",
  "format": "mp4",
  "qualityType": "HD",
  "streamDesc": "WEB_109",
  "videoBitrate": ..., "audioBitrate": ..., "fps": ...,
  "hdrType": 0, "rotate": 0, "weight": 62, "defaultStream": false
}
```

Real measured ladder from one note (`duration` 22.8 s throughout):

| codec | resolution | size | streamDesc |
|---|---|---|---|
| h264 | 720x1280 | 2.63 MB | WEB_259 |
| h265 | 720x1280 | 2.88 MB | WEB_309 |
| h265 | 1080x1920 | 3.46 MB | WEB_301 |
| h265 | 1440x2560 | 6.29 MB | WEB_108 |
| h265 | 2160x3840 | 10.52 MB | WEB_109 |

**`h264` carries only the single 720p entry.** Everything above 720p lives under `h265`. So
"best quality" and "most compatible" are genuinely different picks, not the same file.

### Practical rules

- `masterUrl` carries `?sign=...&t=<hex unix ts>`. The `t` is a hex-encoded timestamp, so the
  link is **time-limited**. `backupUrls[0]` is unsigned and stable — try it first.
- Audio is **muxed into the same MP4** (AAC). Never look for a separate audio stream.
- The video is served from `sns-video-qc.xhscdn.com` / `sns-bak-v6.xhscdn.com`, which are
  reachable **directly** — no proxy needed.
- For video notes, `imageList` holds exactly one entry: the cover frame. Its `fileId` gives the
  original cover, which is better quality than `video.image.thumbnailFileid` (a `.webp` frame).

## Other top-level state keys (usually not needed)

`global`, `user`, `login`, `feed`, `search`, `layout`, `activity`, `liveList`, `notification`.
The `feed` store looks tempting for enumerating notes, but on a note page it is empty and the
home feed requires signed API calls — do not go down that path.
