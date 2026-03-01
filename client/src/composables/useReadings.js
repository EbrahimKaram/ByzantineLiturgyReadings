import { ref, watch, onMounted, onUnmounted } from 'vue';
import { fetchSundayReadings } from '../services/calendarService';
import { getLocalReading } from '../services/localReadingsService';

export function useReadings() {
  const readings = ref([]);
  const loading = ref(false);
  const error = ref(null);
  let activeLoadId = 0;

  // Helper to get the initial date (today)
  const getInitialDate = () => {
    // Check hash first
    const hash = window.location.hash.substring(1);
    if (hash) {
      const parts = hash.split('-');
      if (parts.length === 3) {
        const year = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10) - 1;
        const day = parseInt(parts[2], 10);
        const dateFromHash = new Date(year, month, day);
        if (!isNaN(dateFromHash.getTime())) {
          return dateFromHash;
        }
      }
    }

    return new Date();
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
        if (localReading.Notes) descriptionParts.push(`${localReading.Notes}`);
        
        /* 
        if (localReading['Holy Day of Obligation']) {
           descriptionParts.unshift('✝ Holy Day of Obligation');
        } 
        */

        // Calculate exclusive end date for compatibility with Google Calendar logic in ReadingCard
        // (Google Calendar uses exclusive end dates for all-day events)
        const startDateStr = currentDate.value.getFullYear() + '-' + 
            String(currentDate.value.getMonth() + 1).padStart(2, '0') + '-' + 
            String(currentDate.value.getDate()).padStart(2, '0');
            
        const nextDay = new Date(currentDate.value);
        nextDay.setDate(nextDay.getDate() + 1);
        const endDateStr = nextDay.getFullYear() + '-' + 
            String(nextDay.getMonth() + 1).padStart(2, '0') + '-' + 
            String(nextDay.getDate()).padStart(2, '0');

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
      const sortedCalendarEvents = events.sort((a, b) => {
        const aHasReadings = a.description && (a.description.includes('Epistle') || a.description.includes('Gospel'));
        const bHasReadings = b.description && (b.description.includes('Epistle') || b.description.includes('Gospel'));

        if (aHasReadings && !bHasReadings) return -1;
        if (!aHasReadings && bHasReadings) return 1;
        return 0;
      });

      if (localEvent) {
        const normalizeTitle = (title) => String(title || '').trim().toLowerCase();
        const localTitle = normalizeTitle(localEvent.summary);

        const mergedEvents = sortedCalendarEvents.filter((event) => {
          // Keep local reading if titles duplicate
          if (localTitle && normalizeTitle(event.summary) === localTitle) {
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
    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    const dateString = `${year}-${month}-${day}`;
    
    if (window.location.hash.substring(1) !== dateString) {
      window.location.hash = dateString;
    }
    loadReadings();
  }, { immediate: true });

  const handleHashChange = () => {
    const hash = window.location.hash.substring(1);
    if (hash) {
      const parts = hash.split('-');
      if (parts.length === 3) {
        const year = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10) - 1;
        const day = parseInt(parts[2], 10);
        const dateFromHash = new Date(year, month, day);
        
        if (!isNaN(dateFromHash.getTime())) {
          // Compare timestamps to avoid redundant updates
          // Note: currentDate.value might have time components if not careful, 
          // but our logic mostly keeps it clean or we just compare YMD.
          // Let's just set it, the watcher will handle the rest (and check for loops via hash check)
          if (dateFromHash.getTime() !== currentDate.value.getTime()) {
             currentDate.value = dateFromHash;
          }
        }
      }
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
