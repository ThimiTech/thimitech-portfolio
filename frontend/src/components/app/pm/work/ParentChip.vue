<script setup lang="ts">
import type { Task } from '../pm'
import { swatch } from './meta'
import { useWorkspace } from './workspace'
defineProps<{ item: Task }>()
const ws = useWorkspace()
</script>
<template>
  <RouterLink
    :to="ws.pathOf(item)"
    draggable="false"
    class="inline-flex max-w-[11rem] min-w-0 shrink items-center rounded px-1.5 py-0.5 text-[10.5px] font-medium uppercase tracking-[0.02em]"
    :style="{ color: swatch(item.id), background: `color-mix(in srgb, ${swatch(item.id)} 14%, transparent)` }"
    :title="`${item.type === 'module' ? 'Module' : 'Epic'}: ${item.title}`"
    @click.stop
  >
    <span class="truncate">{{ item.title }}</span>
  </RouterLink>
</template>
