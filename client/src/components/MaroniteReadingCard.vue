<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  liturgicTitle: { type: String, default: '' },
  readings: { type: Array, default: () => [] },
  date: { type: Date, default: null },
});

const dateDisplay = computed(() => {
  if (!props.date) return '';
  return new Date(props.date).toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });
});

// Expand/collapse individual readings
const expanded = ref({});
const toggle = (idx) => {
  expanded.value[idx] = !expanded.value[idx];
};

const READING_LABELS = {
  reading: 'Old Testament',
  psalm: 'Epistle',
  gospel: 'Gospel',
};

const label = (type) => READING_LABELS[type] ?? type;

// Format reading text: verse-by-verse (each \n = new verse) displayed as paragraphs
const formatText = (text) => text?.trim().replace(/\n+/g, '\n').split('\n') ?? [];
</script>

<template>
  <div class="bg-white dark:bg-stone-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4 border-amber-700 dark:border-amber-600 relative">

    <div v-if="dateDisplay" class="text-sm font-semibold text-stone-500 dark:text-stone-400 mb-2 uppercase tracking-wide">
      {{ dateDisplay }}
    </div>

    <h2 class="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100 mb-6 border-b border-stone-200 dark:border-stone-700 pb-2">
      {{ liturgicTitle || 'Maronite Readings' }}
    </h2>

    <div class="space-y-4">
      <div v-for="(reading, idx) in readings" :key="idx" class="border border-stone-200 dark:border-stone-700 rounded-lg overflow-hidden">

        <!-- Reading header (always visible) -->
        <button
          class="w-full flex items-center justify-between px-4 py-3 bg-stone-50 dark:bg-stone-900/40 hover:bg-stone-100 dark:hover:bg-stone-700/60 transition-colors text-left"
          @click="toggle(idx)"
        >
          <div>
            <span class="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-500 block mb-0.5">
              {{ label(reading.type) }}
            </span>
            <span class="text-sm font-semibold text-stone-700 dark:text-stone-300">
              {{ reading.reference }}
            </span>
            <span v-if="reading.book" class="text-xs text-stone-500 dark:text-stone-400 block">
              {{ reading.book }}
            </span>
          </div>
          <svg
            class="w-5 h-5 text-stone-400 transition-transform duration-200 flex-shrink-0 ml-4"
            :class="{ 'rotate-180': expanded[idx] }"
            xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
          >
            <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
          </svg>
        </button>

        <!-- Reading text (expandable) -->
        <div v-if="expanded[idx]" class="px-4 py-4">
          <p
            v-for="(verse, vi) in formatText(reading.text)"
            :key="vi"
            class="text-stone-700 dark:text-stone-300 leading-relaxed text-[0.95rem]"
            :class="{ 'mt-2': vi > 0 }"
          >
            {{ verse }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
