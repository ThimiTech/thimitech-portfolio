<script setup lang="ts">
import { computed } from "vue";
import { fmtMonth, shiftMonth, thisMonth } from "./attendance";

const month = defineModel<string>({ required: true });
const atNow = computed(() => month.value >= thisMonth());
</script>

<template>
  <div class="inline-flex items-center gap-1 rounded-full border border-ink/15 bg-sheet p-0.5" role="group" aria-label="Choose month">
    <button type="button" class="rounded-full p-1.5 text-ink/60 hover:bg-panel hover:text-ink focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none" aria-label="Previous month" @click="month = shiftMonth(month, -1)">
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
    </button>
    <span class="min-w-[9.5rem] text-center font-display text-[15px]" aria-live="polite">{{ fmtMonth(month) }}</span>
    <button type="button" class="rounded-full p-1.5 text-ink/60 hover:bg-panel hover:text-ink focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none disabled:opacity-30" aria-label="Next month" :disabled="atNow" @click="month = shiftMonth(month, 1)">
      <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
    </button>
  </div>
</template>
