$content = @"
param(
    [Parameter(Mandatory=$false)]
    [string]$Year = "2025"
)

# Base URL containing the calendars
$baseUrl = "https://romaniancatholic.org/liturgical-calendar"

Write-Host "Scraping $baseUrl for $Year calendars..."

try {
    # Download the page content
    $page = Invoke-WebRequest -Uri $baseUrl -UseBasicParsing
}
catch {
    Write-Error "Failed to retrieve the webpage: $_"
    exit 1
}

# Create output directory
$outputDir = Join-Path $PSScriptRoot $Year
if (-not (Test-Path -Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    Write-Host "Created directory: $outputDir"
}

# Find all PDF links containing "Calendar <Year>"
# We match hrefs that contain "Calendar", the Year, and end in ".pdf"
$regexPattern = 'href="([^"]*Calendar(?:%20|\s)' + $Year + '[^"]+\.pdf[^"]*)"'
$matches = [regex]::Matches($page.Content, $regexPattern, "IgnoreCase")

if ($matches.Count -eq 0) {
    Write-Warning "No calendar PDFs found for year $Year."
    Write-Host "Available links might not match the pattern 'Calendar $Year'. Please check the website."
    return
}

Write-Host "Found $($matches.Count) calendar files."

foreach ($match in $matches) {
    $url = $match.Groups[1].Value
    
    if ($url -notmatch "^http") {
        $uri = [System.Uri]$baseUrl
        # Simple join for root-relative paths
        if ($url.StartsWith("/")) {
            $url = "$($uri.Scheme)://$($uri.Host)$url"
        } else {
            $url = "$($uri.Scheme)://$($uri.Host)/$url"
        }
    }

    try {
        $uriObj = [System.Uri]$url
        $segment = $uriObj.Segments[-1]
        
        # Decode URL (e.g. %20 -> space)
        $fileName = [System.Net.WebUtility]::UrlDecode($segment)
        
        $outputPath = Join-Path $outputDir $fileName
        
        Write-Host "Downloading: $fileName"
        Invoke-WebRequest -Uri $url -OutFile $outputPath
    }
    catch {
        Write-Error "Failed to download $url : $_"
    }
}

Write-Host "Download complete. Files saved to $outputDir"
"@
