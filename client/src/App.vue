<template>
  <div class="min-h-screen bg-stone-100 dark:bg-stone-900 py-12 px-4 sm:px-6 lg:px-8 font-serif">
    <div class="max-w-3xl mx-auto">
      <header class="text-center mb-12">
        <h1 class="text-4xl font-bold text-stone-800 dark:text-stone-100 mb-2 tracking-tight">Byzantine Liturgy Readings</h1>
        <p class="text-stone-600 dark:text-stone-400 italic mb-8">Scripture readings for the Sunday Liturgies from the Saint George Cathedral Calendar </p>

        <!-- Date Navigation Controls -->
        <div class="flex items-center justify-center space-x-4 bg-white dark:bg-stone-800 p-4 rounded-lg shadow-sm inline-flex">
          <button 
            @click="previousSunday"
            class="p-2 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700 text-stone-600 dark:text-stone-300 transition-colors"
            aria-label="Previous Sunday"
          >
            ←
          </button>
          
          <span class="text-lg font-semibold text-stone-800 dark:text-stone-200 min-w-[140px]">
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
      </header>

      <main>
        <div v-if="loading" class="flex flex-col items-center justify-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-800 dark:border-red-600"></div>
          <p class="mt-4 text-stone-600 dark:text-stone-400">Loading readings...</p>
        </div>

        <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-8 rounded-r shadow-sm">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Error loading readings</h3>
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
          />
          
          <div v-if="!loading && readings.length === 0" class="text-center py-12 bg-white dark:bg-stone-800 rounded-lg shadow p-6">
            <p class="text-stone-500 dark:text-stone-400 text-lg">No readings found for this Sunday.</p>
          </div>
        </div>
      </main>
      
      <footer class="mt-16 text-center text-stone-500 dark:text-stone-500 text-sm">
        <p>Data provided by Google Calendar</p>
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
