#!/usr/bin/env python3
"""
Fetch the first 5 articles listed on https://ekantipur.com/entertainment.

Uses requests + BeautifulSoup (server-rendered HTML; no browser required).

Install: pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ekantipur.com"
LIST_PATH = "/entertainment"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ne,en-US;q=0.9,en;q=0.8",
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding == "ISO-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def excerpt_from_description(desc: BeautifulSoup) -> str | None:
    for p in desc.find_all("p"):
        if p.find_parent(class_="author-name"):
            continue
        text = p.get_text(strip=True)
        if text:
            return text
    return None


def image_url_from_block(block: BeautifulSoup) -> str | None:
    img = block.select_one("div.category-image img")
    if not img:
        return None
    return img.get("data-src") or img.get("src")


def read_time_from_description(desc: BeautifulSoup) -> str | None:
    span = desc.select_one("div.time-wrapper span")
    return span.get_text(strip=True) if span else None


def parse_listing(html: str, limit: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()

    for block in soup.select("div.category-inner-wrapper"):
        desc = block.select_one("div.category-description")
        if not desc:
            continue
        a = desc.select_one("h2 a[href]")
        if not a:
            continue
        href = (a.get("href") or "").strip()
        if "/entertainment/" not in href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen:
            continue
        seen.add(url)

        author_el = desc.select_one("div.author-name")
        author = author_el.get_text(strip=True) if author_el else None

        item = {
            "title": a.get_text(strip=True),
            "url": url,
            "author": author,
            "excerpt": excerpt_from_description(desc),
            "read_time": read_time_from_description(desc),
            "image_url": image_url_from_block(block),
        }
        out.append(item)
        if len(out) >= limit:
            break

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Ekantipur entertainment listing.")
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=5,
        help="Number of articles to collect (default: 5)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write JSON to this file (UTF-8). Default: print to stdout.",
    )
    args = parser.parse_args()

    list_url = urljoin(BASE_URL, LIST_PATH)
    try:
        html = fetch_html(list_url)
        articles = parse_listing(html, limit=args.count)
    except requests.RequestException as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        return 1

    if not articles:
        print("No articles found (selectors may need updating).", file=sys.stderr)
        return 2

    payload = {"source": list_url, "articles": articles}
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {len(articles)} articles to {args.output}")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
