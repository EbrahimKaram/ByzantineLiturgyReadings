#!/bin/bash

# # Make it executable first
# chmod +x get_calendars.sh

# # Run for the current year
# ./get_calendars.sh

# # Run for a specific year
# ./get_calendars.sh 2025

# Default to current year if not provided
YEAR=${1:-$(date +%Y)}
UPLOAD_YEAR=$((YEAR - 1))

BASE_URL="https://files.ecatholic.com/25848/documents/$UPLOAD_YEAR/12"
OUTPUT_DIR="./$YEAR"

echo "Targeting Year: $YEAR"
echo "Predicting Source Base URL: $BASE_URL"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Array of months
MONTHS=("January" "February" "March" "April" "May" "June" "July" "August" "September" "October" "November" "December")

# Loop through months
for month in "${MONTHS[@]}"; do
    downloaded=false
    final_filename="Calendar $YEAR $month.pdf"
    output_path="$OUTPUT_DIR/$final_filename"
    
    # Possible naming patterns
    patterns=("Calendar $YEAR $month.pdf" "$month.pdf")
    
    for pattern in "${patterns[@]}"; do
        # Encode spaces to %20
        url_encoded_name="${pattern// /%20}"
        url="$BASE_URL/$url_encoded_name"
        
        # Try to download (fail silently on error)
        if curl -s -f -o "$output_path" "$url"; then
            echo -e "\e[32mSuccess: $month (Found as '$pattern')\e[0m"
            downloaded=true
            break
        fi
    done
    
    if [ "$downloaded" = false ]; then
        echo -e "\e[33mWarning: Could not find file for $month at $BASE_URL\e[0m"
    fi
done

# Handle Special Announcements
announcement_patterns=("Special Calendar Announcements.pdf" "Special Calendar Anouncements.pdf")
announcement_out="$OUTPUT_DIR/Special Calendar Announcements.pdf"

for pattern in "${announcement_patterns[@]}"; do
    url_encoded_name="${pattern// /%20}"
    url="$BASE_URL/$url_encoded_name"
    
    if curl -s -f -o "$announcement_out" "$url"; then
        echo -e "\e[32mSuccess: Special Announcements (Found as '$pattern')\e[0m"
        break
    fi
done

echo "Done! Files saved to $OUTPUT_DIR"
