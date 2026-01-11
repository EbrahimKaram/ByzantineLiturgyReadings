<template>
  <div class="bg-white dark:bg-stone-800 rounded-lg shadow-xl border border-stone-200 dark:border-stone-700 p-4 w-72 font-serif select-none">
    <!-- Header -->
    <div class="flex justify-between items-center mb-4">
      <button @click.stop="prevMonth" class="p-1 hover:bg-stone-100 dark:hover:bg-stone-700 rounded-full transition-colors text-stone-600 dark:text-stone-300">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
      </button>
      <span class="font-semibold text-stone-800 dark:text-stone-100 text-lg">
        {{ currentMonthName }} {{ currentYear }}
      </span>
      <button @click.stop="nextMonth" class="p-1 hover:bg-stone-100 dark:hover:bg-stone-700 rounded-full transition-colors text-stone-600 dark:text-stone-300">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
      </button>
    </div>

    <!-- Weekday Headers -->
    <div class="grid grid-cols-7 mb-2 text-center">
      <span v-for="day in weekDays" :key="day" class="text-xs font-bold text-stone-400 dark:text-stone-500 uppercase tracking-wider">
        {{ day }}
      </span>
    </div>

    <!-- Calendar Grid -->
    <div class="grid grid-cols-7 gap-1 text-center">
      <div v-for="blank in firstDayOfMonth" :key="'blank-' + blank" class="p-1"></div>
      <button
        v-for="date in daysInMonth"
        :key="date"
        @click.stop="selectDate(date)"
        :class="[
          'p-1 text-sm rounded-full w-8 h-8 flex items-center justify-center transition-all duration-200',
          isSelected(date) 
            ? 'bg-red-800 text-white dark:bg-red-700 shadow-md' 
            : 'text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700',
          isToday(date) && !isSelected(date) ? 'ring-1 ring-red-800 text-red-800 dark:ring-red-500 dark:text-red-400 font-semibold' : '',
          isSunday(date) && !isSelected(date) ? 'text-red-800/80 dark:text-red-400/80 font-medium' : ''
        ]"
      >
        {{ date }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  modelValue: Date
});

const emit = defineEmits(['update:modelValue', 'close']);

// Internal state for the view (which month we are looking at)
const viewDate = ref(props.modelValue ? new Date(props.modelValue) : new Date());

const weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const currentMonthName = computed(() => months[viewDate.value.getMonth()]);
const currentYear = computed(() => viewDate.value.getFullYear());

const daysInMonth = computed(() => {
  const d = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() + 1, 0);
  return d.getDate();
});

const firstDayOfMonth = computed(() => {
  // getDay returns 0 for Sunday.
  const d = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth(), 1);
  return d.getDay();
});

const prevMonth = () => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() - 1, 1);
};

const nextMonth = () => {
  viewDate.value = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth() + 1, 1);
};

const selectDate = (day) => {
  const newDate = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth(), day);
  emit('update:modelValue', newDate);
  emit('close');
};

const isSelected = (day) => {
  if (!props.modelValue) return false;
  const d = new Date(props.modelValue);
  return d.getDate() === day && 
         d.getMonth() === viewDate.value.getMonth() && 
         d.getFullYear() === viewDate.value.getFullYear();
};

const isToday = (day) => {
  const today = new Date();
  return today.getDate() === day && 
         today.getMonth() === viewDate.value.getMonth() && 
         today.getFullYear() === viewDate.value.getFullYear();
};

const isSunday = (day) => {
  const d = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth(), day);
  return d.getDay() === 0;
};
</script>
