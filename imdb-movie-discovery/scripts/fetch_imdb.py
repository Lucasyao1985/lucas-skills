#!/usr/bin/env python3
"""
IMDB GraphQL API helper for the movie-discovery skill.
Reads session cookies from the user's IMDB Cookie.txt.

Usage:
    python scripts/fetch_imdb.py trending --limit 10
    python scripts/fetch_imdb.py title --id tt0111161
    python scripts/fetch_imdb.py similar --id tt0111161 --limit 5
    python scripts/fetch_imdb.py search --query "Little Brother"

Get cookies: place browser-exported cookies at C:/Users/Lucas/Desktop/imdb/Cookie.txt
"""

import argparse
import json
import os
import sys
import uuid

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

IMDB_API = "https://api.graphql.imdb.com/"
COOKIE_DIR = "C:/Users/Lucas/Desktop/imdb"
COOKIE_FILE = os.path.join(COOKIE_DIR, "Cookie.txt")

# Working queries — with voteCount included for popularity sorting
QUERIES = {
    "trending": lambda limit: {
        "query": "query { trendingTitles(limit: %d) { titles { id originalTitleText { text } titleType { id } releaseYear { year } ratingsSummary { aggregateRating voteCount } titleGenres { genres { genre { text } } } primaryImage { url } runtime { seconds } credits(first: 3) { edges { node { name { nameText { text } } } } } } } }" % limit,
        "variables": {}
    },
    "title": lambda tid: {
        "query": "{ titles(ids: [\"%s\"]) { id originalTitleText { text } titleType { id } releaseYear { year } ratingsSummary { aggregateRating voteCount } plot { plotText { plainText } } primaryImage { url width height } runtime { seconds } titleGenres { genres { genre { text } } } credits(first: 5) { edges { node { name { nameText { text } } } } } moreLikeThisTitles(first: 5) { edges { node { id originalTitleText { text } releaseYear { year } ratingsSummary { aggregateRating voteCount } titleGenres { genres { genre { text } } } } } } } }" % tid,
        "variables": {}
    },
    "similar": lambda tid, limit: {
        "query": "{ titles(ids: [\"%s\"]) { moreLikeThisTitles(first: %d) { edges { node { id originalTitleText { text } titleType { id } releaseYear { year } ratingsSummary { aggregateRating voteCount } plot { plotText { plainText } } titleGenres { genres { genre { text } } } primaryImage { url } runtime { seconds } } } } } }" % (tid, limit),
        "variables": {}
    },
    "search": lambda q: {
        "query": "{ mainSearch(first: 10, options: {searchTerm: \"%s\"}) { edges { node { entity { __typename ... on Title { id originalTitleText { text } titleType { id } releaseYear { year } ratingsSummary { aggregateRating voteCount } } } } } } }" % q.replace('"', '\\"'),
        "variables": {}
    },
}

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://www.imdb.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "x-imdb-client-name": "imdb-web-next",
    "x-imdb-client-rid": lambda: uuid.uuid4().hex[:20].upper(),
}


def _get_votes(item):
    """Extract voteCount from a title dict (search result or trending title)."""
    try:
        return (item.get("ratingsSummary") or {}).get("voteCount") or 0
    except Exception:
        return 0


def _dedupe_and_sort_titles(titles):
    """Deduplicate by title ID and sort descending by voteCount (popularity)."""
    seen = set()
    unique = []
    for t in titles:
        tid = t.get("id")
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(t)
    unique.sort(key=_get_votes, reverse=True)
    return unique


def sort_results(data, command):
    """Post-process API results: deduplicate and sort by popularity (voteCount)."""
    if "errors" in data and "data" not in data:
        return data

    d = data.get("data") or {}
    if not d:
        return data

    if command == "trending":
        titles = d.get("trendingTitles", {}).get("titles", [])
        d["trendingTitles"]["titles"] = _dedupe_and_sort_titles(titles)

    elif command == "search":
        edges = d.get("mainSearch", {}).get("edges", [])
        titles = []
        for edge in edges:
            entity = (edge.get("node") or {}).get("entity") or {}
            if entity.get("__typename") == "Title":
                titles.append(entity)
        d["mainSearch"]["edges"] = [
            {"node": {"entity": t}} for t in _dedupe_and_sort_titles(titles)
        ]

    elif command in ("title", "similar"):
        titles = d.get("titles", [])
        for t in titles:
            mlt = (t.get("moreLikeThisTitles") or {}).get("edges", [])
            mlt_titles = [n["node"] for n in mlt]
            (t.get("moreLikeThisTitles") or {})["edges"] = [
                {"node": n} for n in _dedupe_and_sort_titles(mlt_titles)
            ]

    data["data"] = d
    return data


def load_cookies():
    """Load cookies from Cookie.txt (Chrome format: name TAB domain TAB path TAB ...)."""
    cookies = {}
    if not os.path.exists(COOKIE_FILE):
        print(f"WARNING: No cookie file at {COOKIE_FILE}", file=sys.stderr)
        return cookies
    with open(COOKIE_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                cookies[parts[0]] = parts[5]
    return cookies


def fetch(query_name, **kwargs):
    """Execute a named IMDB GraphQL query and post-process results."""
    if query_name not in QUERIES:
        raise ValueError(f"Unknown query: {query_name}. Options: {list(QUERIES)}")

    payload = QUERIES[query_name](**kwargs)
    headers = dict(HEADERS)
    headers["x-imdb-client-rid"] = (
        headers["x-imdb-client-rid"]()
        if callable(headers["x-imdb-client-rid"])
        else headers["x-imdb-client-rid"]
    )

    session = requests.Session()
    session.headers.update(headers)
    cookies = load_cookies()
    if cookies:
        session.cookies.update(cookies)

    response = session.post(IMDB_API, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        errors = data["errors"]
        print(f"WARNING: {len(errors)} API error(s)", file=sys.stderr)
        for e in errors[:3]:
            print(f"  - {e.get('message', e)}", file=sys.stderr)

    # Post-process: sort by popularity (voteCount), deduplicate
    return sort_results(data, query_name)


def print_json(data, indent=2):
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Fetch data from IMDB GraphQL API")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("trending")
    t.add_argument("--limit", type=int, default=10)

    i = sub.add_parser("title")
    i.add_argument("--id", required=True, dest="tid", help="IMDb ttId, e.g. tt0111161")

    s = sub.add_parser("similar")
    s.add_argument("--id", required=True, dest="tid")
    s.add_argument("--limit", type=int, default=5)

    q = sub.add_parser("search")
    q.add_argument("--query", required=True, dest="q")

    args = parser.parse_args()
    kwargs = {k: v for k, v in vars(args).items() if k != "command"}
    data = fetch(args.command, **kwargs)
    print_json(data)


if __name__ == "__main__":
    main()
