param(
    [Parameter(Mandatory=$false)]
    [string]$Year = "$(Get-Date -Format 'yyyy')"
)

# To run the script, use:
# .\Script_to_get_pdfs.ps1 -Year 2025


# 1. Setup
$uploadYear = [int]$Year - 1
# Based on 2024-2026 data, files are hosted here:
$baseUrl = "https://files.ecatholic.com/25848/documents/$uploadYear/12"
$outputDir = Join-Path $PSScriptRoot $Year

Write-Host "Targeting Year: $Year"
Write-Host "Predicting Source Base URL: $baseUrl"

if (-not (Test-Path -Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    Write-Host "Created directory: $outputDir"
}

$months = [System.Globalization.DateTimeFormatInfo]::CurrentInfo.MonthNames[0..11]

# 2. Loop through months and try Patterns
$monthCounter = 1
foreach ($month in $months) {
    $monthNum = $monthCounter.ToString("00")
    $downloaded = $false
    
    # We want to save everything as "MM Calendar YYYY Month.pdf" for consistency
    $finalFileName = "$monthNum Calendar $Year $month.pdf"
    $outputPath = Join-Path $outputDir $finalFileName

    # Possible naming patterns on the server
    $patterns = @(
        "Calendar $Year $month.pdf",  # Modern (2025/2026)
        "$month.pdf"                  # Legacy (2024)
    )

    foreach ($pattern in $patterns) {
        # Encode URL (spaces becomes %20)
        $urlEncodedName = $pattern.Replace(" ", "%20") 
        
        $url = "$baseUrl/$urlEncodedName"

        try {
            # Try to download
            Invoke-WebRequest -Uri $url -OutFile $outputPath -ErrorAction Stop
            Write-Host "Success: $month (Found as '$pattern')" -ForegroundColor Green
            $downloaded = $true
            break # Stop checking other patterns for this month
        }
        catch {
            # 404 Not Found is expected if we check the wrong pattern first
        }
    }

    if (-not $downloaded) {
        Write-Warning "Could not find file for $month at $baseUrl"
    }
    $monthCounter++
}

# 3. Handle Special Announcements (and check for known typos)
$announcementPatterns = @(
    "Special Calendar Announcements.pdf", 
    "Special Calendar Anouncements.pdf" # 2026 file has this typo
)
$announcementOut = Join-Path $outputDir "Special Calendar Announcements.pdf"

foreach ($pattern in $announcementPatterns) {
    $urlEncodedName = $pattern.Replace(" ", "%20")
    $url = "$baseUrl/$urlEncodedName"
    try {
        Invoke-WebRequest -Uri $url -OutFile $announcementOut -ErrorAction Stop
        Write-Host "Success: Special Announcements (Found as '$pattern')" -ForegroundColor Green
        break
    } catch {}
}