<script setup lang="ts">
import type { ItemType } from '../plan'
import { TYPE_META } from './meta'
withDefaults(defineProps<{ type: ItemType; size?: number }>(), { size: 16 })
</script>
<template>
  <span
    class="inline-grid shrink-0 place-items-center rounded-[4px]"
    :style="{ width: `${size}px`, height: `${size}px`, background: TYPE_META[type].color }"
    :title="TYPE_META[type].label"
    role="img"
    :aria-label="TYPE_META[type].label"
  >
    <svg viewBox="0 0 16 16" :width="size - 3" :height="size - 3" fill="none" stroke="var(--color-on-accent)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path :d="TYPE_META[type].glyph" :fill="type === 'story' || type === 'epic' || type === 'bug' ? 'var(--color-on-accent)' : 'none'" />
    </svg>
  </span>
</template>
