import pdfplumber
import re
import json
import csv
import os
from pathlib import Path

# Regex patterns matching the logic in ReadingCard.vue
TAGS_RE = re.compile(r'<[^>]*>')
WHITESPACE_RE = re.compile(r'\s+')
TONE_RE = re.compile(r'Tone\s+(\d+)', re.IGNORECASE)
MATINS_RES_RE = re.compile(r'Res\.?\s*Gospel\s+(\d+)', re.IGNORECASE)
MATINS_TEXT_RE = re.compile(r'Matins\s+Gospel:?\s*(.+?)(?=\s*(?:Divine Liturgy|Epistle|Gospel|Following)|$)', re.IGNORECASE)
IMPLICIT_LITURGY_RE = re.compile(r'Divine Liturgy:?\s*([^;]+);\s*([^;]+?)(?=\s*(?:Following|\.\s*[A-Z]|$))', re.IGNORECASE)
EPISTLE_RE = re.compile(r'(?:^|[\s,;.])Epistle:?\s*(.+?)(?=\s*(?:Gospel|Following)|$)', re.IGNORECASE)
GOSPEL_RE = re.compile(r'(?:^|[\s,;.])Gospel:?\s*(.+?)(?=\s*(?:Following|\.\s+[A-Z])|$)', re.IGNORECASE)
FOLLOWING_RE = re.compile(r'Following[:\s]*', re.IGNORECASE)
DIVINE_LITURGY_HEADER_RE = re.compile(r'Divine Liturgy:?', re.IGNORECASE)

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
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
        "notes": notes if notes else None
    }

def extract_day_number(text):
    # Look for a number at the very start
    match = re.search(r'\b(\d{1,2})\b', text)
    if match:
        return int(match.group(1))
    return None

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
                        tables = page.extract_tables()
                        
                        # Use a column-based state to track active entries for merging
                        # Assuming max 7 columns for a week, but can be dynamic. 
                        # We use a dictionary keyed by column index.
                        active_entries = {} 

                        if tables:
                            for table in tables:
                                for row in table:
                                    for col_idx, cell in enumerate(row):
                                        if not cell:
                                            continue
                                            
                                        cleaned_cell = cell.strip()
                                        if not cleaned_cell:
                                            continue

                                        # Strict Day Number Check: Must be at start
                                        day_match = re.match(r'^(\d{1,2})(?:\s|$|\D)', cleaned_cell)
                                        day_num = int(day_match.group(1)) if day_match else None
                                        
                                        # Filter out unlikely day numbers (e.g. "16" in "16 - 20")
                                        # Heuristic: If it looks like a verse range "16 - 20" or "16-20", it is not a day.
                                        if day_num:
                                            if re.match(r'^\d{1,2}\s*[\-–]\s*\d+', cleaned_cell):
                                                day_num = None

                                        if day_num:
                                            # New Day Found: Create Entry
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
                                                # Other fields parsed later
                                            }
                                            active_entries[col_idx] = new_entry
                                            results.append(new_entry)
                                        
                                        else:
                                            # Continuation Text?
                                            if col_idx in active_entries:
                                                # Append text to existing entry and update Raw Text
                                                entry = active_entries[col_idx]
                                                entry["Raw Text"] += "\n" + cleaned_cell
                                            else:
                                                # Orphan text (maybe from header or prev page?)
                                                # For now, ignore or try to append to last added result?
                                                pass

                        else:
                            # Fallback for pages without tables (rare/messy)
                            text = page.extract_text()
                            if text:
                                # Simple day parsing for raw text
                                # This doesn't support the fancy merging unless we parse the layout
                                pass 
                                
                    # After processing all cells, run parsing on the final aggregated texts
                    # Note: We appended to dictionaries inside 'results' list, so they are updated.

            except Exception as e:
                print(f"    Error processing {pdf_file.name}: {e}")

    # Final Pass: Parse fields from the aggregated Raw Text
    final_results = []
    for entry in results:
        parsed = parse_reading_text(entry["Raw Text"])
        title = clean_title(parsed['notes'], entry['Day'])
        
        entry.update({
            "Title": title,
            "Tone": parsed['tone'],
            "Matins Gospel": parsed['matinsGospel'],
            "Epistle": parsed['epistle'],
            "Gospel": parsed['gospel']
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
    csv_columns = ["Date", "Title", "Tone", "Matins Gospel", "Epistle", "Gospel", "Raw Text"]
    
    with open(csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
    print(f"Extraction complete. Saved to {csv_output}")
