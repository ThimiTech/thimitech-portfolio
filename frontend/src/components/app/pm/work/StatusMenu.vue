<script setup lang="ts">
import { computed } from 'vue'
import type { Column, Task } from '../pm'
import Dropdown from './Dropdown.vue'
import { CATEGORY_META, categoryOf } from './meta'
import { useWorkspace } from './workspace'
const props = withDefaults(defineProps<{ task: Task; size?: 'sm' | 'md' }>(), { size: 'sm' })
const ws = useWorkspace()
const columns = computed<Column[]>(() => ws.columnsFor(props.task))
const current = computed(() => columns.value.find((c) => c.id === props.task.column))
const cat = computed(() => categoryOf(props.task.status))
const editable = computed(() => ws.canMove(props.task))
function pick(c: Column, close: () => void) {
  close()
  if (c.id !== props.task.column) ws.patch(props.task, { column: c.id })
}
</script>
<template>
  <Dropdown :label="`Status of ${task.key}`" :disabled="!editable" :width="200">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        class="inline-flex max-w-full items-center gap-1 rounded font-mono font-medium uppercase tracking-[0.04em] whitespace-nowrap"
        :class="[CATEGORY_META[cat].lozenge, size === 'md' ? 'px-2.5 py-1.5 text-[11.5px]' : 'px-1.5 py-0.5 text-[10px]', editable ? 'hover:brightness-95' : 'cursor-default']"
        :aria-haspopup="editable ? 'menu' : undefined"
        :aria-expanded="editable ? open : undefined"
        :aria-label="`Status: ${current?.name || task.status}${editable ? '. Change status' : ''}`"
        @click="toggle"
      >
        <span class="truncate">{{ current?.name || CATEGORY_META[cat].label }}</span>
        <svg v-if="editable" viewBox="0 0 12 12" class="h-2.5 w-2.5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
      </button>
    </template>
    <template #default="{ close }">
      <p class="px-3 pt-1.5 pb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink/50">Move to</p>
      <button
        v-for="c in columns"
        :key="c.id"
        type="button"
        role="menuitem"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none"
        @click="pick(c, close)"
      >
        <span class="rounded px-1.5 py-0.5 font-mono text-[10px] uppercase" :class="CATEGORY_META[categoryOf(c.status)].lozenge">{{ c.name }}</span>
        <span v-if="c.id === task.column" class="ml-auto text-xs text-ink/50">current</span>
      </button>
    </template>
  </Dropdown>
</template>
