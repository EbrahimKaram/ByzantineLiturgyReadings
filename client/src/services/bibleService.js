const BASE_URL = 'https://bible-api.com';

export async function fetchScriptureText(reference) {
  if (!reference) return null;

  // 1. Clean the reference
  const cleanRef = reference
    .replace(/^(Epistle|Gospel)\s*/i, '')
    .replace(/–/g, '-')
    .replace(/\s*:\s*/g, ':') // Remove spaces around colons
    .replace(/\s*-\s*/g, '-') // Remove spaces around hyphens
    .trim()
    .replace(/[.;]+$/, ''); // Remove trailing periods or semicolons

  try {
    // 2. Split by semicolon to handle multiple ranges
    const parts = cleanRef.split(';');
    let fullHtml = '';
    let lastBook = '';
    let lastChapter = '';

    for (let part of parts) {
      part = part.trim();
      if (!part) continue;

      let queryRef = part;
      
      // Check if this part has a book name (e.g. "Heb. 11:9")
      const hasLetters = /[a-zA-Z]/.test(part);

      if (hasLetters) {
        queryRef = part;
        // Update context
        const match = part.match(/^((?:\d\s*)?[a-zA-Z\.]+)\s*(\d+)?/);
        if (match) {
          lastBook = match[1];
          if (match[2]) lastChapter = match[2];
        }
      } else {
        // It's a continuation.
        if (part.includes(':')) {
          // New chapter, same book
          queryRef = `${lastBook} ${part}`;
          const chMatch = part.match(/^(\d+):/);
          if (chMatch) lastChapter = chMatch[1];
        } else {
          // Same chapter, same book
          queryRef = `${lastBook} ${lastChapter}:${part}`;
        }
      }

      // 3. Fetch this specific chunk
      const chunkHtml = await fetchSinglePassage(queryRef);
      if (chunkHtml) {
        fullHtml += (fullHtml ? '<div class="my-4 text-center text-stone-400 text-xs tracking-widest">***</div>' : '') + chunkHtml;
      }
    }

    return fullHtml || null;

  } catch (error) {
    console.error("Error fetching scripture:", error);
    return null;
  }
}

async function fetchSinglePassage(ref) {
  try {
    const response = await fetch(`${BASE_URL}/${encodeURIComponent(ref)}?translation=dra`);
    if (!response.ok) return null;
    const data = await response.json();
    
    // Transform verses into HTML with superscript numbers
    return data.verses.map(v => 
      `<span class="text-xs align-top text-red-800 dark:text-red-400 font-bold mr-0.5 select-none">${v.verse}</span>${v.text}`
    ).join(' ');
    
  } catch (e) {
    console.error(`Failed to fetch part: ${ref}`, e);
    return null;
  }
}
