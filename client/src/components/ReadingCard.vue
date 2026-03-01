<script setup>
import { computed, ref } from 'vue';
import { fetchScriptureText } from '../services/bibleService';
import { parseReadingDescription } from '../utils/readingParser';

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  link: {
    type: String,
    default: ''
  },
  start: {
    type: Object,
    default: null
  },
  end: {
    type: Object,
    default: null
  },
  fasting: {
    type: String,
    default: null
  },
  usaHoliday: {
    type: String,
    default: null
  },
  canadaHoliday: {
    type: String,
    default: null
  },
  isHolyDayOfObligation: {
    type: Boolean,
    default: false
  }
});

const dateDisplay = computed(() => {
  if (!props.start) return '';

  const getDto = (dt) => dt.dateTime ? new Date(dt.dateTime) : new Date(dt.date + 'T00:00:00');
  const isAllDay = (dt) => !!dt.date;

  const startDate = getDto(props.start);

  const options = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' };
  const strStart = startDate.toLocaleDateString(undefined, options);

  if (!props.end) return strStart;

  const endDate = getDto(props.end);

  // Google Calendar all-day events have an exclusive end date (starts next day at 00:00)
  // We subtract 1 second to pull it back to the actual visual end day for comparison
  if (isAllDay(props.end)) {
    endDate.setSeconds(endDate.getSeconds() - 1);
  }

  // If it's the same day, just return that day
  if (startDate.toDateString() === endDate.toDateString()) {
    return strStart;
  }

  // It's a multi-day event
  const strEnd = endDate.toLocaleDateString(undefined, options);
  return `${strStart} – ${strEnd}`;
});

const parsed = computed(() => {
  return parseReadingDescription(props.description);
});

const hasParsedData = computed(() => {
  return parsed.value.epistle || parsed.value.gospel;
});

const isDevelopment = import.meta.env.DEV;

// --- New Logic for Fetching Text ---
const epistleText = ref(null);
const gospelText = ref(null);
const loadingEpistle = ref(false);
const loadingGospel = ref(false);

const toggleEpistle = async () => {
  if (epistleText.value) {
    epistleText.value = null; // Collapse
    return;
  }
  if (!parsed.value?.epistle) return;

  loadingEpistle.value = true;
  epistleText.value = await fetchScriptureText(parsed.value.epistle);
  loadingEpistle.value = false;
};

const toggleGospel = async () => {
  if (gospelText.value) {
    gospelText.value = null; // Collapse
    return;
  }
  if (!parsed.value?.gospel) return;

  loadingGospel.value = true;
  gospelText.value = await fetchScriptureText(parsed.value.gospel);
  loadingGospel.value = false;
};
</script>

<template>
  <div
    class="bg-white dark:bg-stone-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4 border-red-800 dark:border-red-600 relative">

    <!-- Holy Day Banner -->
    <div v-if="isHolyDayOfObligation"
      class="absolute top-0 right-0 bg-amber-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg shadow-sm z-10 flex items-center gap-1">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
        <path fill-rule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-11.25a.75.75 0 00-1.5 0v2.5h-2.5a.75.75 0 000 1.5h2.5v2.5a.75.75 0 001.5 0v-2.5h2.5a.75.75 0 000-1.5h-2.5v-2.5z"
          clip-rule="evenodd" />
      </svg>
      HOLY DAY OF OBLIGATION
    </div>

    <div v-if="dateDisplay"
      class="text-sm font-semibold text-stone-500 dark:text-stone-400 mb-2 uppercase tracking-wide flex items-center gap-2 flex-wrap">
      {{ dateDisplay }}

      <!-- Holidays Chips -->
      <span v-if="usaHoliday"
        :title="`USA Holiday: ${usaHoliday}`"
        aria-label="USA Holiday"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
        🇺🇸 {{ usaHoliday }}
      </span>
      <span v-if="canadaHoliday"
        :title="`Canadian Holiday: ${canadaHoliday}`"
        aria-label="Canadian Holiday"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
        🇨🇦 {{ canadaHoliday }}
      </span>
    </div>
    <h2
      class="text-2xl font-serif font-bold text-stone-900 dark:text-stone-100 mb-6 border-b border-stone-200 dark:border-stone-700 pb-2">
      {{ title }}
    </h2>

    <!-- Structured Content -->
    <div v-if="hasParsedData" class="space-y-6">

      <!-- Liturgical Info -->
      <div class="bg-stone-50 dark:bg-stone-900/50 p-4 rounded-lg border border-stone-100 dark:border-stone-700">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-if="parsed.tone" class="flex flex-col">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">Tone {{
                parsed.tone }}</span>
              <div class="group relative flex items-center">
                <span
                  class="cursor-help text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 text-xs border border-stone-300 rounded-full w-4 h-4 flex items-center justify-center">?</span>
                <div
                  class="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-stone-800 text-white text-xs rounded shadow-lg z-10 text-center">
                  The musical mode (1-8) used for the Resurrectional hymns this week.
                  <div
                    class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-800">
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="parsed.matinsGospel" class="flex flex-col">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">Matins Gospel
                {{ parsed.matinsGospel }}</span>
              <div class="group relative flex items-center">
                <span
                  class="cursor-help text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 text-xs border border-stone-300 rounded-full w-4 h-4 flex items-center justify-center">?</span>
                <div
                  class="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2 bg-stone-800 text-white text-xs rounded shadow-lg z-10 text-center">
                  The reading for the morning service (Orthros) from the cycle of 11 Resurrectional Gospels.
                  <div
                    class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-stone-800">
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Fasting Info -->
        <div v-if="fasting" class="mt-3 pt-3 border-t border-stone-200 dark:border-stone-700 flex items-start gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"
            class="w-4 h-4 text-stone-400 mt-0.5 flex-shrink-0">
            <path
              d="M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03C11.34 12.84 13 11.12 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.76 0-5 2.24-5 4z" />
          </svg>
          <div>
            <div class="flex items-center gap-2 mb-0.5">
              <span class="text-xs font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">Fasting</span>
              <div class="group relative flex items-center">
                <span class="cursor-help text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 text-xs border border-stone-300 rounded-full w-4 h-4 flex items-center justify-center">?</span>
                <div class="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-72 p-4 bg-stone-900 border border-stone-700 text-white text-xs rounded-xl shadow-2xl z-50 pointer-events-none">
  
                  <p class="mb-3 font-bold text-amber-400 tracking-wide uppercase text-[10px] flex items-center gap-2">
                    <span class="w-1 h-1 bg-amber-400 rounded-full"></span>
                    Fasting Guidelines
                  </p>

                  <div class="space-y-4">
                    <div>
                      <p class="font-bold text-stone-100 mb-1">Strict Fasting & Abstinence</p>
                      <p class="text-stone-400 leading-relaxed">it is traditional to fast until evening on weekdays, and to abstain from meat, fish, eggs, dairy products, and foods cooked with oil, as well as from alcohol and sexual relations.</p>
                    </div>

                    <div class="pt-2 border-t border-stone-800">
                      <p class="font-bold text-stone-100 mb-1">Common Abstinence</p>
                      <p class="text-stone-400 leading-relaxed">Abstention from meat. Dairy and oil are usually permitted.</p>
                    </div>

                    <div class="pt-2 border-t border-stone-800">
                      <div class="flex items-center justify-between">
                        <p class="font-bold text-emerald-400">Dispensation (Hârți)</p>
                        <span class="bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded text-[9px]">FAST-FREE</span>
                      </div>
                      <p class="text-stone-400 leading-relaxed mt-1">Normal rules are relaxed; all foods are permitted.</p>
                    </div>
                  </div>

                  <div class="absolute top-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-t-stone-900"></div>
                  <div class="absolute top-full left-1/2 -translate-x-1/2 border-[7px] border-transparent border-t-stone-700 -z-10"></div>
                </div>
              </div>
            </div>
            <span class="text-sm text-stone-700 dark:text-stone-300 italic">{{ fasting }}</span>
          </div>
        </div>
      </div>

      <!-- Scripture Readings -->
      <div class="space-y-4">
        <div v-if="parsed.epistle" class="relative pl-4 border-l-4 border-amber-500">
          <h3 class="text-sm font-bold text-amber-700 dark:text-amber-500 uppercase tracking-wide mb-1">Epistle</h3>
          <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ parsed.epistle }}</p>

          <!-- Toggle Button -->
          <button @click="toggleEpistle"
            class="mt-2 text-xs font-medium text-stone-500 hover:text-amber-600 underline decoration-dotted underline-offset-4">
            {{ epistleText ? 'Hide Text' : 'Read Passage' }}
          </button>

          <!-- Loading State -->
          <div v-if="loadingEpistle" class="mt-2 text-sm text-stone-400 animate-pulse">Loading scripture...</div>

          <!-- The Actual Text -->
          <div v-if="epistleText"
            class="mt-3 p-4 bg-amber-50 dark:bg-stone-900/50 rounded text-stone-700 dark:text-stone-300 text-sm leading-relaxed border border-amber-100 dark:border-stone-700">
            <div v-html="epistleText"></div>
            <p
              class="mt-3 pt-2 border-t border-amber-200/50 dark:border-stone-700 text-[10px] text-stone-400 text-right uppercase tracking-wider">
              Douay-Rheims 1899 American Edition</p>
          </div>
        </div>

        <div v-if="parsed.gospel" class="relative pl-4 border-l-4 border-red-600">
          <h3 class="text-sm font-bold text-red-700 dark:text-red-500 uppercase tracking-wide mb-1">Gospel</h3>
          <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ parsed.gospel }}</p>

          <!-- Toggle Button -->
          <button @click="toggleGospel"
            class="mt-2 text-xs font-medium text-stone-500 hover:text-red-700 underline decoration-dotted underline-offset-4">
            {{ gospelText ? 'Hide Text' : 'Read Passage' }}
          </button>

          <!-- Loading State -->
          <div v-if="loadingGospel" class="mt-2 text-sm text-stone-400 animate-pulse">Loading scripture...</div>

          <!-- The Actual Text -->
          <div v-if="gospelText"
            class="mt-3 p-4 bg-red-50 dark:bg-stone-900/50 rounded text-stone-700 dark:text-stone-300 text-sm leading-relaxed border border-red-100 dark:border-stone-700">
            <div v-html="gospelText"></div>
            <p
              class="mt-3 pt-2 border-t border-red-200/50 dark:border-stone-700 text-[10px] text-stone-400 text-right uppercase tracking-wider">
              Douay-Rheims 1899 American Edition</p>
          </div>
        </div>
      </div>

      <!-- Additional Notes -->
      <div v-if="parsed.notes" class="mt-6 pt-4 border-t border-stone-200 dark:border-stone-700">
        <h4 class="text-sm font-bold text-stone-500 dark:text-stone-400 uppercase mb-2">Rubrics & Notes</h4>
        <p class="text-stone-600 dark:text-stone-400 italic text-sm">{{ parsed.notes }}</p>
      </div>
    </div>

    <!-- Fallback for unparsed content -->
    <div v-else class="text-stone-700 dark:text-stone-300 font-serif text-lg leading-relaxed whitespace-pre-wrap"
      v-html="description">
    </div>

    <!-- Footer Link -->
    <div v-if="link" class="mt-6 pt-4 border-t border-stone-100 dark:border-stone-700 flex justify-end">
      <a :href="link" target="_blank" rel="noopener noreferrer"
        class="text-xs font-medium text-stone-400 hover:text-red-700 dark:hover:text-red-400 flex items-center gap-1 transition-colors uppercase tracking-wider">
        View in Calendar
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
          <path fill-rule="evenodd"
            d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z"
            clip-rule="evenodd" />
          <path fill-rule="evenodd"
            d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z"
            clip-rule="evenodd" />
        </svg>
      </a>
    </div>

    <!-- Development Debug: Raw Source Text -->
    <details v-if="isDevelopment && description" class="mt-4 pt-4 border-t border-stone-100 dark:border-stone-700">
      <summary class="text-xs font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider cursor-pointer select-none">
        Raw Text (Dev Only)
      </summary>
      <pre class="mt-3 p-3 rounded bg-stone-50 dark:bg-stone-900/50 border border-stone-200 dark:border-stone-700 text-xs text-stone-700 dark:text-stone-300 whitespace-pre-wrap break-words">{{ description }}</pre>
    </details>
  </div>
</template>
