import pdfplumber
import re
import json
import csv
import os
from pathlib import Path
from datetime import date

# Regex patterns matching the logic in ReadingCard.vue
TAGS_RE = re.compile(r'<[^>]*>')
WHITESPACE_RE = re.compile(r'\s+')
TONE_RE = re.compile(r'Tone\s+(\d+)', re.IGNORECASE)
MATINS_RES_RE = re.compile(r'Res\.?\s*Gospel\s+(\d+)', re.IGNORECASE)
MATINS_TEXT_RE = re.compile(r'Matins\s+Gospel:?\s*(.+?)(?=\s*(?:Divine Liturgy|Epistle|Gospel|Following)|$)', re.IGNORECASE)
IMPLICIT_LITURGY_RE = re.compile(r'Divine Liturgy:?\s*([^;]+);\s*([^;]+?)(?=\s*(?:Following|\.\s*[A-Z]|$))', re.IGNORECASE)
EPISTLE_RE = re.compile(r'(?:^|[\s,;.])(?:Epistle|Ep\.?):?\s*(.+?)(?=\s*(?:Gospel|Following)|$)', re.IGNORECASE)
GOSPEL_RE = re.compile(r'(?:^|[\s,;.])Gospel:?\s*(.+?)(?=\s*(?:Following|\.\s+[A-Z])|$)', re.IGNORECASE)
FOLLOWING_RE = re.compile(r'Following[:\s]*', re.IGNORECASE)
DIVINE_LITURGY_HEADER_RE = re.compile(r'Divine Liturgy:?', re.IGNORECASE)
FASTING_RE = re.compile(r'(Strict Fast and abstinence|Common Abstinence|Strict Fast|Abstinence|Dispensation\s*\([^)]+\)|Dispensation)', re.IGNORECASE)

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

def parse_reading_text(text):
    if not text:
        return None

    # Start with a clean working copy
    work_text = TAGS_RE.sub(' ', text)
    work_text = WHITESPACE_RE.sub(' ', work_text).strip()

    # 0. Extract Fasting/Abstinence (Look for it early to remove it from Title/notes)
    fasting = None
    fasting_match = FASTING_RE.search(work_text)
    if fasting_match:
        fasting = fasting_match.group(1)
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
        epistle = clean_string(implicit_match.group(1))
        gospel = clean_string(implicit_match.group(2))
        work_text = work_text.replace(implicit_match.group(0), '')
    else:
        # Clear Liturgy Header if present
        work_text = DIVINE_LITURGY_HEADER_RE.sub('', work_text)

        # 4. Extract Epistle
        epistle_match = EPISTLE_RE.search(work_text)
        if epistle_match:
            epistle = clean_string(epistle_match.group(1))
            work_text = work_text.replace(epistle_match.group(0), '')

        # 5. Extract Gospel
        gospel_match = GOSPEL_RE.search(work_text)
        if gospel_match:
            gospel = clean_string(gospel_match.group(1))
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
        "notes": notes if notes else None
    }

def extract_day_number(text):
    # Look for a number at the very start
    match = re.search(r'\b(\d{1,2})\b', text)
    if match:
        return int(match.group(1))
    return None

def extract_day_number_at_start(text):
    if not text:
        return None
    cleaned = text.strip()
    day_match = re.match(r'^(\d{1,2})(?:\s|$|\D)', cleaned)
    if not day_match:
        return None

    day_num = int(day_match.group(1))
    if re.match(r'^\d{1,2}\s*[\-–]\s*\d+', cleaned):
        return None
    if re.match(r'^\d{1,2}\s*[;:]', cleaned):
        return None
    if re.match(r'^\d\s+(?:Tim|Cor|Pet|John|Kgs|Sam|Chr|Thess|Macc|Ki|Sa|Co|Ti|Pe|Jo)', cleaned, re.IGNORECASE):
        return None

    return day_num if 1 <= day_num <= 31 else None

def is_weekday_header_row(row):
    if not row:
        return False

    tokens = []
    for cell in row[:7]:
        if not cell:
            continue
        first = re.split(r'\s+', cell.strip().lower())[0]
        first = re.sub(r'[^a-z]', '', first)
        if first:
            tokens.append(first)

    if len(tokens) < 4:
        return False

    weekday_hits = sum(1 for token in tokens if token in WEEKDAY_TOKENS)
    return weekday_hits >= 4

def is_week_row(row):
    if not row:
        return False
    cells = row[:7]
    day_hits = sum(1 for cell in cells if extract_day_number_at_start(cell))
    return day_hits >= 2

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
    # Remove the day number if it appears at the start of the notes
    if day:
        # Regex to match the day number at the start, possibly followed by punctuation
        pattern = fr'^{day}[\s,.-]*'
        return re.sub(pattern, '', notes).strip()
    return notes.strip()

def process_pdfs(root_dir):
    results = []
    
    root_path = Path(root_dir)
    for year_dir in root_path.glob("20*"):
        if not year_dir.is_dir():
            continue
            
        year = year_dir.name
        print(f"Processing year {year}...")
        
        for pdf_file in year_dir.glob("*.pdf"):
            print(f"  Processing file: {pdf_file.name}")
            
            # extract month from filename key
            parts = pdf_file.stem.split()
            month_name_raw = parts[-1] if len(parts) > 1 else pdf_file.stem
            month_num = MONTH_MAP.get(month_name_raw.lower())
            
            if not month_num:
                print(f"    Warning: Could not identify month from '{month_name_raw}'. Skipping.")
                continue

            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        tables = page.find_tables()

                        if not tables:
                            continue

                        for table in tables:
                            extracted_rows = table.extract() or []
                            if not extracted_rows:
                                continue

                            normalized_rows = []
                            for row_idx, row in enumerate(extracted_rows):
                                row = row or []
                                if len(row) < 7:
                                    row = row + [None] * (7 - len(row))
                                elif len(row) > 7:
                                    row = row[:7]
                                normalized_rows.append((row_idx, row))

                            week_rows = []
                            for row_idx, row in normalized_rows:
                                if is_weekday_header_row(row):
                                    continue
                                if is_week_row(row):
                                    week_rows.append((row_idx, row))

                            if len(week_rows) > 5:
                                week_rows = week_rows[:5]

                            for row_idx, row in week_rows:
                                for col_idx in range(7):
                                    cell = row[col_idx]
                                    if not cell:
                                        continue

                                    cleaned_cell = cell.strip()
                                    if not cleaned_cell:
                                        continue

                                    day_num = extract_day_number_at_start(cleaned_cell)
                                    if not day_num:
                                        bbox = get_table_cell_bbox(table, row_idx, col_idx)
                                        day_num = extract_day_from_cell_style(page, bbox)

                                    if not day_num:
                                        continue

                                    yy = year[-2:]
                                    dd = f"{day_num:02d}"
                                    mm = month_num
                                    date_id = f"{mm}{dd}{yy}"

                                    new_entry = {
                                        "Date": date_id,
                                        "Year": year,
                                        "Month": month_name_raw,
                                        "Day": day_num,
                                        "Raw Text": cleaned_cell
                                    }
                                    results.append(new_entry)
                                
                    # Table cell text already contains full daily content; no cross-cell merging needed.

            except Exception as e:
                print(f"    Error processing {pdf_file.name}: {e}")

    # Final Pass: Parse fields from the aggregated Raw Text
    final_results = []
    for entry in results:
        parsed = parse_reading_text(entry["Raw Text"])
        title = clean_title(parsed['notes'], entry['Day'])
        
        # Determine Holy Day of Obligation
        is_holy_day = False
        
        # Check if Sunday
        try:
            # Entry has Year (str), Date (MMDDYY), Day (int)
            mm = int(entry["Date"][:2])
            dd = int(entry["Day"])
            yyyy = int(entry["Year"])
            dt = date(yyyy, mm, dd)
            if dt.weekday() == 6: # Sunday
                is_holy_day = True
        except Exception:
            pass

        # Check Raw Text
        if re.search(r'Holy Day of Obligation', entry["Raw Text"], re.IGNORECASE):
            is_holy_day = True

        entry.update({
            "Title": title,
            "Tone": parsed['tone'],
            "Matins Gospel": parsed['matinsGospel'],
            "Epistle": parsed['epistle'],
            "Gospel": parsed['gospel'],
            "Fasting": parsed['fasting'],
            "Holy Day of Obligation": is_holy_day
        })
        final_results.append(entry)

    return final_results

if __name__ == "__main__":
    calendars_dir = Path(__file__).parent
    data = process_pdfs(calendars_dir)
    
    # Save as JSON (optional, keep for debugging)
    json_output = calendars_dir / "extracted_readings.json"
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Save as CSV
    csv_output = calendars_dir / "readings.csv"
    csv_columns = ["Date", "Title", "Tone", "Matins Gospel", "Epistle", "Gospel", "Fasting", "Holy Day of Obligation", "Raw Text"]
    
    with open(csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
    print(f"Extraction complete. Saved to {csv_output}")
