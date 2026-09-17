#!/usr/bin/env python3
r"""
LinkedIn Job Search Pipeline - Full workflow
  1. search  -> matched_jobs.json (fresh search results)
  2. expire-check -> expired_ids.json (mark dead listings)
  3. html-gen -> filtered HTML page for desktop

Usage:
  D:\Conda\python.exe pipeline.py                    # full pipeline
  D:\Conda\python.exe pipeline.py --skip-search      # skip search, use cached JSON
  D:\Conda\python.exe pipeline.py --output-dir PATH  # custom output dir
"""

import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent
DESKTOP_DIR = Path(r"C:\Users\Lucas\Desktop\415\领英自动化职位搜索")
PYTHON = r"D:\Conda\python.exe"
SEARCH_SCRIPT = SKILL_DIR / "search.py"
EXPIRE_SCRIPT = SKILL_DIR / "check_expired.py"
HTML_SCRIPT = SKILL_DIR / "gen_html.py"
CHECK_RESPONSES_SCRIPT = SKILL_DIR / "check_responses.py"


def step(name, script, *args):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    cmd = [PYTHON, str(script)] + list(args)
    result = subprocess.run(cmd, cwd=str(SKILL_DIR))
    if result.returncode != 0:
        print(f"  WARNING: {name} exited with code {result.returncode}")
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job Search Pipeline")
    parser.add_argument("--skip-search", action="store_true", help="Skip fresh search")
    parser.add_argument("--check-responses", action="store_true", help="Also check applied/saved jobs")
    parser.add_argument("--output-dir", type=str, default=str(DESKTOP_DIR), help="Output directory for HTML")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    matched_json = SKILL_DIR / "matched_jobs.json"

    print("=" * 60)
    print("  LinkedIn Job Search Pipeline")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Skill dir: {SKILL_DIR}")
    print(f"  Output dir: {args.output_dir}")
    print("=" * 60)

    # Step 1: Search
    if not args.skip_search:
        # Clear old expired cache — fresh search means fresh validation
        expired_json = SKILL_DIR / "expired_ids.json"
        if expired_json.exists():
            expired_json.unlink()
            print("  Cleared old expired_ids.json cache")
        step("Step 1/3: Search LinkedIn", SEARCH_SCRIPT)
    else:
        print("\n  Step 1/3: SKIPPED (using cached matched_jobs.json)")

    if not matched_json.exists():
        print("\n  ERROR: matched_jobs.json not found. Run search first.")
        sys.exit(1)

    # Step 2: Check expired
    step("Step 2/3: Check expired listings", EXPIRE_SCRIPT)

    # Step 3: Generate HTML
    step("Step 3/3: Generate HTML", HTML_SCRIPT)

    # Step 4 (optional): Check applied/saved jobs
    if args.check_responses:
        step("Step 4/4: Check applied/saved jobs", CHECK_RESPONSES_SCRIPT, "--json-only")
        # Re-generate HTML with cross-reference data
        step("Step 4/4b: Re-generate HTML with status", HTML_SCRIPT)

    # Copy results to desktop
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_candidates = sorted(SKILL_DIR.glob("职位投递列表_*.html"), reverse=True)
    if html_candidates:
        import shutil
        dest = out_dir / f"职位投递列表_{date_str}.html"
        shutil.copy(html_candidates[0], dest)
        print(f"\n  HTML copied to: {dest}")

    # Also copy matched_jobs
    if matched_json.exists():
        import shutil
        dest_json = out_dir / f"matched_jobs_{date_str}.json"
        shutil.copy(matched_json, dest_json)
        print(f"  JSON copied to: {dest_json}")

    print(f"\n{'=' * 60}")
    print(f"  Pipeline complete. Open the HTML file to start applying.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
