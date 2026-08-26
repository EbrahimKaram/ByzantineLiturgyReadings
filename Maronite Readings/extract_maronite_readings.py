"""Extract structured reading references from maronite_heritage_raw.json.

Produces maronite_readings.json — a list of pages, each with a "days" dict
mapping weekday name → {old_testament, epistle, gospel} reference strings.

Key parsing rules:
- Sunday always gets 3 readings: OT + Epistle + Gospel.
- Mon–Sat get 2 readings: Epistle + Gospel.
- Pages where all days are packed under heading=None (no explicit weekday headings
  in the page, e.g. "Epiphany") are decoded as: first 3 refs = Sunday, then pairs
  = Monday through Saturday.
- Pages where only Sunday is under heading=None and Mon–Sat have explicit headings
  (e.g. most weekly pages) are also handled correctly.
- Reference text is normalized: trailing descriptive text after the citation
  (e.g. "Titus 2:11-3:7 Transformation of Life" → "Titus 2:11-3:7") is stripped.

Usage:
    python extract_maronite_readings.py [--input maronite_heritage_raw.json]
                                        [--output maronite_readings.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

WEEKDAYS = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

GOSPEL_BOOKS = frozenset([
    "matthew", "matt", "mt", "mark", "mk", "luke", "lk", "john", "jn",
])
# OT identified by exclusion of NT books; these are common Maronite OT citations.
OT_BOOKS = frozenset([
    "genesis", "gen", "gn", "exodus", "ex", "exod", "leviticus", "lev",
    "numbers", "num", "deuteronomy", "deut", "dt", "joshua", "josh",
    "judges", "judg", "ruth", "samuel", "sam", "kings", "kgs", "chronicles",
    "chr", "ezra", "nehemiah", "neh", "esther", "est", "job", "psalms", "ps",
    "psalm", "proverbs", "prov", "ecclesiastes", "eccl", "song", "songs",
    "isaiah", "isa", "is", "jeremiah", "jer", "lamentations", "lam",
    "baruch", "bar", "ezekiel", "ezek", "ez", "daniel", "dan", "dn",
    "hosea", "hos", "joel", "jl", "amos", "am", "obadiah", "ob",
    "jonah", "micah", "mic", "nahum", "nah", "habakkuk", "hab",
    "zephaniah", "zeph", "haggai", "hag", "zechariah", "zech", "malachi", "mal",
    "sirach", "sir", "wisdom", "wis", "tobit", "tob", "judith", "jdt",
    "maccabees", "macc",
])

# Matches "Book chapter:verses" (standard) or "Book verses" (single-chapter books
# like Philemon, 2 John, 3 John, Obadiah, Jude which omit the colon entirely).
CITATION_RE = re.compile(
    r"^((?:[1-3]\s)?[A-Za-z][A-Za-z'.]*(?:\s+[A-Za-z][A-Za-z'.]*){0,3}"
    r"\s+\d{1,3}(?:\s*:\s*[\d][^\n]*|[\s\-:+,][^\n]*))"
)

# Strip trailing descriptive title text after a verse range.
# Only matches when the trailing text is purely alphabetic (no digits/colons/+),
# so "2 Samuel 7: 8-10" and "1 Cor 15:12-26" are never truncated.
TRAILING_TITLE_RE = re.compile(r"(?<=\d)\s+[A-Z][A-Za-z\s]+$")


def find_first_citation(text):
    """Return the first scripture citation found in the text, or None."""
    for line in text.split("\n")[:5]:
        m = CITATION_RE.match(line.strip())
        if m:
            return normalize_ref(m.group(1).strip())
    return None


def normalize_ref(ref):
    """Strip trailing descriptive text from a citation (e.g. title after verse range)."""
    if not ref:
        return ref
    # Remove trailing title text but keep verse range suffixes like "a", "b"
    ref = TRAILING_TITLE_RE.sub("", ref).strip()
    # Normalize internal whitespace around colons and hyphens
    ref = re.sub(r"\s*:\s*", ":", ref)
    ref = re.sub(r"\s{2,}", " ", ref)
    return ref.strip()


def classify_ref(ref):
    """Return 'gospel', 'old_testament', or 'epistle'."""
    if not ref:
        return "epistle"
    # Numbered books need special handling: "1 John", "2 John", "3 John" are epistles
    # while plain "John" is the gospel.
    first_word = ref.split()[0].lower().rstrip(".")
    second_word = ref.split()[1].lower().rstrip(".") if len(ref.split()) > 1 else ""

    # Numbered prefix means the book name is the second token
    if first_word in ("1", "2", "3"):
        book = second_word
    else:
        book = first_word

    if book in GOSPEL_BOOKS:
        # Disambiguate "1 John", "2 John", "3 John" from Gospel "John"
        if book == "john" and first_word in ("1", "2", "3"):
            return "epistle"
        return "gospel"
    if book in OT_BOOKS:
        return "old_testament"
    return "epistle"


def get_refs_from_section(section):
    """Return an ordered list of normalized citation strings from a section."""
    refs = []
    for block in section["readings"]:
        ref = block.get("reference") or find_first_citation(block.get("text") or "")
        if ref:
            refs.append(normalize_ref(ref))
    return refs


def refs_to_day(refs, is_sunday):
    """Map a flat list of refs to {old_testament?, epistle, gospel}."""
    day = {}
    for ref in refs:
        kind = classify_ref(ref)
        if kind not in day:
            day[kind] = ref
        # If already seen this type and it's a different reading (e.g. 2nd Mass),
        # store as a note but keep the first occurrence as the primary.
    return day


def decode_none_heading(refs, has_explicit_weekday_sections):
    """
    Decode a heading=None block into per-day readings.

    Two cases:
    - If explicit Mon–Sat sections follow: the None block is just Sunday.
    - If no explicit weekday sections exist: all days are packed here.
      Sunday = first occurrence of each type (OT, Epistle, Gospel) in order,
      skipping duplicates (e.g. "OR" alternatives for OT).  Mon–Sat = pairs.
    """
    days = {}
    if has_explicit_weekday_sections:
        days["SUNDAY"] = refs_to_day(refs, is_sunday=True)
    else:
        if not refs:
            return days
        # Collect Sunday: first occurrence of each reading type, in sequence.
        # Duplicate types (OR alternatives) are skipped so they don't displace
        # the Epistle/Gospel slots.
        sun = {}
        sun_end = 0
        for i, ref in enumerate(refs):
            kind = classify_ref(ref)
            if kind not in sun:
                sun[kind] = ref
                sun_end = i + 1
            if "gospel" in sun:
                break
        days["SUNDAY"] = sun
        rest = refs[sun_end:]
        weekday_names = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
        for i, day_name in enumerate(weekday_names):
            pair = rest[i * 2 : i * 2 + 2]
            if not pair:
                break
            days[day_name] = refs_to_day(pair, is_sunday=False)
    return days


def parse_page(page):
    sections = page.get("sections", [])
    has_explicit_weekday_sections = any(s["heading"] in WEEKDAYS for s in sections)

    days = {}
    for section in sections:
        heading = section["heading"]
        refs = get_refs_from_section(section)

        if heading is None:
            decoded = decode_none_heading(refs, has_explicit_weekday_sections)
            days.update(decoded)
        elif heading in WEEKDAYS:
            days[heading] = refs_to_day(refs, is_sunday=(heading == "SUNDAY"))

    return days


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input",
        default=str(Path(__file__).parent / "maronite_heritage_raw.json"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "maronite_readings.json"),
    )
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results = []
    warnings = 0

    for page_data in raw:
        page_name = page_data["page"]
        days = parse_page(page_data)

        # Skip warning on informational pages (Synaxarion biographies, etc.)
        # that contain no structured liturgical readings at all.
        has_any_gospel = any(d.get("gospel") for d in days.values())

        if has_any_gospel:
            for day_name, readings in days.items():
                if not readings.get("gospel"):
                    print(f"  WARN: {page_name} / {day_name} — no gospel found", file=sys.stderr)
                    warnings += 1
                if day_name == "SUNDAY" and not readings.get("old_testament"):
                    print(f"  WARN: {page_name} / {day_name} — no OT reading found", file=sys.stderr)
                    warnings += 1

        results.append({"page": page_name, "days": days})

    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(results)} pages to {args.output}  ({warnings} warnings)")


if __name__ == "__main__":
    main()
