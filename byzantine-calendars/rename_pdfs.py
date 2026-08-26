import os
from pathlib import Path

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
}

def rename_pdfs(root_dir):
    root_path = Path(root_dir)
    renamed_count = 0

    for year_dir in root_path.glob("20*"):
        if not year_dir.is_dir():
            continue
            
        print(f"Processing directory: {year_dir}")
        for pdf_file in year_dir.glob("*.pdf"):
            filename = pdf_file.name
            
            # check if already has prefix (starts with digit digit)
            if filename[:2].isdigit():
                print(f"  Skipping {filename} (already has prefix)")
                continue

            # Try to identify month from filename
            # filename format expected: "Calendar YYYY Month.pdf"
            # We split by space and look for a month keyword
            
            parts = pdf_file.stem.split()
            found_month = None
            found_month_num = None
            
            # iterate parts backwards to find month
            for part in reversed(parts):
                clean_part = part.lower().strip()
                if clean_part in MONTH_MAP:
                    found_month = part
                    found_month_num = MONTH_MAP[clean_part]
                    break
            
            if found_month_num:
                new_filename = f"{found_month_num} {filename}"
                old_path = pdf_file
                new_path = pdf_file.parent / new_filename
                
                try:
                    os.rename(old_path, new_path)
                    print(f"  Renamed: '{filename}' -> '{new_filename}'")
                    renamed_count += 1
                except Exception as e:
                    print(f"  Error renaming {filename}: {e}")
            else:
                 print(f"  Could not identify month in '{filename}'")

    print(f"\nTotal files renamed: {renamed_count}")

if __name__ == "__main__":
    calendars_dir = Path(__file__).parent
    rename_pdfs(calendars_dir)
