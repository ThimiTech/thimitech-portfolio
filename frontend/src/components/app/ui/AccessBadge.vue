<script setup lang="ts">
// Shown only above Internal, so ordinary items stay uncluttered.
import { LEVEL_HINT, LEVEL_LABEL, type Level } from "@/stores/auth";

defineProps<{ level?: Level | number }>();
</script>

<template>
  <span
    v-if="level && level > 1"
    class="inline-flex items-center gap-1 rounded-full border px-1.5 py-px font-mono text-[10px] tracking-[0.06em] whitespace-nowrap uppercase"
    :class="level >= 3 ? 'border-rust/40 bg-rust/10 text-rust' : 'border-flag/40 bg-flag/10 text-flag'"
    :title="`${LEVEL_LABEL[level as Level]}: ${LEVEL_HINT[level as Level]}`"
  >
    <svg viewBox="0 0 24 24" class="h-2.5 w-2.5" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
    {{ LEVEL_LABEL[level as Level] }}
  </span>
</template>
