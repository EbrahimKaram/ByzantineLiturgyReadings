$files = @{
    "Calendar 2026 January.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20January.pdf?t=1764694572000";
    "Calendar 2026 February.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20February.pdf?t=1764694675000";
    "Calendar 2026 March.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20March.pdf?t=1764694702000";
    "Calendar 2026 April.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20April.pdf?t=1764694727000";
    "Calendar 2026 May.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20May.pdf?t=1764694751000";
    "Calendar 2026 June.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20June.pdf?t=1764694770000";
    "Calendar 2026 July.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20July.pdf?t=1764694792000";
    "Calendar 2026 August.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20August.pdf?t=1764694819000";
    "Calendar 2026 September.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20September.pdf?t=1764694841000";
    "Calendar 2026 October.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20October.pdf?t=1764694863000";
    "Calendar 2026 November.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20November.pdf?t=1764694884000";
    "Calendar 2026 December.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Calendar%202026%20December.pdf?t=1764694905000";
    "Special Calendar Announcements.pdf" = "https://files.ecatholic.com/25848/documents/2025/12/Special%20Calendar%20Anouncements.pdf?t=1764696432000"
}

foreach ($item in $files.GetEnumerator()) {
    $outputPath = Join-Path "calendars/2026" $item.Key
    Write-Host "Downloading $($item.Key)..."
    try {
        Invoke-WebRequest -Uri $item.Value -OutFile $outputPath
    } catch {
        Write-Error "Failed to download $($item.Key): $_"
    }
}