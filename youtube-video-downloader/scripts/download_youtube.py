#!/usr/bin/env python3
"""YouTube video downloader using yt-dlp."""
import sys
import os
import subprocess
import json
from pathlib import Path


def download(url: str, output_path: str) -> dict:
    """Download a YouTube video to the specified output path."""
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "-o", output_path,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main():
    if len(sys.argv) < 3:
        print("Usage: python download_youtube.py <url> <output_path>")
        sys.exit(1)

    url = sys.argv[1]
    output_path = sys.argv[2]

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    result = download(url, output_path)
    print(result["stdout"])
    if result["stderr"]:
        print(result["stderr"], file=sys.stderr)
    sys.exit(result["returncode"])


if __name__ == "__main__":
    main()
