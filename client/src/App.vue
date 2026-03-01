<template>
  <div class="min-h-screen bg-stone-100 dark:bg-stone-900 py-12 px-4 sm:px-6 lg:px-8 font-serif">
    <div class="max-w-3xl mx-auto">
      <header class="text-center mb-8">
        <div class="flex justify-center mb-4">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-red-800 dark:text-red-600">
            <!-- Vertical post -->
            <line x1="12" y1="2" x2="12" y2="22"></line>
            <!-- Top bar (Titulus) -->
            <line x1="9" y1="6" x2="15" y2="6"></line>
            <!-- Middle bar (Patibulum) -->
            <line x1="5" y1="10" x2="19" y2="10"></line>
            <!-- Bottom slanted bar (Suppedaneum) -->
            <line x1="8" y1="15" x2="16" y2="18"></line>
          </svg>
        </div>
        <h1 class="text-4xl font-bold text-stone-800 dark:text-stone-100 mb-2 tracking-tight">Romanian Byzantine Liturgy Readings</h1>
        <p class="text-stone-600 dark:text-stone-400 italic">Scripture readings for the Romanian Byzantine Liturgies from the <a href="https://www.stgeorgeoh.org/calendar" target="_blank" rel="noopener noreferrer" class="underline">Saint George Cathedral Calendar.</a>
        
          We are specifically following the readings as outlined by the Romanian <a href="https://romaniancatholic.org/" target="_blank" rel="noopener noreferrer" class="underline">Catholic Diocese Eparchy of St. George in Canton</a>.</p>

      </header>

      <!-- Date Navigation Controls (Sticky) -->
      <div class="sticky top-4 z-30 flex justify-center mb-8">
        <div class="relative">
          <div class="absolute inset-0 bg-white/90 dark:bg-stone-800/90 backdrop-blur-sm rounded-lg shadow-lg border border-stone-200 dark:border-stone-700"></div>
          <div class="relative flex items-center justify-center space-x-2 sm:space-x-4 p-2 sm:p-4">
          <button 
            @click="previousDay"
            class="p-1 sm:p-2 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            aria-label="Previous Day"
          >
            ←
          </button>
          
          <span class="text-sm sm:text-lg font-semibold text-stone-800 dark:text-stone-200 min-w-[110px] sm:min-w-[140px] text-center">
            {{ formatDate(currentDate) }}
          </span>
          
          <button 
            @click="nextDay"
            class="p-1 sm:p-2 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            aria-label="Next Day"
          >
            →
          </button>
          
          <div class="h-6 w-px bg-stone-300 dark:bg-stone-600 mx-1 sm:mx-2"></div>

          <button 
            @click="goToToday"
            class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            title="Go to Today"
          >
            Today
          </button>

          <button 
            @click="goToComingSunday"
            class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            title="Go to Next Sunday"
          >
            Coming Sunday
          </button>
          
          <div class="relative">
            <button 
              @click="toggleDatePicker"
              class="p-1.5 rounded-md hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
              :class="{ 'bg-stone-100 dark:bg-stone-700 text-red-800 dark:text-red-400': showDatePicker }"
              title="Select Date"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
            </button>
            
            <div v-if="showDatePicker" class="fixed inset-0 z-40" @click="showDatePicker = false"></div>
            
            <div v-if="showDatePicker" class="absolute top-full right-0 sm:left-1/2 sm:-translate-x-1/2 sm:right-auto mt-2 z-50">
              <DatePicker 
                :modelValue="currentDate" 
                @update:modelValue="onDateSelect"
                @close="showDatePicker = false"
              />
            </div>
          </div>

          </div>
        </div>
      </div>

      <main>
        <div v-if="loading" class="flex flex-col items-center justify-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-800 dark:border-red-600"></div>
          <p class="mt-4 text-stone-600 dark:text-stone-400">Loading Calendar events...</p>
        </div>

        <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8 rounded-r shadow-sm">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Error loading Calendar events</h3>
              <div class="mt-2 text-sm text-red-700 dark:text-red-300">
                <p>{{ error }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="space-y-8">
          <div class="text-center">
             <a :href="romanCatholicLink" target="_blank" rel="noopener noreferrer" class="text-sm text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-300 transition-colors underline decoration-stone-300 dark:decoration-stone-600">
              Roman Catholic Readings for this day
            </a>
          </div>

          <ReadingCard
            v-for="event in readings"
            :key="event.id"
            :title="event.summary"
            :description="event.description"
            :link="event.htmlLink"
            :start="event.start"
            :end="event.end"
            :fasting="event.fasting"
            :usa-holiday="event.usaHoliday"
            :canada-holiday="event.canadaHoliday"
            :is-holy-day-of-obligation="event.isHolyDayOfObligation"
          />
          
          <div v-if="!loading && readings.length === 0" class="text-center py-12 bg-white dark:bg-stone-800 rounded-lg shadow p-6">
            <p class="text-stone-500 dark:text-stone-400 text-lg">No readings found for this day.</p>
          </div>
        </div>
      </main>
      
      <footer class="mt-16 text-center text-stone-500 dark:text-stone-500 text-sm space-y-4">
        <div class="space-y-1">
          <p>Data provided by Google Calendar</p>
          <p class="text-xs opacity-75">Scripture texts: Douay-Rheims 1899 American Edition</p>
        </div>

        <div class="flex flex-wrap justify-center items-center gap-4 pt-4 border-t border-stone-200 dark:border-stone-800 w-full mx-auto">
          <a href="https://github.com/EbrahimKaram/ByzantineLiturgyReadings" target="_blank" rel="noopener noreferrer" class="text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors" aria-label="GitHub Repository">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
          </a>
          <a href="https://github.com/EbrahimKaram/ByzantineLiturgyReadings/issues/new" target="_blank" rel="noopener noreferrer" class="flex items-center gap-2 text-stone-400 hover:text-red-600 dark:hover:text-red-500 transition-colors font-medium">
             <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span>Report Issue</span>
          </a>
          <a href="https://www.buymeacoffee.com/bobKaram" target="_blank" rel="noopener noreferrer" class="flex items-center gap-2 text-stone-400 hover:text-amber-600 dark:hover:text-amber-500 transition-colors font-medium">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>
            <span>Buy me a coffee</span>
          </a>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useReadings } from './composables/useReadings';
import ReadingCard from './components/ReadingCard.vue';
import DatePicker from './components/DatePicker.vue';

const { readings, loading, error, currentDate, previousDay, nextDay, goToToday, goToComingSunday } = useReadings();
const showDatePicker = ref(false);

const toggleDatePicker = () => {
  showDatePicker.value = !showDatePicker.value;
};

const onDateSelect = (selectedDate) => {
  currentDate.value = selectedDate;
};

const formatDate = (date) => {
  if (!date) return '';
  return date.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};

const romanCatholicLink = computed(() => {
  if (!currentDate.value) return '#';
  const d = new Date(currentDate.value);
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const year = String(d.getFullYear()).slice(-2);
  
  return `https://bible.usccb.org/bible/readings/${month}${day}${year}.cfm`;
});
</script>
