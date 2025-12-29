<template>
  <div class="bg-white dark:bg-stone-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4 border-red-800 dark:border-red-600">
    <h2 class="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100 mb-6 border-b border-stone-200 dark:border-stone-700 pb-2">
      {{ title }}
    </h2>

    <!-- Structured Content -->
    <div v-if="hasParsedData" class="space-y-6">
      
      <!-- Liturgical Info -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-stone-50 dark:bg-stone-900/50 p-4 rounded-lg border border-stone-100 dark:border-stone-700">
        <div v-if="parsed.tone" class="flex flex-col">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">Tone {{ parsed.tone }}</span>
            <div class="group relative flex items-center">
              <span class="cursor-help text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 text-xs border border-stone-300 rounded-full w-4 h-4 flex items-center justify-center">?</span>
              <div class="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-stone-800 text-white text-xs rounded shadow-lg z-10 text-center">
                The musical mode (1-8) used for the Resurrectional hymns this week.
                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-800"></div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="parsed.matinsGospel" class="flex flex-col">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">Matins Gospel {{ parsed.matinsGospel }}</span>
            <div class="group relative flex items-center">
              <span class="cursor-help text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 text-xs border border-stone-300 rounded-full w-4 h-4 flex items-center justify-center">?</span>
              <div class="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2 bg-stone-800 text-white text-xs rounded shadow-lg z-10 text-center">
                The reading for the morning service (Orthros) from the cycle of 11 Resurrectional Gospels.
                <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-800"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Scripture Readings -->
      <div class="space-y-4">
        <div v-if="parsed.epistle" class="relative pl-4 border-l-4 border-amber-500">
          <h3 class="text-sm font-bold text-amber-700 dark:text-amber-500 uppercase tracking-wide mb-1">Epistle</h3>
          <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ parsed.epistle }}</p>
          <p class="text-xs text-stone-500 mt-1">The reading from the Acts or Epistles of the Apostles.</p>
        </div>

        <div v-if="parsed.gospel" class="relative pl-4 border-l-4 border-red-600">
          <h3 class="text-sm font-bold text-red-700 dark:text-red-500 uppercase tracking-wide mb-1">Gospel</h3>
          <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ parsed.gospel }}</p>
          <p class="text-xs text-stone-500 mt-1">The reading from the four Evangelists.</p>
        </div>
      </div>

      <!-- Additional Notes -->
      <div v-if="parsed.notes" class="mt-6 pt-4 border-t border-stone-200 dark:border-stone-700">
        <h4 class="text-sm font-bold text-stone-500 dark:text-stone-400 uppercase mb-2">Rubrics & Notes</h4>
        <p class="text-stone-600 dark:text-stone-400 italic text-sm">{{ parsed.notes }}</p>
      </div>
    </div>

    <!-- Fallback for unparsed content -->
    <div v-else class="text-stone-700 dark:text-stone-300 font-serif text-lg leading-relaxed whitespace-pre-wrap" v-html="description">
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
});

const parsed = computed(() => {
  if (!props.description) return {};

  // Simple HTML strip for parsing text content
  const text = props.description.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  // Regex patterns
  const toneMatch = text.match(/Tone\s+(\d+)/i);
  const matinsMatch = text.match(/Res\.?\s*Gospel\s+(\d+)/i);
  
  // Epistle: Matches "Epistle" followed by content until "Gospel" or end
  const epistleMatch = text.match(/Epistle\s+(.*?)(?=;?\s*Gospel|$)/i);
  
  // Gospel: Matches "Gospel" followed by content until "Following" or end
  const gospelMatch = text.match(/Gospel\s+(.*?)(?=\s*Following|$)/i);

  // Notes: Matches everything after "Following"
  const notesMatch = text.match(/(Following.*)/i);

  return {
    tone: toneMatch ? toneMatch[1] : null,
    matinsGospel: matinsMatch ? matinsMatch[1] : null,
    epistle: epistleMatch ? epistleMatch[1].trim().replace(/;$/, '') : null,
    gospel: gospelMatch ? gospelMatch[1].trim() : null,
    notes: notesMatch ? notesMatch[1].trim() : null
  };
});

const hasParsedData = computed(() => {
  return parsed.value.epistle || parsed.value.gospel;
});
</script>
