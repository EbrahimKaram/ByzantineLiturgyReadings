import { ref, watch } from 'vue';
import { fetchSundayReadings } from '../services/calendarService';

export function useReadings() {
  const readings = ref([]);
  const loading = ref(false);
  const error = ref(null);
  
  // Helper to get the initial Sunday (today or next Sunday)
  const getInitialSunday = () => {
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

  // Watch for date changes to refetch data
  watch(currentDate, () => {
    loadReadings();
  }, { immediate: true });

  return {
    readings,
    loading,
    error,
    currentDate,
    previousSunday,
    nextSunday
  };
}
