import pdfplumber
import re
import json
import csv
import calendar
from collections import Counter
from pathlib import Path
from datetime import date

# Regex patterns matching the logic in ReadingCard.vue
TAGS_RE = re.compile(r'<[^>]*>')
WHITESPACE_RE = re.compile(r'\s+')
TONE_RE = re.compile(r'Tone\s+(\d+)', re.IGNORECASE)
MATINS_RES_RE = re.compile(r'Res\.?\s*Gospel\s+(\d+)', re.IGNORECASE)
MATINS_TEXT_RE = re.compile(r'Matins\s+Gospel:?\s*(.+?)(?=\s*(?:Divine Liturgy|Epistle|Gospel|Following)|$)', re.IGNORECASE)
IMPLICIT_LITURGY_RE = re.compile(r'Divine Liturgy:?\s*([^;]+);\s*([^;]+?)(?=\s*(?:Following|\.\s*[A-Z]|$))', re.IGNORECASE)
EPISTLE_RE = re.compile(r'(?:^|[\s,;.])(?:Epistle\b|Ep\b\.?)\s*:?\s*(.+?)(?=\s*(?:Gospel|G\s*:|Following)|$)', re.IGNORECASE)
APOSTLE_EPISTLE_RE = re.compile(r'(?:^|[\s,;.])(?:Apostle\b|Apost\.)\s+((?:[1-3]\s*)?(?:Acts|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Phlm|Philem|Heb|Jas|James|Pet|Jude|Rev)\.?\s*[^;]*?\d\s*:\s*\d[^;]*?)(?=\s*(?:;\s*)?(?:Gospel|G\s*:|Following)|$)', re.IGNORECASE)
EPISTLE_BEFORE_GOSPEL_RE = re.compile(r'(?:^|[\s,;.])((?:[1-3]\s*)?(?:Acts|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Phlm|Philem|Heb|Jas|James|Pet|Jude|Rev)\.?\s*[^;]*?\d\s*:\s*\d[^;]*?)(?=\s*;\s*(?:Gospel|G\s*:))', re.IGNORECASE)
GOSPEL_RE = re.compile(r'(?:^|[\s,;.])(?:Gospel|G\s*:)\s*(.+?)(?=\s*(?:Following|(?:Divine\s+)?Liturgy|Great\s+blessing\s+of\s+water|Holy\s+Day\s+of\s+Obligation|\.\s+[A-Z])|$)', re.IGNORECASE)
FOLLOWING_NOTES_START_RE = re.compile(
    r'\b(?:the\s+readings?\s+for\s+the\s+following\s+week|following\s+week\s+readings?|following\s+week)\b',
    re.IGNORECASE
)
DIVINE_LITURGY_HEADER_RE = re.compile(r'Divine Liturgy:?', re.IGNORECASE)
FASTING_RE = re.compile(
    r'(Strict Fast and abstinence|Strict Abstinence|Common Abstinence|Strict Fast|Dispensation\s*\([^)]+\)|Dispensation|Abstinence(?:\s+from\s+[^\n.;]+(?:\s+this\s+week)?)?)',
    re.IGNORECASE
)
CANADA_HOLIDAY_RE = re.compile(r'\bCANADA\s*:\s*(.+?)(?=(?:\s+USA\s*:)|$)', re.IGNORECASE)
USA_HOLIDAY_RE = re.compile(r'\bUSA\s*:\s*(.+?)(?=(?:\s+CANADA\s*:)|$)', re.IGNORECASE)
TRAILING_REFERENCE_NOISE_RE = re.compile(
    r'(?:\s*[;,.]\s*|\s+)'
    r'(?:also\b|may\s+also\s+read\b|forefeast\b|resurrection\s+service\b|matins\s+and\b)'
    r'.*$',
    re.IGNORECASE
)
TRAILING_OVERLAY_DAY_RE = re.compile(r'\s*/\s*\d{1,2}\b.*$')

MOJIBAKE_REPLACEMENTS = {
    "â€“": "–",
    "â€”": "—",
    "â€˜": "‘",
    "â€™": "’",
    "â€œ": "“",
    "â€": "”",
    "Â": ""
}

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
}

WEEKDAY_TOKENS = {
    "sun", "sunday", "mon", "monday", "tue", "tues", "tuesday",
    "wed", "wednesday", "thu", "thur", "thurs", "thursday",
    "fri", "friday", "sat", "saturday"
}

def clean_string(s):
    if not s:
        return None
    # Remove leading/trailing punctuation and whitespace
    return re.sub(r'^[;:,.\-\s]+|[;:,.\-\s]+$', '', s.strip())

def normalize_mojibake(text):
    if not text:
        return text

    normalized = str(text)
    for broken, fixed in MOJIBAKE_REPLACEMENTS.items():
        normalized = normalized.replace(broken, fixed)
    return normalized

def normalize_scripture_reference(value):
    text = clean_string(value)
    if not text:
        return None

    text = re.sub(r'\b(?:Great\s+blessing\s+of\s+water|Holy\s+Day\s+of\s+Obligation)\b.*$', '', text, flags=re.IGNORECASE)
    text = TRAILING_REFERENCE_NOISE_RE.sub('', text)
    text = TRAILING_OVERLAY_DAY_RE.sub('', text)
    text = text.replace(chr(0x2013), '-')
    text = text.replace(chr(0x2014), '-')

    chars = list(text)
    for idx in range(1, len(chars) - 1):
        if ord(chars[idx]) in (0x00E2, 0x00C3) and chars[idx - 1].isdigit() and chars[idx + 1].isdigit():
            chars[idx] = '-'
    text = ''.join(chars)

    text = re.sub(r'(?<=\d)\s*-\s*(?=\d)', '-', text)
    text = WHITESPACE_RE.sub(' ', text).strip()
    return clean_string(text)

def extract_country_holidays(text):
    canada_holiday = None
    usa_holiday = None
    work_text = text

    canada_match = CANADA_HOLIDAY_RE.search(work_text)
    if canada_match:
        canada_holiday = clean_string(canada_match.group(1))
        work_text = work_text.replace(canada_match.group(0), ' ')

    usa_match = USA_HOLIDAY_RE.search(work_text)
    if usa_match:
        usa_holiday = clean_string(usa_match.group(1))
        work_text = work_text.replace(usa_match.group(0), ' ')

    work_text = WHITESPACE_RE.sub(' ', work_text).strip()
    return work_text, canada_holiday, usa_holiday

def parse_reading_text(text):
    if not text:
        return None

    # Start with a clean working copy
    work_text = TAGS_RE.sub(' ', text)
    work_text = WHITESPACE_RE.sub(' ', work_text).strip()
    work_text = normalize_mojibake(work_text)

    # Extract country-specific holidays early so they don't remain in title/notes
    work_text, canada_holiday, usa_holiday = extract_country_holidays(work_text)

    # 0. Extract Fasting/Abstinence (Look for it early to remove it from Title/notes)
    fasting = None
    fasting_match = FASTING_RE.search(work_text)
    if fasting_match:
        fasting = WHITESPACE_RE.sub(' ', fasting_match.group(1)).strip()
        if re.match(r'^Abstinence\b', fasting, re.IGNORECASE) and ' from ' not in fasting.lower():
            fasting = 'Abstinence'
        work_text = work_text.replace(fasting_match.group(0), '')

    # 1. Extract Tone
    tone = None
    tone_match = TONE_RE.search(work_text)
    if tone_match:
        tone = tone_match.group(1)
        # Remove matched tone to avoid confusion and clean up for notes
        work_text = work_text.replace(tone_match.group(0), '')

    # 2. Extract Matins
    matins_gospel = None
    matins_res_match = MATINS_RES_RE.search(work_text)
    
    if matins_res_match:
        matins_gospel = matins_res_match.group(1)
        # Remove matched Res. Gospel to avoid it being picked up by generic Gospel regex
        work_text = work_text.replace(matins_res_match.group(0), '')
    else:
        matins_text_match = MATINS_TEXT_RE.search(work_text)
        if matins_text_match:
            matins_gospel = clean_string(matins_text_match.group(1))
            work_text = work_text.replace(matins_text_match.group(0), '')

    # 3. Prepare for Liturgy Parsing
    epistle = None
    gospel = None

    implicit_match = IMPLICIT_LITURGY_RE.search(work_text)
    
    if implicit_match:
        epistle = normalize_scripture_reference(implicit_match.group(1))
        gospel = normalize_scripture_reference(implicit_match.group(2))
        work_text = work_text.replace(implicit_match.group(0), '')
    else:
        # Clear Liturgy Header if present
        work_text = DIVINE_LITURGY_HEADER_RE.sub('', work_text)

        # 4. Extract Epistle
        epistle_match = EPISTLE_RE.search(work_text)
        if epistle_match:
            epistle = normalize_scripture_reference(epistle_match.group(1))
            work_text = work_text.replace(epistle_match.group(0), '')
        else:
            apostle_match = APOSTLE_EPISTLE_RE.search(work_text)
            if apostle_match:
                epistle = normalize_scripture_reference(apostle_match.group(1))
                work_text = work_text.replace(apostle_match.group(0), '')
            else:
                epistle_fallback_match = EPISTLE_BEFORE_GOSPEL_RE.search(work_text)
                if epistle_fallback_match:
                    epistle = normalize_scripture_reference(epistle_fallback_match.group(1))
                    work_text = work_text.replace(epistle_fallback_match.group(0), '')

        # 5. Extract Gospel
        gospel_match = GOSPEL_RE.search(work_text)
        if gospel_match:
            gospel = normalize_scripture_reference(gospel_match.group(1))
            work_text = work_text.replace(gospel_match.group(0), '')

    # 6. Extract Notes (Whatever is left is roughly the title/notes)
    # The work_text has been stripped of identified parts sequentially
    notes = work_text
    
    # Cleaning based on Vue logic
    notes = re.sub(r'^[\s,;.]+|[\s,;.]+$', '', notes)
    notes = re.sub(r'\s+([,;.])', r'\1', notes)
    notes = re.sub(r'[,;]+\s*\.', '.', notes)
    notes = re.sub(r'\.\s*[,;]+', '.', notes)
    notes = re.sub(r',,+', ',', notes)
    notes = re.sub(r'\.\.+', '.', notes)
    
    notes = notes.strip()
    
    return {
        "tone": tone,
        "matinsGospel": matins_gospel,
        "epistle": epistle,
        "gospel": gospel,
        "fasting": fasting,
        "notes": notes if notes else None,
        "canadaHoliday": canada_holiday,
        "usaHoliday": usa_holiday
    }

def extract_day_number_at_start(text):
    if not text:
        return None

    cleaned = str(text).strip()
    if not cleaned:
        return None

    # Fast fail: If it doesn't start with a digit or 'Common'/'Strict'/'Dispensation', skip heavy regex
    first_char = cleaned[0].upper()
    if not (first_char.isdigit() or first_char in ('C', 'S', 'D', 'A')):
        return None

    # Avoid misclassifying ordinal titles (e.g., "1st SUNDAY ...") as day numbers.
    if re.match(r'^\d{1,2}(?:st|nd|rd|th)\b', cleaned, re.IGNORECASE):
        return None

    # Handle rows where fasting text precedes the day number at the start of the cell.
    fasting_prefixed = re.match(
        r'^(?:Common\s+Abstinence|Strict\s+Abstinence|Strict\s+Fast(?:\s+and\s+abstinence)?|Dispensation(?:\s*\([^)]+\))?)\s+(\d{1,2})(?=\s|$|[;:,\-–()./])',
        cleaned,
        re.IGNORECASE
    )
    if fasting_prefixed:
        day_num = int(fasting_prefixed.group(1))
        if 1 <= day_num <= 31:
            return day_num

    day_match = re.match(r'^(\d{1,2})(?=\s|$|[;:,\-–()./])', cleaned)
    if not day_match:
        return None

    day_num = int(day_match.group(1))
    if re.match(r'^\d{1,2}\s*[\-–]\s*\d+', cleaned):
        return None
    if re.match(r'^\d{1,2}\s*[;:]', cleaned):
        return None
    if re.match(r'^\d{1,2}\s*,\s*(?:Gospel|Ep(?:istle)?\b|Res\.?\s*Gospel\b)', cleaned, re.IGNORECASE):
        return None
    if re.match(r'^\d\s+(?:Tim|Cor|Pet|John|Kgs|Sam|Chr|Thess|Macc)[a-z]*\b', cleaned, re.IGNORECASE):
        return None

    if 1 <= day_num <= 31:
        return day_num

    return None

def replace_day_number_at_start(text, old_day, new_day):
    if not text:
        return text
    cleaned = str(text).strip()
    
    fasting_prefixed = re.match(
        r'^((?:Common\s+Abstinence|Strict\s+Abstinence|Strict\s+Fast(?:\s+and\s+abstinence)?|Dispensation(?:\s*\([^)]+\))?)\s+)' + str(old_day) + r'(?=\s|$|[;:,\-–()./])',
        cleaned,
        re.IGNORECASE
    )
    if fasting_prefixed:
        return text[:fasting_prefixed.end(1)] + str(new_day) + text[fasting_prefixed.end():]
    
    day_match = re.match(r'^' + str(old_day) + r'(?=\s|$|[;:,\-–()./])', cleaned)
    if day_match:
        return str(new_day) + text[day_match.end():]
    return text

def is_weekday_header_row(row):
    if not row:
        return False

    weekday_hits = 0
    for cell in row[:7]:
        if not cell:
            continue
        
        # Fast path check
        text = cell.strip().lower()
        if not text:
            continue
            
        # Simple extraction of first word characters
        first_part = text.split()[0]
        cleaned = "".join(c for c in first_part if c.isalpha())
        
        if cleaned in WEEKDAY_TOKENS:
            weekday_hits += 1

    return weekday_hits >= 4

def get_table_cell_bbox(table, row_idx, col_idx):
    try:
        row_obj = table.rows[row_idx]
        cell = row_obj.cells[col_idx]
        if isinstance(cell, (tuple, list)) and len(cell) >= 4:
            x0, top, x1, bottom = cell[:4]
            if all(v is not None for v in (x0, top, x1, bottom)):
                return (float(x0), float(top), float(x1), float(bottom))
    except Exception:
        return None
    return None

def get_logical_cell_bbox(table, row_idx, logical_col_idx, group_width):
    if group_width <= 1:
        return get_table_cell_bbox(table, row_idx, logical_col_idx)

    x0 = None
    top = None
    x1 = None
    bottom = None

    start = logical_col_idx * group_width
    end = start + group_width
    for physical_col in range(start, end):
        bbox = get_table_cell_bbox(table, row_idx, physical_col)
        if not bbox:
            continue
        bx0, btop, bx1, bbottom = bbox
        x0 = bx0 if x0 is None else min(x0, bx0)
        top = btop if top is None else min(top, btop)
        x1 = bx1 if x1 is None else max(x1, bx1)
        bottom = bbottom if bottom is None else max(bottom, bbottom)

    if None in (x0, top, x1, bottom):
        return None
    return (x0, top, x1, bottom)

def merge_unique_parts(parts):
    merged = []
    seen = set()
    
    for part in parts:
        text = (part or '').strip()
        if not text:
            continue

        # Check if we've seen this exact text before
        if text in seen:
            continue
            
        # Check if text is a substring of something we've already collected
        # (This remains O(N), but 'merged' is usually very small)
        if any(text in existing for existing in merged):
            continue
            
        merged.append(text)
        seen.add(text)

    return "\n".join(merged) if merged else None

def collapse_row_to_7_columns(row):
    row = row or []
    col_count = len(row)

    if col_count == 7:
        return row[:7], 1

    if col_count > 7 and col_count % 7 == 0:
        group_width = col_count // 7
        collapsed = []
        for logical_col in range(7):
            start = logical_col * group_width
            end = start + group_width
            parts = row[start:end]
            collapsed.append(merge_unique_parts(parts))
        return collapsed, group_width

    if col_count < 7:
        return row + [None] * (7 - col_count), 1

    return row[:7], 1

def extract_day_from_cell_style(page, bbox):
    if not bbox:
        return None

    x0, top, x1, bottom = bbox
    width = x1 - x0
    height = bottom - top
    if width <= 0 or height <= 0:
        return None

    top_band = top + (height * 0.40)

    digit_chars = []
    for ch in page.chars:
        try:
            cx = (float(ch["x0"]) + float(ch["x1"])) / 2.0
            cy = (float(ch["top"]) + float(ch["bottom"])) / 2.0
            if x0 <= cx <= x1 and top <= cy <= bottom and str(ch.get("text", "")).isdigit():
                digit_chars.append(ch)
        except Exception:
            continue

    if not digit_chars:
        return None

    top_digits = [c for c in digit_chars if float(c.get("top", top)) <= top_band]
    candidates = top_digits if top_digits else digit_chars

    max_size = max(float(c.get("size", 0)) for c in candidates)
    prominent = [c for c in candidates if float(c.get("size", 0)) >= (max_size - 0.25)]
    if not prominent:
        return None

    prominent = sorted(prominent, key=lambda c: float(c.get("x0", 0)))
    digit_text = "".join(str(c.get("text", "")) for c in prominent)

    match = re.search(r'(\d{1,2})', digit_text)
    if not match:
        return None

    day_num = int(match.group(1))
    return day_num if 1 <= day_num <= 31 else None

def clean_title(notes, day):
    if not notes:
        return ""
    cleaned = notes.strip()
    # Remove the day number if it appears at the start of the notes
    if day:
        # Regex to match the day number at the start, possibly followed by punctuation
        pattern = fr'^{day}[\s,.-]*'
        cleaned = re.sub(pattern, '', cleaned)

    cleaned = re.sub(r'\bHoly\s+Day\s+of\s+Obligation\b\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    cleaned = re.sub(r'\s+([,.;:])', r'\1', cleaned)
    cleaned = re.sub(r'([,.;:]){2,}', r'\1', cleaned)
    cleaned = re.sub(r'^[\s,.;:]+|[\s,.;:]+$', '', cleaned)
    return cleaned.strip()

def split_following_notes(notes):
    if not notes:
        return (None, None)

    normalized_notes = WHITESPACE_RE.sub(' ', notes).strip()

    # Handle inline patterns like:
    # "THOMAS SUNDAY ... Gospel ... Following week readings ..."
    # and "... The readings for the following week ..."
    inline_following_match = FOLLOWING_NOTES_START_RE.search(normalized_notes)
    if inline_following_match:
        before = normalized_notes[:inline_following_match.start()].strip()
        after = normalized_notes[inline_following_match.start():].strip()

        before = re.sub(r'^[\s,;:.\-]+|[\s,;:.\-]+$', '', before)
        after = re.sub(r'^[\s,;:.\-]+|[\s,;:.\-]+$', '', after)

        following_text = after or None
        regular_text = before or None
        return (following_text, regular_text)

    sentences = [part.strip() for part in re.split(r'(?<=[.!?])\s+', notes) if part.strip()]
    following_parts = []
    regular_parts = []

    for sentence in sentences:
        if FOLLOWING_NOTES_START_RE.search(sentence):
            following_parts.append(sentence)
        else:
            regular_parts.append(sentence)

    following_text = ' '.join(following_parts).strip() or None
    regular_text = ' '.join(regular_parts).strip() or None
    return (following_text, regular_text)

def raw_text_quality_score(text):
    if not text:
        return 0
    normalized = WHITESPACE_RE.sub(' ', str(text)).strip()
    alpha_count = sum(1 for ch in normalized if ch.isalpha())
    digit_only_penalty = -100 if re.fullmatch(r'\d{1,2}', normalized) else 0
    return (alpha_count * 10) + len(normalized) + digit_only_penalty

def extract_overlay_day_numbers(text, base_day=None):
    if not text:
        return []

    text_str = str(text)
    days = []

    # 1. Standard slash-separated overlay (e.g., "23 / 30")
    one_line = WHITESPACE_RE.sub(' ', text_str).strip()
    match = re.match(r'^(\d{1,2})(?:\s*/\s*(\d{1,2}))+', one_line)
    if match:
        for value in re.findall(r'\d{1,2}', match.group(0)):
            day_num = int(value)
            if 1 <= day_num <= 31 and day_num not in days:
                days.append(day_num)

    # 2. Embedded slash overlay (e.g., "... / 31")
    for value in re.findall(r'(?:(?<=\s)|(?<=^))/\s*(\d{1,2})(?=\b)', one_line):
        day_num = int(value)
        if 1 <= day_num <= 31 and day_num not in days:
            days.append(day_num)

    # 3. Stacked/Vertical overlay (e.g. "23 ... \n30 ...")
    # Only look for this if we have a base_day (the primary day of the cell)
    if base_day:
        next_week_day = base_day + 7
        # We only expect this towards the end of the month (e.g. > 20)
        if base_day > 20 and next_week_day <= 31:
            # Check if this specific next_week_day exists as a standalone token in the text
            # We look for it preceded by newline or start of string, because in stacked cells 
            # the day number is usually on its own line or start of line.
            # We must be careful not to match scripture chapter/verse.
            
            # Regex: 
            # (?:\A|[\n\r])      -> Start of string or newline
            # \s*                -> optional whitespace
            # (next_week_day)    -> our target number
            # (?=\s|$)           -> followed by whitespace or end of string
            # 
            # We also want to avoid matches like "Psalm 30" or "Matt 30:1".
            # The capture group ensures we get the number.
            
            pattern = r'(?:^|[\n\r])\s*(' + str(next_week_day) + r')(?=\s|$)'
            found = re.search(pattern, text_str)
            if found:
                found_day = int(found.group(1))
                if found_day not in days:
                    days.append(found_day)

    return days

def dedupe_entries_by_date(entries):
    deduped_by_date = {}
    for entry in entries:
        key = (entry.get("Year"), entry.get("Date"))
        current = deduped_by_date.get(key)
        if current is None:
            deduped_by_date[key] = entry
            continue

        current_score = raw_text_quality_score(current.get("Raw Text"))
        incoming_score = raw_text_quality_score(entry.get("Raw Text"))
        if incoming_score > current_score:
            deduped_by_date[key] = entry

    return list(deduped_by_date.values())

def is_holy_day_of_obligation(entry):
    try:
        mm = int(entry["Date"][:2])
        dd = int(entry["Day"])
        yyyy = int(entry["Year"])
        dt = date(yyyy, mm, dd)
        if dt.weekday() == 6:  # Sunday
            return True
    except Exception:
        pass

    return bool(re.search(r'Holy Day of Obligation', entry["Raw Text"], re.IGNORECASE))

def enrich_entry(entry):
    parsed = parse_reading_text(entry["Raw Text"])
    following_notes, main_notes = split_following_notes(parsed['notes'])
    title = clean_title(main_notes, entry['Day'])

    entry.update({
        "Title": title,
        "Tone": parsed['tone'],
        "Matins Gospel": parsed['matinsGospel'],
        "Epistle": parsed['epistle'],
        "Gospel": parsed['gospel'],
        "Fasting": parsed['fasting'],
        "Notes": following_notes,
        "Canada Holiday": parsed['canadaHoliday'],
        "USA Holiday": parsed['usaHoliday'],
        "Holy Day of Obligation": is_holy_day_of_obligation(entry)
    })
    return entry

def csv_sort_key(row):
    try:
        year = int(row.get("Year"))
        month = int(str(row.get("Date", ""))[:2])
        day = int(row.get("Day"))
        return (year, month, day)
    except Exception:
        return (9999, 12, 31)

def write_output_files(calendars_dir, sorted_data):
    json_output = calendars_dir / "extracted_readings.json"
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, indent=2)

    csv_output = calendars_dir / "readings.csv"
    csv_columns = ["Date", "Title", "Tone", "Matins Gospel", "Epistle", "Gospel", "Fasting", "Notes", "Canada Holiday", "USA Holiday", "Holy Day of Obligation", "Raw Text"]

    with open(csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for row in sorted_data:
            writer.writerow(row)

    print(f"Extraction complete. Saved to {csv_output}")

def process_table_month(table, page, year, month_num, month_name_raw):
    """
    Extracts readings from a single table if it matches the month structure.
    Returns a list of result dictionaries.
    """
    results = []
    extracted_rows = table.extract() or []
    if not extracted_rows:
        return []

    normalized_rows = []
    group_width = 1
    for row_idx, row in enumerate(extracted_rows):
        collapsed_row, row_group_width = collapse_row_to_7_columns(row)
        if row_group_width > group_width:
            group_width = row_group_width
        normalized_rows.append((row_idx, collapsed_row))

    # Calculate validation metrics for this month
    cal_first_weekday, cal_days_in_m = calendar.monthrange(int(year), int(month_num))
    # (Monday(0) + 1) % 7 = Column 1. (Sunday(6) + 1) % 7 = Column 0.
    expected_start_col = (cal_first_weekday + 1) % 7

    week_blocks = []
    current_block = None

    for row_idx, row in normalized_rows:
        if is_weekday_header_row(row):
            continue

        cells = row[:7]
        days_found = [] 
        for c_i, c_val in enumerate(cells):
            d_val = extract_day_number_at_start(c_val)
            if d_val:
                days_found.append((c_i, d_val))

        is_valid_week = False
        if len(days_found) >= 2:
            is_valid_week = True
        elif len(days_found) == 1:
            col, val = days_found[0]
            # Case A: It's the 1st of the month
            if val == 1 and col == expected_start_col:
                is_valid_week = True
            # Case B: It's the end of the month
            elif val >= 28 and val <= cal_days_in_m:
                is_valid_week = True

        if is_valid_week:
            if current_block:
                week_blocks.append(current_block)
            current_block = {
                "start_row_idx": row_idx,
                "rows": [row]
            }
        elif current_block:
            current_block["rows"].append(row)

    if current_block:
        week_blocks.append(current_block)

    # Smart Anchoring: Find the block that actually contains the start of the month
    start_block_index = 0
    found_start = False
    
    for idx, block in enumerate(week_blocks):
        if found_start:
            break
        row = block["rows"][0]
        cells = row[:7]
        for col_idx, cell_text in enumerate(cells):
            day_val = extract_day_number_at_start(cell_text)
            if not day_val:
                continue
            
            expected_val = col_idx - expected_start_col + 1
            if 1 <= day_val <= 7 and day_val == expected_val:
                start_block_index = idx
                found_start = True
                break
    
    week_blocks = week_blocks[start_block_index:]

    for block_idx, block in enumerate(week_blocks):
        block_rows = block["rows"]
        start_row_idx = block["start_row_idx"]

        combined_cells = [None] * 7
        day_numbers = [None] * 7
        explicit_day_numbers = [None] * 7

        for col_idx in range(7):
            parts = [row[col_idx] for row in block_rows if row[col_idx]]
            combined_cell = merge_unique_parts(parts)
            combined_cells[col_idx] = combined_cell.strip() if combined_cell else None
            if not combined_cells[col_idx]:
                continue

            day_num = extract_day_number_at_start(combined_cells[col_idx])
            if day_num:
                explicit_day_numbers[col_idx] = day_num
            if not day_num:
                bbox = get_logical_cell_bbox(table, start_row_idx, col_idx, group_width)
                day_num = extract_day_from_cell_style(page, bbox)
            day_numbers[col_idx] = day_num

        base_candidates = [
            explicit_day_numbers[col_idx] - col_idx
            for col_idx in range(7)
            if explicit_day_numbers[col_idx]
        ]

        if base_candidates:
            block_base_day = Counter(base_candidates).most_common(1)[0][0]
        else:
            block_base_day = 1 - expected_start_col + (block_idx * 7)

        expected_by_col = [None] * 7
        for col_idx in range(7):
            expected_day = block_base_day + col_idx
            if 1 <= expected_day <= cal_days_in_m:
                expected_by_col[col_idx] = expected_day

        for col_idx in range(7):
            if not combined_cells[col_idx]:
                continue
            expected_day = expected_by_col[col_idx]
            if not expected_day:
                continue
            current_day = day_numbers[col_idx]
            if current_day is None or current_day != expected_day:
                day_numbers[col_idx] = expected_day

        # Infer missing days
        for col_idx in range(7):
            if not combined_cells[col_idx] or day_numbers[col_idx]:
                continue
            left_idx = None
            for i in range(col_idx - 1, -1, -1):
                if day_numbers[i]:
                    left_idx = i
                    break
            right_idx = None
            for i in range(col_idx + 1, 7):
                if day_numbers[i]:
                    right_idx = i
                    break
            inferred = None
            if left_idx is not None and right_idx is not None:
                span = right_idx - left_idx
                if (day_numbers[right_idx] - day_numbers[left_idx]) == span:
                    inferred = day_numbers[left_idx] + (col_idx - left_idx)
            elif left_idx is not None:
                inferred = day_numbers[left_idx] + (col_idx - left_idx)
            elif right_idx is not None:
                inferred = day_numbers[right_idx] - (right_idx - col_idx)

            if inferred and 1 <= inferred <= 31:
                day_numbers[col_idx] = inferred

        for col_idx in range(7):
            cleaned_cell = combined_cells[col_idx]
            if not cleaned_cell:
                continue

            entry_days = []
            base_day = day_numbers[col_idx]
            if base_day and 1 <= base_day <= 31:
                entry_days.append(base_day)

            for overlay_day in extract_overlay_day_numbers(cleaned_cell, base_day):
                if overlay_day not in entry_days:
                    entry_days.append(overlay_day)
            
            if not entry_days:
                continue
            
            # Create entries for each identified day
            # For cells with multiple days (overlays), we need to SPLIT the text 
            # so that the second day gets its own content, not just a copy of the whole cell.
            
            cell_text_map = { d: cleaned_cell for d in entry_days }
            
            # Attempt to split text if we have multiple days and they seem stacked
            if len(entry_days) > 1:
                sorted_days = sorted(entry_days)
                # Simple heuristic: If we found a "stacked" day (day[i+1] = day[i] + 7), 
                # try to split the text at that number.
                
                # We only support splitting 2 stacked days for now as that's the common case.
                if len(sorted_days) == 2 and sorted_days[1] == sorted_days[0] + 7:
                    d1, d2 = sorted_days
                    
                    # Find the split point (the appearance of d2 on a new line or start line)
                    # Support both stacked (newline + d2) and slash ( / d2 ) formats
                    
                    # Pattern 1: Stacked - (\n or ^) + whitespace + d2 + (whitespace or $)
                    p_stack = r'(?:^|[\n\r])\s*(' + str(d2) + r')(?=\s|$)'
                    
                    # Pattern 2: Slash - / + whitespace + d2 + (whitespace or $)
                    # We look for slash preceded by space or newline, and followed by d2
                    p_slash = r'(?:^|\s)/\s*(' + str(d2) + r')(?=\s|$)'
                    
                    split_match = re.search(p_stack, cleaned_cell)
                    if not split_match:
                        split_match = re.search(p_slash, cleaned_cell)
                    
                    if split_match:
                        split_start = split_match.start()
                        d2_start_idx = split_match.start(1) # The start of the number itself
                        
                        # d1 text is everything before the match start
                        # (in slash case, before the /)
                        t1 = cleaned_cell[:split_start].strip()
                        
                        # d2 text is everything from the number onwards
                        # (skipping the split pattern prefix like \n or / )
                        t2 = cleaned_cell[d2_start_idx:].strip()
                        
                        cell_text_map[d1] = t1
                        cell_text_map[d2] = t2

            explicit_day = extract_day_number_at_start(cleaned_cell)
            
            yy = year[-2:]
            mm = month_num
            for day_num in entry_days:
                # Get the specific text for this day
                day_raw_text = cell_text_map.get(day_num, cleaned_cell)
                
                dd = f"{day_num:02d}"
                date_id = f"{mm}{dd}{yy}"
                new_entry = {
                    "Date": date_id,
                    "Year": year,
                    "Month": month_name_raw,
                    "Day": day_num,
                    "Raw Text": day_raw_text
                }
                results.append(new_entry)
    
    return results

def process_pdfs(root_dir):
    results = []
    
    root_path = Path(root_dir)
    # Ensure deterministic processing order
    for year_dir in sorted(root_path.glob("20*")):
        if not year_dir.is_dir():
            continue
            
        year = year_dir.name
        print(f"Processing year {year}...")
        
        pdf_files = sorted(year_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            print(f"  Processing file: {pdf_file.name}")
            
            parts = pdf_file.stem.split()
            month_name_raw = parts[-1] if len(parts) > 1 else pdf_file.stem
            month_num = MONTH_MAP.get(month_name_raw.lower())
            
            if not month_num:
                print(f"    Warning: Could not identify month from '{month_name_raw}'. Skipping.")
                continue

            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        tables = page.find_tables()
                        if not tables:
                            continue

                        for table in tables:
                            table_results = process_table_month(table, page, year, month_num, month_name_raw)
                            results.extend(table_results)
                    # Table cell text already contains full daily content; no cross-cell merging needed.

            except Exception as e:
                print(f"    Error processing {pdf_file.name}: {e}")

    deduped_results = dedupe_entries_by_date(results)
    return [enrich_entry(entry) for entry in deduped_results]

def main():
    calendars_dir = Path(__file__).parent
    data = process_pdfs(calendars_dir)
    sorted_data = sorted(data, key=csv_sort_key)
    write_output_files(calendars_dir, sorted_data)

if __name__ == "__main__":
    main()
