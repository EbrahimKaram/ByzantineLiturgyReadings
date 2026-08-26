import json
from datetime import datetime, timedelta
import os

def check_missing_dates(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {json_path}")
        return

    dates_present = set()
    
    for entry in data:
        date_str = entry.get("Date")
        if date_str:
            try:
                # The format seems to be MMDDYY based on "010124"
                date_obj = datetime.strptime(date_str, "%m%d%y").date()
                dates_present.add(date_obj)
            except ValueError:
                print(f"Warning: Could not parse date: {date_str}")
                continue

    if not dates_present:
        print("No valid dates found in the file.")
        return

    min_date = min(dates_present)
    max_date = max(dates_present)
    
    print(f"Checking range from {min_date} to {max_date}")
    
    current_date = min_date
    missing_dates = []
    
    while current_date <= max_date:
        if current_date not in dates_present:
            missing_dates.append(current_date)
        current_date += timedelta(days=1)
        
    if missing_dates:
        print(f"Found {len(missing_dates)} missing dates:")
        for d in missing_dates:
            print(d.strftime('%Y-%m-%d'))
    else:
        print("No missing dates found in the range.")

if __name__ == "__main__":
    json_file = os.path.join(os.path.dirname(__file__), 'extracted_readings.json')
    check_missing_dates(json_file)
