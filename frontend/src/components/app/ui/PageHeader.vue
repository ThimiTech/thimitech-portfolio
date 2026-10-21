<script setup lang="ts">
defineProps<{ eyebrow?: string; title: string; description?: string }>();
</script>

<template>
  <header class="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div class="min-w-0">
      <p v-if="eyebrow" class="ledger-label flex items-center gap-2">
        <span class="inline-block h-1.5 w-1.5 rounded-full bg-flag" aria-hidden="true" />
        {{ eyebrow }}
      </p>
      <h1 class="mt-2 font-display text-[28px] leading-tight font-medium tracking-tight text-ink sm:text-[32px]">
        {{ title }}
      </h1>
      <p v-if="description" class="mt-1.5 max-w-2xl text-sm text-ink/60">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
