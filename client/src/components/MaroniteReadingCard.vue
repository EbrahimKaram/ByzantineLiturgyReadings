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

const readingStyle = (type) => {
  if (type === 'gospel') {
    return {
      border: 'border-red-600',
      heading: 'text-red-700 dark:text-red-500',
      hover: 'hover:text-red-700',
      box: 'bg-red-50 dark:bg-stone-900/50 border border-red-100 dark:border-stone-700',
    };
  }
  if (type === 'psalm') {
    return {
      border: 'border-amber-500',
      heading: 'text-amber-700 dark:text-amber-500',
      hover: 'hover:text-amber-600',
      box: 'bg-amber-50 dark:bg-stone-900/50 border border-amber-100 dark:border-stone-700',
    };
  }
  return {
    border: 'border-stone-400',
    heading: 'text-stone-600 dark:text-stone-400',
    hover: 'hover:text-stone-700 dark:hover:text-stone-300',
    box: 'bg-stone-50 dark:bg-stone-900/50 border border-stone-200 dark:border-stone-700',
  };
};

// Format reading text: verse-by-verse (each \n = new verse) displayed as paragraphs
const formatText = (text) => text?.trim().replace(/\n+/g, '\n').split('\n') ?? [];
</script>

<template>
  <div class="bg-white dark:bg-stone-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4 border-red-800 dark:border-red-600 relative">

    <div v-if="dateDisplay" class="text-sm font-semibold text-stone-500 dark:text-stone-400 mb-2 uppercase tracking-wide">
      {{ dateDisplay }}
    </div>

    <h2 class="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100 mb-6 border-b border-stone-200 dark:border-stone-700 pb-2">
      {{ liturgicTitle || 'Maronite Readings' }}
    </h2>

    <div class="space-y-4">
      <div
        v-for="(reading, idx) in readings"
        :key="idx"
        class="relative pl-4 border-l-4"
        :class="readingStyle(reading.type).border"
      >
        <h3
          class="text-sm font-bold uppercase tracking-wide mb-1"
          :class="readingStyle(reading.type).heading"
        >
          {{ label(reading.type) }}
        </h3>
        <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ reading.reference }}</p>
        <span v-if="reading.book" class="block text-xs text-stone-500 dark:text-stone-400">
          {{ reading.book }}
        </span>

        <button
          class="mt-2 text-xs font-medium text-stone-500 underline decoration-dotted underline-offset-4"
          :class="readingStyle(reading.type).hover"
          @click="toggle(idx)"
        >
          {{ expanded[idx] ? 'Hide Text' : 'Read Passage' }}
        </button>

        <div
          v-if="expanded[idx]"
          class="mt-3 p-4 rounded text-stone-700 dark:text-stone-300 text-sm leading-relaxed"
          :class="readingStyle(reading.type).box"
        >
          <p
            v-for="(verse, vi) in formatText(reading.text)"
            :key="vi"
            :class="{ 'mt-2': vi > 0 }"
          >
            {{ verse }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
