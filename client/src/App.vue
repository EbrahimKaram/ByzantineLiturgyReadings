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
        <h1 class="text-4xl font-bold text-stone-800 dark:text-stone-100 mb-2 tracking-tight">Byzantine Liturgy Readings</h1>
        <p class="text-stone-600 dark:text-stone-400 italic">Scripture readings for the Sunday Liturgies from the <a href="https://www.stgeorgeoh.org/calendar" target="_blank" rel="noopener noreferrer" class="underline">Saint George Cathedral Calendar</a></p>
      </header>

      <!-- Date Navigation Controls (Sticky) -->
      <div class="sticky top-4 z-30 flex justify-center mb-8">
        <div class="flex items-center justify-center space-x-4 bg-white/90 dark:bg-stone-800/90 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-stone-200 dark:border-stone-700">
          <button 
            @click="previousSunday"
            class="p-2 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            aria-label="Previous Sunday"
          >
            ←
          </button>
          
          <span class="text-lg font-semibold text-stone-800 dark:text-stone-200 min-w-[140px] text-center">
            {{ formatDate(currentDate) }}
          </span>
          
          <button 
            @click="nextSunday"
            class="p-2 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            aria-label="Next Sunday"
          >
            →
          </button>
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
          <ReadingCard
            v-for="event in readings"
            :key="event.id"
            :title="event.summary"
            :description="event.description"
            :link="event.htmlLink"
          />
          
          <div v-if="!loading && readings.length === 0" class="text-center py-12 bg-white dark:bg-stone-800 rounded-lg shadow p-6">
            <p class="text-stone-500 dark:text-stone-400 text-lg">No readings found for this Sunday.</p>
          </div>
        </div>
      </main>
      
      <footer class="mt-16 text-center text-stone-500 dark:text-stone-500 text-sm space-y-4">
        <div class="space-y-1">
          <p>Data provided by Google Calendar</p>
          <p class="text-xs opacity-75">Scripture texts: Douay-Rheims 1899 American Edition</p>
        </div>

        <div class="flex justify-center items-center gap-4 pt-4 border-t border-stone-200 dark:border-stone-800 max-w-xs mx-auto">
          <a href="https://github.com/EbrahimKaram/ByzantineLiturgyReadings" target="_blank" rel="noopener noreferrer" class="text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors" aria-label="GitHub Repository">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
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
import { useReadings } from './composables/useReadings';
import ReadingCard from './components/ReadingCard.vue';

const { readings, loading, error, currentDate, previousSunday, nextSunday } = useReadings();

const formatDate = (date) => {
  if (!date) return '';
  return new Date(date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};
</script>
