import { ref, watch, onMounted, onUnmounted } from 'vue';
import { fetchSundayReadings } from '../services/calendarService';
import { getLocalReading } from '../services/localReadingsService';

const TITLE_MATCH_THRESHOLD = 0.8;

const toDateString = (date) => {
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const parseDateFromHash = (hashValue) => {
  if (!hashValue) return null;

  const parts = hashValue.split('-');
  if (parts.length !== 3) return null;

  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  const parsedDate = new Date(year, month, day);

  return Number.isNaN(parsedDate.getTime()) ? null : parsedDate;
};

export function useReadings() {
  const normalizeTitle = (title) => String(title || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ')
    .replace(/\bss\.?\b/gi, 'saints')
    .replace(/\bst\.?\b/gi, 'saint')
    .replace(/\bven\.?\b/gi, 'venerable')
    .replace(/[^a-zA-Z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();

  const tokenOverlapScore = (a, b) => {
    const aTokens = new Set(a.split(' ').filter(Boolean));
    const bTokens = new Set(b.split(' ').filter(Boolean));
    if (!aTokens.size || !bTokens.size) return 0;

    let common = 0;
    for (const token of aTokens) {
      if (bTokens.has(token)) common += 1;
    }

    return common / Math.max(aTokens.size, bTokens.size);
  };

  const bigramDiceScore = (a, b) => {
    const toBigrams = (input) => {
      const compact = input.replace(/\s+/g, '');
      if (compact.length < 2) return [];
      const grams = [];
      for (let i = 0; i < compact.length - 1; i += 1) {
        grams.push(compact.slice(i, i + 2));
      }
      return grams;
    };

    const aBigrams = toBigrams(a);
    const bBigrams = toBigrams(b);
    if (!aBigrams.length || !bBigrams.length) return 0;

    const bCounts = new Map();
    for (const gram of bBigrams) {
      bCounts.set(gram, (bCounts.get(gram) || 0) + 1);
    }

    let intersection = 0;
    for (const gram of aBigrams) {
      const count = bCounts.get(gram) || 0;
      if (count > 0) {
        intersection += 1;
        bCounts.set(gram, count - 1);
      }
    }

    return (2 * intersection) / (aBigrams.length + bBigrams.length);
  };

  const getTitleSimilarity = (a, b) => {
    const normalizedA = normalizeTitle(a);
    const normalizedB = normalizeTitle(b);
    return getNormalizedTitleSimilarity(normalizedA, normalizedB);
  };

  const getNormalizedTitleSimilarity = (normalizedA, normalizedB) => {

    if (!normalizedA || !normalizedB) return 0;
    if (normalizedA === normalizedB) return 1;

    // Avoid fuzzy matches on very short titles
    if (normalizedA.length < 10 || normalizedB.length < 10) return 0;

    const tokenScore = tokenOverlapScore(normalizedA, normalizedB);
    const diceScore = bigramDiceScore(normalizedA, normalizedB);
    return (tokenScore + diceScore) / 2;
  };

  const readings = ref([]);
  const loading = ref(false);
  const error = ref(null);
  let activeLoadId = 0;

  // Helper to get the initial date (today)
  const getInitialDate = () => {
    const hashDate = parseDateFromHash(window.location.hash.substring(1));
    return hashDate || new Date();
  };

  const currentDate = ref(getInitialDate());

  const loadReadings = async () => {
    const loadId = ++activeLoadId;
    loading.value = true;
    error.value = null;
    try {
      // First try to get local reading
      const localReading = getLocalReading(currentDate.value);
      let localEvent = null;
      
      if (localReading) {
        // Format local reading to match the expected structure
        const descriptionParts = [];
        if (localReading.Epistle) descriptionParts.push(`Epistle: ${localReading.Epistle}`);
        if (localReading.Gospel) descriptionParts.push(`Gospel: ${localReading.Gospel}`);
        if (localReading.Tone) descriptionParts.push(`Tone ${localReading.Tone}`);
        if (localReading['Matins Gospel']) descriptionParts.push(`Matins Gospel: ${localReading['Matins Gospel']}`);
        // if (localReading.Fasting) descriptionParts.push(`Fasting: ${localReading.Fasting}`);
        if (localReading.Notes) descriptionParts.push(localReading.Notes);
        
        /* 
        if (localReading['Holy Day of Obligation']) {
           descriptionParts.unshift('✝ Holy Day of Obligation');
        } 
        */

        // Calculate exclusive end date for compatibility with Google Calendar logic in ReadingCard
        // (Google Calendar uses exclusive end dates for all-day events)
        const startDateStr = toDateString(currentDate.value);
            
        const nextDay = new Date(currentDate.value);
        nextDay.setDate(nextDay.getDate() + 1);
        const endDateStr = toDateString(nextDay);

        localEvent = {
          id: localReading.id || localReading.Date, // Fallback ID
          summary: localReading.Title,
          description: descriptionParts.join('\n'),
          htmlLink: '', // Could link to a bible site if we parsed verses
          // New properties
          fasting: localReading.Fasting,
          usaHoliday: localReading['USA Holiday'],
          canadaHoliday: localReading['Canada Holiday'],
          isHolyDayOfObligation: localReading['Holy Day of Obligation'] === true,
          start: { date: startDateStr },
          end: { date: endDateStr }
        };
      }

      let events = [];
      try {
        events = await fetchSundayReadings(currentDate.value);
      } catch (calendarError) {
        if (!localEvent) {
          throw calendarError;
        }
        console.warn('Calendar fetch failed; showing local reading only.', calendarError);
      }
      
      // Sort events: Prioritize events with "Epistle" or "Gospel" in the description
      const sortedCalendarEvents = [...events].sort((a, b) => {
        const aHasReadings = a.description && (a.description.includes('Epistle') || a.description.includes('Gospel'));
        const bHasReadings = b.description && (b.description.includes('Epistle') || b.description.includes('Gospel'));

        if (aHasReadings && !bHasReadings) return -1;
        if (!aHasReadings && bHasReadings) return 1;
        return 0;
      });

      if (localEvent) {
        const localTitle = localEvent.summary;
        const normalizedLocalTitle = normalizeTitle(localTitle);

        const mergedEvents = sortedCalendarEvents.filter((event) => {
          // Keep local reading if titles duplicate
          const normalizedEventTitle = normalizeTitle(event.summary);
          const titleSimilarity = getNormalizedTitleSimilarity(normalizedLocalTitle, normalizedEventTitle);
          if (titleSimilarity >= TITLE_MATCH_THRESHOLD) {
            return false;
          }

          // Also remove exact duplicate body if title differs slightly
          return !(event.summary === localEvent.summary && event.description === localEvent.description);
        });

        if (loadId === activeLoadId) {
          readings.value = [localEvent, ...mergedEvents];
        }
      } else {
        if (loadId === activeLoadId) {
          readings.value = sortedCalendarEvents;
        }
      }
    } catch (e) {
      if (loadId === activeLoadId) {
        error.value = e.message || 'Failed to load readings';
      }
    } finally {
      if (loadId === activeLoadId) {
        loading.value = false;
      }
    }
  };

  const previousDay = () => {
    const newDate = new Date(currentDate.value);
    newDate.setDate(newDate.getDate() - 1);
    currentDate.value = newDate;
  };

  const nextDay = () => {
    const newDate = new Date(currentDate.value);
    newDate.setDate(newDate.getDate() + 1);
    currentDate.value = newDate;
  };

  const goToToday = () => {
    currentDate.value = new Date();
  };

  const goToComingSunday = () => {
    const d = new Date(); // Start from today
    const day = d.getDay();
    // If today is Sunday (0), we want today.
    // If today is Monday (1) to Saturday (6), we want the next Sunday.
    const diff = d.getDate() + (day === 0 ? 0 : (7 - day));
    currentDate.value = new Date(d.setDate(diff));
  };

  // Watch for date changes to refetch data and update hash
  watch(currentDate, (newDate) => {
    const dateString = toDateString(newDate);
    
    if (window.location.hash.substring(1) !== dateString) {
      window.location.hash = dateString;
    }
    loadReadings();
  }, { immediate: true });

  const handleHashChange = () => {
    const dateFromHash = parseDateFromHash(window.location.hash.substring(1));
    if (dateFromHash && dateFromHash.getTime() !== currentDate.value.getTime()) {
      currentDate.value = dateFromHash;
    }
  };

  onMounted(() => {
    window.addEventListener('hashchange', handleHashChange);
  });

  onUnmounted(() => {
    window.removeEventListener('hashchange', handleHashChange);
  });

  return {
    readings,
    loading,
    error,
    currentDate,
    previousDay,
    nextDay,
    goToToday,
    goToComingSunday
  };
}
