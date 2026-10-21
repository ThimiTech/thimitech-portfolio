<script setup lang="ts">
import { dismissToast, toasts } from "./toast";

const TONE = {
  success: { bar: "bg-moss", icon: "M20 6 9 17l-5-5", label: "Success" },
  error: { bar: "bg-rust", icon: "M12 8v5M12 16.5v.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z", label: "Error" },
  info: { bar: "bg-sky", icon: "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z", label: "Notice" },
} as const;
</script>

<template>
  <!-- Polite live region: announces without stealing focus. -->
  <div
    class="pointer-events-none fixed inset-x-0 bottom-0 z-[10001] flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-0 sm:items-end"
    role="status"
    aria-live="polite"
  >
    <TransitionGroup
      enter-from-class="opacity-0 translate-y-2"
      leave-to-class="opacity-0"
      enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
      leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto flex w-full max-w-sm items-start gap-3 overflow-hidden rounded-lg border border-ink/10 bg-sheet py-3 pr-2 pl-0 text-sm text-ink shadow-lg"
      >
        <span class="w-1 self-stretch" :class="TONE[t.tone].bar" aria-hidden="true" />
        <svg viewBox="0 0 24 24" class="mt-0.5 h-4 w-4 shrink-0" :class="t.tone === 'error' ? 'text-rust' : t.tone === 'success' ? 'text-moss' : 'text-sky'" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path :d="TONE[t.tone].icon" />
        </svg>
        <p class="min-w-0 flex-1 leading-snug"><span class="sr-only">{{ TONE[t.tone].label }}: </span>{{ t.message }}</p>
        <button type="button" class="rounded p-1 text-ink/45 hover:bg-panel hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40" aria-label="Dismiss notification" @click="dismissToast(t.id)">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
