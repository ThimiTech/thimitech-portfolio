<script setup lang="ts">
// Placeholder rows while content loads. `label` is announced to screen readers.
withDefaults(defineProps<{ rows?: number; height?: string; label?: string }>(), {
  rows: 3,
  height: "h-10",
  label: "Loading",
});
</script>

<template>
  <div class="grid gap-2" aria-busy="true" :aria-label="label" role="status">
    <div v-for="i in rows" :key="i" class="rounded-md bg-panel/70 motion-safe:animate-pulse" :class="height" />
  </div>
</template>
