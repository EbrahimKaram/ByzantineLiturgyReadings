export function parseReadingDescription(description) {
  if (!description) return {};

  // Start with a clean working copy
  let workText = description.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  // Helper to clean extracted values (remove trailing punctuation)
  const clean = (s) => s?.trim().replace(/^[;:,.\-\s]+|[;:,.\-\s]+$/g, '') || null;

  // 1. Extract Tone
  let tone = null;
  const toneMatch = workText.match(/Tone\s+(\d+)/i);
  if (toneMatch) {
    tone = toneMatch[1];
    workText = workText.replace(toneMatch[0], '');
  }

  // 2. Extract Matins
  let matinsGospel = null;
  const matinsResMatch = workText.match(/Res\.?\s*Gospel\s+(\d+)/i);

  if (matinsResMatch) {
    matinsGospel = matinsResMatch[1];
    workText = workText.replace(matinsResMatch[0], '');
  } else {
    // Look for explicit Matins Gospel phrase, stopping before other major keywords
    const matinsTextMatch = workText.match(/Matins\s+Gospel:?\s*(.+?)(?=\s*(?:Divine Liturgy|Epistle|Gospel|Following)|$)/i);
    if (matinsTextMatch) {
      matinsGospel = clean(matinsTextMatch[1]);
      workText = workText.replace(matinsTextMatch[0], '');
    }
  }

  // 3. Prepare for Liturgy Parsing
  let epistle = null;
  let gospel = null;

  // Check for implicit "Divine Liturgy: <Epistle>; <Gospel>" pattern first (where labels are missing)
  // This must look at description or workText before stripping "Divine Liturgy" blindly
  // We match "Divine Liturgy" followed by texts separated by semicolon, ending at period or "Following"
  const implicitMatch = workText.match(/Divine Liturgy:?\s*([^;]+);\s*([^;]+?)(?=\s*(?:Following|\.\s*[A-Z]|$))/i);

  if (implicitMatch) {
    // If we found the implicit pair, capture them and remove the whole segment
    epistle = clean(implicitMatch[1]);
    gospel = clean(implicitMatch[2]);
    workText = workText.replace(implicitMatch[0], '');
  } else {
    // Fallback: Remove "Divine Liturgy" header if present to clean up the text for keyword search
    workText = workText.replace(/Divine Liturgy:?/i, '');

    // 4. Extract Epistle
    // Look for "Epistle:" followed by text until "Gospel" or end
    const epistleMatch = workText.match(/(?:^|[\s,;.])Epistle:?\s*(.+?)(?=\s*(?:Gospel|Following)|$)/i);
    if (epistleMatch) {
      epistle = clean(epistleMatch[1]);
      workText = workText.replace(epistleMatch[0], '');
    }

    // 5. Extract Gospel
    // Look for "Gospel:" followed by text until "Following", a new sentence with Capital Letter, or end
    const gospelMatch = workText.match(/(?:^|[\s,;.])Gospel:?\s*(.+?)(?=\s*(?:Following|\.\s+[A-Z])|$)/i);
    if (gospelMatch) {
      gospel = clean(gospelMatch[1]);
      workText = workText.replace(gospelMatch[0], '');
    }
  }

  // 6. Extract Notes (Whatever is left)
  // Clean up remaining punctuation and "Following" label
  let notes = workText
    // .replace(/Following[:\s]*/i, '') // Remove "Following" keyword if it remains
    .replace(/^[\s,;.]+|[\s,;.]+$/g, '')  // Trim punctuation from start/end
    .replace(/\s+([,;.])/g, '$1')         // Remove space before punctuation (e.g. " ,")
    .replace(/[,;]+\s*\./g, '.')          // Fix combined separators (e.g. ",." -> ".")
    .replace(/\.\s*[,;]+/g, '.')          // Fix dot followed by comma/semicolon
    .replace(/,,+/g, ',')                 // Fix multiple commas (was previously removing them)
    .replace(/\.\.+/g, '.')               // Fix multiple dots
    .trim();
  
  return {
    tone,
    matinsGospel,
    epistle,
    gospel,
    notes: notes || null
  };
}
