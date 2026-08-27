"""Fetch Maronite daily readings from the evangelizo.ws API for a range of years.

Produces maronite_calendar.json — a date-keyed dict (YYYY-MM-DD) where each
entry contains the liturgical title and the full reading texts returned by the
API. Designed to be a static asset shipped with the Vue.js frontend.

Usage:
    python build_maronite_calendar.py [--years 2025 2026 2027]
                                      [--delay 1.5] [--output maronite_calendar.json]
"""
import argparse
import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API_BASE = "https://publication.evangelizo.ws/MAE/days"
REQUEST_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.5",
    "origin": "https://dailygospel.org",
    "referer": "https://dailygospel.org/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
}

# Strip [[BookCode chapter,verse]] verse-reference markers embedded in text
VERSE_MARKER_RE = re.compile(r"\[\[[\w_,. ]+\]\]")
# Remove trailing period from reference_displayed
REF_TRAIL_RE = re.compile(r"\.+$")
# "#BookCode chapter,verse" non-consecutive verse separators
HASH_SEP_RE = re.compile(r"#\S+\s+\d+,\S+")


def clean_text(raw: str) -> str:
    text = VERSE_MARKER_RE.sub("", raw or "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def normalize_reference(reading_code: str, book_code: str, ref_displayed: str) -> str:
    """Build a readable reference like '1 Jn 4:7-21' from API fields."""
    # Use reading_code as base; remove underscores in numbered book prefix
    code = re.sub(r"(\d)_", r"\1 ", reading_code)
    # Replace comma verse separator with colon
    code = code.replace(",", ":")
    # Replace non-consecutive verse markers (#Book ch:v) with ellipsis
    code = HASH_SEP_RE.sub("…", code)
    return REF_TRAIL_RE.sub("", code).strip()


class RateLimited(Exception):
    """The remote API rejected the request with HTTP 429."""


class NotFound(Exception):
    """The remote API has no data for this date (HTTP 404)."""


def fetch_day(date_str: str, session: requests.Session, retries: int = 3) -> dict:
    url = f"{API_BASE}/{date_str}?from=gospelComponent"
    last_status = None
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=REQUEST_HEADERS, timeout=20)
            last_status = resp.status_code
            if resp.status_code == 404:
                raise NotFound(f"{date_str}: 404 Not Found")
            if resp.status_code == 429:
                wait = 30 * (2 ** attempt)
                print(
                    f"  429 {date_str}: Too Many Requests "
                    f"(attempt {attempt + 1}/{retries}, retry in {wait}s)",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json().get("data", {})
            readings = []
            for r in data.get("readings", []):
                readings.append({
                    "type": r.get("type", ""),
                    "reference": normalize_reference(
                        r.get("reading_code", ""),
                        r.get("book", {}).get("code", ""),
                        r.get("reference_displayed", ""),
                    ),
                    "book": r.get("book", {}).get("full_title", ""),
                    "text": clean_text(r.get("text", "")),
                })
            return {
                "liturgic_title": data.get("liturgic_title", ""),
                "readings": readings,
            }
        except (NotFound, RateLimited):
            raise
        except Exception as exc:
            if attempt == retries - 1:
                raise
            print(f"  FAIL {date_str}: {exc} (retrying)", file=sys.stderr, flush=True)
            time.sleep(1)
    if last_status == 429:
        raise RateLimited(f"{date_str}: 429 Too Many Requests after {retries} attempts")
    raise RuntimeError(f"{date_str}: request failed after {retries} attempts")


def date_range(year: int):
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="+", type=int, default=[2025, 2026, 2027])
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to wait between successful API calls",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "maronite_calendar.json"),
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    existing = {}
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(existing)} existing entries from {output_path}")

    all_dates = [d for year in sorted(set(args.years)) for d in date_range(year)]
    to_fetch = [d for d in all_dates if d not in existing]
    print(
        f"Fetching {len(to_fetch)} dates across {args.years} "
        f"with {args.delay}s between calls…"
    )

    results = dict(existing)
    done = 0
    skipped = []

    def save(label: str) -> None:
        output_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        print(f"  {label}: {len(results)} entries saved to {output_path}", flush=True)

    with requests.Session() as session:
        try:
            for date_str in to_fetch:
                try:
                    entry = fetch_day(date_str, session)
                except NotFound as exc:
                    skipped.append(date_str)
                    print(f"  SKIP {exc}", file=sys.stderr, flush=True)
                    done += 1
                    if args.delay > 0 and done < len(to_fetch):
                        time.sleep(args.delay)
                    continue
                results[date_str] = entry
                done += 1
                if done % 50 == 0:
                    print(f"  {done}/{len(to_fetch)} processed, saving…", flush=True)
                    save("checkpoint")
                if args.delay > 0 and done < len(to_fetch):
                    time.sleep(args.delay)
        except RateLimited as exc:
            print(f"\nRate limited. Stopping so remaining dates can be retried later.\n  {exc}", file=sys.stderr, flush=True)
            save("rate-limited")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nInterrupted. Saving progress…", file=sys.stderr, flush=True)
            save("interrupted")
            sys.exit(130)
        except Exception as exc:
            print(f"\nUnexpected error. Saving progress…\n  {exc}", file=sys.stderr, flush=True)
            save("error")
            raise

    save("done")
    if skipped:
        print(f"Skipped {len(skipped)} missing date(s): {', '.join(skipped)}")
    print(f"Done. {len(results)} total entries saved to {output_path}")


if __name__ == "__main__":
    main()
