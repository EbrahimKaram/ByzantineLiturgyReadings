<script setup>
import { computed, ref } from 'vue';
import { fetchScriptureText } from '../services/bibleService';

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
  if (!props.description) return {};

  // Simple HTML strip for parsing text content
  const text = props.description.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  // Regex patterns
  const toneMatch = text.match(/Tone\s+(\d+)/i);

  // Matins parsing
  // 1. "Res. Gospel <number>"
  const matinsResMatch = text.match(/Res\.?\s*Gospel\s+(\d+)/i);
  // 2. "Matins Gospel: <text>"
  // Using simplified capture that respects sentence boundaries but allows abbreviations (e.g. "Mt.")
  const matinsTextMatch = text.match(/Matins\s+Gospel:?\s*(.*?)(?=\s+Divine Liturgy|\s*Following|\.\s*[A-Z]|\.\s*$|$)/i);
  
  const matinsGospel = matinsResMatch ? matinsResMatch[1] : (matinsTextMatch ? matinsTextMatch[1].trim() : null);

  // Remove Matins part from text to prevent the generic "Gospel" regex from matching it
  let readingText = text;
  if (matinsResMatch) readingText = readingText.replace(matinsResMatch[0], '');
  if (matinsTextMatch) readingText = readingText.replace(matinsTextMatch[0], '');

  // Divine Liturgy Parsing
  let epistle = null;
  let gospel = null;

  // Check for combined "Divine Liturgy: <Epistle>; <Gospel>" pattern first
  // Relaxed regex to allow dots in abbreviations (e.g. "Mt.") but stop at logical sentence ends
  const divineLiturgyMatch = readingText.match(/Divine Liturgy:?\s*([^;]+);\s*(.*?)(?=\s*Following|\.\s*[A-Z]|\.\s*$|$)/i);

  if (divineLiturgyMatch) {
    epistle = divineLiturgyMatch[1].trim();
    gospel = divineLiturgyMatch[2].trim();
  } else {
    // Fallback to standard "Epistle:" and "Gospel:" keywords
    const epistleMatch = readingText.match(/(?:^|[\s,;.])Epistle[:\s]+\s*(.*?)(?=;?\s*Gospel|$)/i);
    const gospelMatch = readingText.match(/(?:^|[\s,;.])Gospel[:\s]+\s*(.*?)(?=;?\s*Following|$)/i);

    if (epistleMatch) epistle = epistleMatch[1].trim().replace(/^[;:,.\s]+|[;:,.\s]+$/g, '');
    if (gospelMatch) gospel = gospelMatch[1].trim().replace(/^[;:,.\s]+|[;:,.\s]+$/g, '');
  }

  // Notes extraction
  // 1. "Following..." section at the end
  const followingMatch = text.match(/(Following.*)/i);
  
  // 2. Introductory notes (anything before the first reading marker)
  // Markers: Tone, Res. Gospel, Matins Gospel, Divine Liturgy, Epistle, Gospel
  // We find the index of the first marker
  const markersRegex = /Tone\s+\d+|Res\.?\s*Gospel|Matins\s+Gospel|Divine\s+Liturgy|Epistle:|Gospel:/i;
  const firstMarkerMatch = text.match(markersRegex);
  
  let introNote = null;
  if (firstMarkerMatch && firstMarkerMatch.index > 0) {
    introNote = text.substring(0, firstMarkerMatch.index).trim();
    // Clean up trailing punctuation if any, mostly keeping it simple
  } else if (!firstMarkerMatch) {
    // If no readings found, maybe the whole text is a note? 
    // But we usually rely on hasParsedData to show anything.
    // Let's assume if no markers, we don't treat it as intro note here to avoid duplication if the logic fails.
  }

  const combinedNotes = [introNote, followingMatch ? followingMatch[1].trim() : null]
    .filter(Boolean)
    .join('\n\n');

  return {
    tone: toneMatch ? toneMatch[1] : null,
    matinsGospel,
    epistle,
    gospel,
    notes: combinedNotes || null
  };
});

const hasParsedData = computed(() => {
  return parsed.value.epistle || parsed.value.gospel;
});

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
  <div class="bg-white dark:bg-stone-800 rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 p-6 border-t-4 border-red-800 dark:border-red-600">
    <div v-if="dateDisplay" class="text-sm font-semibold text-stone-500 dark:text-stone-400 mb-2 uppercase tracking-wide">
      {{ dateDisplay }}
    </div>
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
          
          <!-- Toggle Button -->
          <button 
            @click="toggleEpistle" 
            class="mt-2 text-xs font-medium text-stone-500 hover:text-amber-600 underline decoration-dotted underline-offset-4"
          >
            {{ epistleText ? 'Hide Text' : 'Read Passage' }}
          </button>

          <!-- Loading State -->
          <div v-if="loadingEpistle" class="mt-2 text-sm text-stone-400 animate-pulse">Loading scripture...</div>

          <!-- The Actual Text -->
          <div v-if="epistleText" class="mt-3 p-4 bg-amber-50 dark:bg-stone-900/50 rounded text-stone-700 dark:text-stone-300 text-sm leading-relaxed border border-amber-100 dark:border-stone-700">
            <div v-html="epistleText"></div>
            <p class="mt-3 pt-2 border-t border-amber-200/50 dark:border-stone-700 text-[10px] text-stone-400 text-right uppercase tracking-wider">Douay-Rheims 1899 American Edition</p>
          </div>
        </div>

        <div v-if="parsed.gospel" class="relative pl-4 border-l-4 border-red-600">
          <h3 class="text-sm font-bold text-red-700 dark:text-red-500 uppercase tracking-wide mb-1">Gospel</h3>
          <p class="text-lg font-serif text-stone-800 dark:text-stone-200">{{ parsed.gospel }}</p>
          
          <!-- Toggle Button -->
          <button 
            @click="toggleGospel" 
            class="mt-2 text-xs font-medium text-stone-500 hover:text-red-700 underline decoration-dotted underline-offset-4"
          >
            {{ gospelText ? 'Hide Text' : 'Read Passage' }}
          </button>

          <!-- Loading State -->
          <div v-if="loadingGospel" class="mt-2 text-sm text-stone-400 animate-pulse">Loading scripture...</div>

          <!-- The Actual Text -->
          <div v-if="gospelText" class="mt-3 p-4 bg-red-50 dark:bg-stone-900/50 rounded text-stone-700 dark:text-stone-300 text-sm leading-relaxed border border-red-100 dark:border-stone-700">
            <div v-html="gospelText"></div>
            <p class="mt-3 pt-2 border-t border-red-200/50 dark:border-stone-700 text-[10px] text-stone-400 text-right uppercase tracking-wider">Douay-Rheims 1899 American Edition</p>
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
    <div v-else class="text-stone-700 dark:text-stone-300 font-serif text-lg leading-relaxed whitespace-pre-wrap" v-html="description">
    </div>

    <!-- Footer Link -->
    <div v-if="link" class="mt-6 pt-4 border-t border-stone-100 dark:border-stone-700 flex justify-end">
      <a 
        :href="link" 
        target="_blank" 
        rel="noopener noreferrer" 
        class="text-xs font-medium text-stone-400 hover:text-red-700 dark:hover:text-red-400 flex items-center gap-1 transition-colors uppercase tracking-wider"
      >
        View in Calendar
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3 h-3">
          <path fill-rule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clip-rule="evenodd" />
          <path fill-rule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clip-rule="evenodd" />
        </svg>
      </a>
    </div>
  </div>
</template>
