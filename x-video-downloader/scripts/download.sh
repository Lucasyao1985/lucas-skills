#!/bin/bash
# X/Twitter media downloader (fallback for single direct URL; prefer extract_media.py)
# Usage: bash download.sh <media_url> <save_path>

MEDIA_URL="$1"
SAVE_PATH="$2"

if [ -z "$MEDIA_URL" ] || [ -z "$SAVE_PATH" ]; then
    echo "Usage: bash download.sh <media_url> <save_path>"
    exit 1
fi

mkdir -p "$(dirname "$SAVE_PATH")"

curl -L --retry 2 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -o "$SAVE_PATH" "$MEDIA_URL"

if [ -f "$SAVE_PATH" ]; then
    FILE_SIZE=$(stat --format=%s "$SAVE_PATH" 2>/dev/null || stat -f%z "$SAVE_PATH" 2>/dev/null)
    if [ "${FILE_SIZE:-0}" -gt 0 ]; then
        echo "Download complete: $SAVE_PATH ($FILE_SIZE bytes)"
    else
        echo "Download failed: file is empty"
        exit 1
    fi
else
    echo "Download failed"
    exit 1
fi
