import { ref, watch, onMounted, onUnmounted } from 'vue';
import { fetchSundayReadings } from '../services/calendarService';

export function useReadings() {
  const readings = ref([]);
  const loading = ref(false);
  const error = ref(null);
  
  // Helper to get the initial Sunday (today or next Sunday)
  const getInitialSunday = () => {
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

    const d = new Date();
    const day = d.getDay();
    // If today is Sunday (0), we want today.
    // If today is Monday (1) to Saturday (6), we want the next Sunday.
    const diff = d.getDate() + (day === 0 ? 0 : (7 - day));
    return new Date(d.setDate(diff));
  };

  const currentDate = ref(getInitialSunday());

  const loadReadings = async () => {
    loading.value = true;
    error.value = null;
    try {
      const events = await fetchSundayReadings(currentDate.value);
      
      // Sort events: Prioritize events with "Epistle" or "Gospel" in the description
      readings.value = events.sort((a, b) => {
        const aHasReadings = a.description && (a.description.includes('Epistle') || a.description.includes('Gospel'));
        const bHasReadings = b.description && (b.description.includes('Epistle') || b.description.includes('Gospel'));

        if (aHasReadings && !bHasReadings) return -1;
        if (!aHasReadings && bHasReadings) return 1;
        return 0;
      });
    } catch (e) {
      error.value = e.message || 'Failed to load readings';
    } finally {
      loading.value = false;
    }
  };

  const previousSunday = () => {
    const newDate = new Date(currentDate.value);
    newDate.setDate(newDate.getDate() - 7);
    currentDate.value = newDate;
  };

  const nextSunday = () => {
    const newDate = new Date(currentDate.value);
    newDate.setDate(newDate.getDate() + 7);
    currentDate.value = newDate;
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
    previousSunday,
    nextSunday
  };
}
