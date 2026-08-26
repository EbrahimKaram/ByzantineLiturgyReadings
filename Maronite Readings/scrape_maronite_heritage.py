"""Scrape maronite-heritage.com's "Gospel Readings" section into structured JSON.

The site (https://www.maronite-heritage.com) organizes readings by liturgical
season/week (e.g. "14th Week Pentecost") and by fixed Synaxarion dates
(e.g. "1Jan"). Every page shares the same sidebar navigation, so we discover
every reachable page from the "Gospel Readings" index page and scrape each
one individually.

Each page is parsed generically:
  - Weekday headers (SUNDAY/MONDAY/.../SATURDAY), optionally preceded by a
    title line (e.g. "Miracle of Cana in Galilee\nSUNDAY"), start a new
    section.
  - Within a section, consecutive text blocks alternate between a scripture
    reference (e.g. "Luke 15:8-10") and its full text.
  - Pages without any weekday headers (e.g. informational pages) are still
    captured via their raw text as a fallback.

Usage:
    python scrape_maronite_heritage.py [--delay 0.5] [--output maronite_heritage_raw.json]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.maronite-heritage.com/LNE.php"
INDEX_PAGE = "Gospel Readings"

# Site-wide nav / index pages that hold no reading content of their own.
EXCLUDED_PAGES = {
    "index", "About us", "Maronites", "Lebanon", "Calendar", "Archive", "Links",
    "Gospel Readings", "Synaxarion",
}

WEEKDAY_TOKENS = {"SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"}

# Best-effort match for a scripture citation at the start of a line, e.g.
# "1 John 4:7-21" or "Isaiah 54: 1+3+5-8+10" or "Titus 2:11-3:7 Transformation of Life".
# Pages are not consistent about whether the citation is alone on its own block
# or embedded as the first line of a larger paragraph, so this is metadata only
# -- the original block text is always preserved untouched in "text".
CITATION_RE = re.compile(
    r"^(?:[1-3]\s*)?[A-Za-z][A-Za-z']*(?:\s+[A-Za-z][A-Za-z']*){0,2}\s+\d{1,3}\s*:\s*[\d+\-\u2013,:\s]+"
)

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ByzantineLiturgyReadings-Scraper/1.0; "
                  "+https://github.com/EbrahimKaram/ByzantineLiturgyReadings)"
}

PAGE_LINK_RE = re.compile(r'href="LNE\.php\?page=([^"&]+)"')


def fetch_page(session, page_name):
    resp = session.get(BASE_URL, params={"page": page_name}, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def discover_page_names(html):
    """Find every LNE.php?page=... link referenced in the sidebar navigation."""
    names = []
    seen = set()
    for match in PAGE_LINK_RE.finditer(html):
        name = match.group(1).replace("%20", " ").strip()
        if not name or name in seen or name in EXCLUDED_PAGES:
            continue
        seen.add(name)
        names.append(name)
    return names


def clean_text(tag):
    """Extract text from a tag, treating <br> as newlines and trimming blank lines."""
    for br in tag.find_all("br"):
        br.replace_with("\n")
    text = tag.get_text().replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def extract_reference(text):
    """Best-effort scripture citation found in the first line of a text block."""
    first_line = text.split("\n", 1)[0]
    match = CITATION_RE.match(first_line)
    return match.group(0).strip() if match else None


def parse_main_content(html, page_name):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("div", id="main")
    if main is None:
        return {"page": page_name, "title": page_name, "sections": [], "raw_text": ""}

    title_tag = main.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else page_name
    if title_tag:
        title_tag.extract()

    raw_text = clean_text(main)

    # Only consider "leaf" div/p blocks (no nested div/p), regardless of how
    # deeply they're nested inside wrapper containers on different page layouts.
    blocks = [el for el in main.find_all(["div", "p"]) if not el.find(["div", "p"])]

    sections = []
    current = None

    for block in blocks:
        text = clean_text(block)
        if not text:
            continue

        lines = text.split("\n")
        last_line = lines[-1].strip().upper()

        if last_line in WEEKDAY_TOKENS:
            label = "\n".join(lines[:-1]).strip() or None
            current = {"heading": last_line, "label": label, "readings": []}
            sections.append(current)
            continue

        if current is None:
            current = {"heading": None, "label": None, "readings": []}
            sections.append(current)

        # Each block is kept verbatim; the reference is best-effort metadata
        # only, since some pages put it in its own block and others embed it
        # as the first line of the full reading paragraph.
        current["readings"].append({"reference": extract_reference(text), "text": text})

    return {"page": page_name, "title": title, "sections": sections, "raw_text": raw_text}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "maronite_heritage_raw.json"),
        help="Path to write the scraped JSON output",
    )
    args = parser.parse_args()

    session = requests.Session()

    print(f"Fetching index page: {INDEX_PAGE}")
    index_html = fetch_page(session, INDEX_PAGE)
    page_names = discover_page_names(index_html)
    print(f"Discovered {len(page_names)} pages to scrape")

    results = []
    for i, page_name in enumerate(page_names, 1):
        print(f"[{i}/{len(page_names)}] Fetching '{page_name}'...")
        try:
            html = fetch_page(session, page_name)
            results.append(parse_main_content(html, page_name))
        except requests.RequestException as exc:
            print(f"  ERROR fetching '{page_name}': {exc}", file=sys.stderr)
            results.append({"page": page_name, "title": page_name, "sections": [], "raw_text": "", "error": str(exc)})
        time.sleep(args.delay)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(results)} pages to {output_path}")


if __name__ == "__main__":
    main()
