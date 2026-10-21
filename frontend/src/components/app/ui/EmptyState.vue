<script setup lang="ts">
defineProps<{ title: string; hint?: string }>();
</script>

<template>
  <div class="flex flex-col items-center justify-center px-6 py-12 text-center">
    <svg viewBox="0 0 120 80" class="h-16 w-24 text-contour/60" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">
      <path d="M60 10c22 0 44 10 46 28s-14 32-40 34-50-8-52-26S38 10 60 10z" />
      <path d="M60 22c14 0 28 6 29 17s-9 21-26 22-31-5-32-16 15-23 29-23z" />
      <path d="M61 33c6 0 12 3 12 7s-4 9-11 9-13-2-13-7 6-9 12-9z" />
      <circle cx="61" cy="40" r="1.6" fill="var(--color-flag)" stroke="none" />
    </svg>
    <p class="mt-4 font-display text-lg text-ink">{{ title }}</p>
    <p v-if="hint" class="mt-1 max-w-sm text-sm text-ink/55">{{ hint }}</p>
    <div v-if="$slots.default" class="mt-5"><slot /></div>
  </div>
</template>
