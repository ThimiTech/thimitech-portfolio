<script setup lang="ts">
/** Assignee picker: avatar trigger, searchable list of project people. */
import { computed, ref } from 'vue'
import Avatar from '../../ui/Avatar.vue'
import Dropdown from './Dropdown.vue'
import { useWorkspace } from './workspace'
const props = withDefaults(defineProps<{ value: number | null; disabled?: boolean; size?: number; showName?: boolean; label?: string }>(), {
  size: 24,
  label: 'Assignee',
})
const emit = defineEmits<{ change: [id: number | null] }>()
const ws = useWorkspace()
const q = ref('')
const person = computed(() => ws.people.find((p) => p.id === props.value) || null)
const shown = computed(() => ws.people.filter((p) => p.name.toLowerCase().includes(q.value.toLowerCase())))
function pick(id: number | null, close: () => void) {
  close()
  q.value = ''
  if (id !== props.value) emit('change', id)
}
</script>
<template>
  <Dropdown :label="label" :disabled="disabled" :width="240">
    <template #trigger="{ toggle, open }">
      <button
        type="button"
        class="inline-flex max-w-full min-w-0 items-center gap-2 rounded-full text-left"
        :class="disabled ? 'cursor-default' : 'hover:opacity-80'"
        :aria-haspopup="disabled ? undefined : 'menu'"
        :aria-expanded="disabled ? undefined : open"
        :aria-label="`${label}: ${person?.name || 'Unassigned'}${disabled ? '' : '. Change'}`"
        :title="person?.name || 'Unassigned'"
        @click="toggle"
      >
        <Avatar v-if="person" :name="person.name" :size="size" />
        <span v-else class="grid grid-cols-1 shrink-0 place-items-center rounded-full border border-dashed border-ink/30 text-ink/40" :style="{ width: `${size}px`, height: `${size}px` }" aria-hidden="true">
          <svg viewBox="0 0 16 16" class="h-3/5 w-3/5" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5.5" r="2.5" /><path d="M3 14c.6-2.7 2.6-4 5-4s4.4 1.3 5 4" /></svg>
        </span>
        <span v-if="showName" class="truncate text-sm" :class="person ? '' : 'text-ink/55'">{{ person?.name || 'Unassigned' }}</span>
      </button>
    </template>
    <template #default="{ close }">
      <div v-if="ws.people.length > 7" class="px-2 pt-1 pb-1.5">
        <input v-model="q" class="input !py-1 text-sm" placeholder="Search people…" aria-label="Search people" />
      </div>
      <button type="button" role="menuitem" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-ink/65 hover:bg-panel focus-visible:bg-panel focus-visible:outline-none" @click="pick(null, close)">
        <span class="h-6 w-6 rounded-full border border-dashed border-ink/30" aria-hidden="true" /> Unassigned
      </button>
      <button
        v-if="ws.me && ws.people.some((p) => p.id === ws.me) && value !== ws.me"
        type="button"
        role="menuitem"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-river hover:bg-panel focus-visible:bg-panel focus-visible:outline-none"
        @click="pick(ws.me, close)"
      >
        <span class="grid grid-cols-1 h-6 w-6 place-items-center text-xs" aria-hidden="true">→</span> Assign to me
      </button>
      <button
        v-for="p in shown"
        :key="p.id"
        type="button"
        role="menuitem"
        class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none"
        :class="p.id === value ? 'font-medium' : ''"
        @click="pick(p.id, close)"
      >
        <Avatar :name="p.name" :size="24" /><span class="truncate">{{ p.name }}</span>
        <span v-if="p.id === value" class="ml-auto text-xs text-ink/50">✓</span>
      </button>
    </template>
  </Dropdown>
</template>
