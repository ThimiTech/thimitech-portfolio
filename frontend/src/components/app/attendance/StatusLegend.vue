<script setup lang="ts">
import { LEGEND, STATUS_META, type CellStatus } from "./attendance";

withDefaults(defineProps<{ items?: CellStatus[] }>(), { items: () => LEGEND });
</script>

<template>
  <ul class="flex flex-wrap gap-x-4 gap-y-2" aria-label="Legend">
    <li v-for="s in items" :key="s" class="flex items-center gap-1.5 text-xs text-ink/60">
      <span class="inline-flex h-5 min-w-5 items-center justify-center rounded px-1 font-mono text-[9.5px] font-medium" :class="STATUS_META[s].cell" aria-hidden="true">
        {{ STATUS_META[s].letter }}
      </span>
      {{ STATUS_META[s].label }}
    </li>
  </ul>
</template>
