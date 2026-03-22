const BASE_URL = 'https://bible-api.com';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

function isFreshCacheEntry(entry) {
  if (!entry || typeof entry !== 'object') return false;
  if (typeof entry.cachedAt !== 'number') return false;
  return Date.now() - entry.cachedAt < CACHE_TTL_MS;
}

export async function fetchScriptureText(reference) {
  if (!reference) return null;

  // 1. Clean the reference
  const cleanRef = reference
    // Handle prefixes like "2, Gospel Lk" or simple "Epistle "
    .replace(/^(?:[\d\s,]*)(Epistle|Gospel)\s*/i, '')
    // Clean typical suffix garbage (e.g. annotations like "Hippolytus, martyr")
    .replace(/\s+[A-Za-z\s,]*martyr.*/i, '')
    .replace(/–/g, '-')
    .replace(/\s+to\s+/gi, '-') // Normalize textual ranges (e.g. "14 to 5:6")
    .replace(/\s+and\s+/gi, ';') // Treat textual 'and' as semicolon splits
    // Fix colons or commas incorrectly placed right after book abbreviations (e.g. "Acts: 2", "John, 12")
    .replace(/([a-zA-Z]+[.]?)[:\,]\s*(\d+)/g, '$1 $2')
    // Remove periods right after alphabetical book abbreviations (e.g. "Phil.", "Rom.")
    .replace(/([a-zA-Z])\./g, '$1')
    // Fix European comma as colon e.g. "Heb 7,26-28" ONLY if followed by verse-dash
    .replace(/([a-zA-Z]+\s+\d+),(\d+-)/g, '$1:$2')
    .replace(/\s*:\s*/g, ':') // Remove spaces around colons
    .replace(/\s*-\s*/g, '-') // Remove spaces around hyphens
    // Treat commas as semicolons to break sequential disjoint verses (e.g. "11:24, 32" -> "11:24; 32")
    .replace(/,/g, ';')
    // Fix for "Verse-Verse-Chapter:Verse" patterns (e.g. "8:8-13-9:1-2") which should be semicolon separated
    .replace(/(\d+-\d+)-(\d+:)/g, '$1;$2')
    // Fix for space-separated cross-chapter ranges (e.g. "1:10-14 2:1-4")
    .replace(/(\d+-\d+)\s+(\d+:)/g, '$1;$2')
    // Fix for dot-separated cross-chapter ranges (e.g. "11:31-33. 12:1-10")
    .replace(/(\d+)\.\s+(\d+:)/g, '$1;$2')
    // Remove alphabetical markings from verses that break APIs (e.g., 7:5a -> 7:5)
    .replace(/(\d)[ab]\b/gi, '$1')
    .trim()
    .replace(/[.;,]+$/, ''); // Remove trailing periods, semicolons, or commas

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
        // Check if the chapter shifts within this part (e.g. "Acts 6:8-7:5")
        const endChMatch = part.match(/-(\d+):/);
        if (endChMatch) lastChapter = endChMatch[1];
      } else {
        // It's a continuation.
        if (part.includes(':')) {
          if (part.match(/^\d+-/)) {
            // Starts with a verse, jumping to new chapter: e.g. "32-12:1"
            queryRef = `${lastBook} ${lastChapter}:${part}`;
            
            // Update lastChapter if it jumps across chapters
            const endChMatch = part.match(/-(\d+):/);
            if (endChMatch) lastChapter = endChMatch[1];
          } else {
            // New chapter, same book: e.g. "16:1" or "16:1-2"
            queryRef = `${lastBook} ${part}`;
            const chMatch = part.match(/^(\d+):/);
            if (chMatch) lastChapter = chMatch[1];
            
            // Update lastChapter if it jumps internally as well
            const endChMatch = part.match(/-(\d+):/);
            if (endChMatch) lastChapter = endChMatch[1];
          }
        } else {
          // Same chapter, same book: e.g. "17-27"
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
  const cacheKey = `bible_text_${ref}`;
  
  // 1. Check Cache
  try {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (isFreshCacheEntry(parsed)) {
        return parsed.value;
      }

      localStorage.removeItem(cacheKey);
    }
  } catch (e) {
    // Ignore potential input errors
  }

  try {
    const response = await fetch(`${BASE_URL}/${encodeURIComponent(ref)}?translation=dra`);
    if (!response.ok) return null;
    const data = await response.json();
    
    // Transform verses into HTML with superscript numbers
    const htmlContent = data.verses.map(v => 
      `<span class="text-xs align-top text-red-800 dark:text-red-400 font-bold mr-0.5 select-none">${v.verse}</span>${v.text}`
    ).join(' ');
    const cachePayload = { cachedAt: Date.now(), value: htmlContent };

    // 2. Save to Cache
    try {
      localStorage.setItem(cacheKey, JSON.stringify(cachePayload));
    } catch (e) {
      // Quota exceeded or disabled
    }

    return htmlContent;
    
  } catch (e) {
    console.error(`Failed to fetch part: ${ref}`, e);
    return null;
  }
}
