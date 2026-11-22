<script setup lang="ts">
import { PRIORITY_META } from './meta'
withDefaults(defineProps<{ priority: string; size?: number }>(), { size: 16 })
</script>
<template>
  <svg
    v-if="PRIORITY_META[priority]"
    viewBox="0 0 16 16"
    :width="size"
    :height="size"
    fill="none"
    :stroke="PRIORITY_META[priority]!.color"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    role="img"
    :aria-label="`${PRIORITY_META[priority]!.label} priority`"
  >
    <title>{{ PRIORITY_META[priority]!.label }} priority</title>
    <path :d="PRIORITY_META[priority]!.path" />
  </svg>
</template>
