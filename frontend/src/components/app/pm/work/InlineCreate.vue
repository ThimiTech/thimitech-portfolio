<script setup lang="ts">
/** Jira's "+ Create issue" row: pick a type, type a summary, Enter. Stays open for the next one; Esc closes. */
import { nextTick, ref, watch } from 'vue'
import type { ItemType } from '../plan'
import TypeIcon from './TypeIcon.vue'
import Dropdown from './Dropdown.vue'
import { TYPE_META } from './meta'
import { useWorkspace, type CreateDefaults } from './workspace'
const props = withDefaults(
  defineProps<{ types: ItemType[]; defaults?: CreateDefaults; label?: string; placeholder?: string; startOpen?: boolean }>(),
  { defaults: () => ({}), label: 'Create issue', placeholder: 'What needs to be done?', startOpen: false },
)
const emit = defineEmits<{ created: [id: number] }>()
const ws = useWorkspace()
const open = ref(props.startOpen)
const type = ref<ItemType>(props.types[0]!)
const title = ref('')
const busy = ref(false)
const input = ref<HTMLInputElement | null>(null)
watch(
  () => props.types,
  (t) => {
    if (!t.includes(type.value)) type.value = t[0]!
  },
)
async function start() {
  open.value = true
  await nextTick()
  input.value?.focus()
}
async function submit() {
  const text = title.value.trim()
  if (!text || busy.value) return
  busy.value = true
  const made = await ws.create({ ...props.defaults, type: type.value, title: text })
  busy.value = false
  if (made) {
    title.value = ''
    emit('created', made.id)
    await nextTick()
    input.value?.focus()
  }
}
const form = ref<HTMLFormElement | null>(null)
/** An empty row closes when focus leaves it (but not when it moves into the type menu). */
function maybeClose() {
  setTimeout(() => {
    const el = document.activeElement
    if (!title.value.trim() && !busy.value && !form.value?.contains(el) && !el?.closest('[role="menu"]')) cancel()
  })
}
function cancel() {
  open.value = false
  title.value = ''
}
defineExpose({ start })
</script>
<template>
  <div v-if="ws.canManage">
    <button
      v-if="!open"
      type="button"
      class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-ink/60 hover:bg-panel/70 hover:text-ink"
      @click="start"
    >
      <svg viewBox="0 0 16 16" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg>
      {{ label }}
    </button>
    <form v-else ref="form" class="flex items-center gap-2 rounded-md border-2 border-river/50 bg-sheet px-2 py-1" @submit.prevent="submit" @focusout="maybeClose">
      <Dropdown v-if="types.length > 1" label="Issue type" :width="170">
        <template #trigger="{ toggle, open: o }">
          <button type="button" class="flex items-center gap-1 rounded px-1 py-1 hover:bg-panel" :aria-expanded="o" aria-haspopup="menu" :aria-label="`Issue type: ${TYPE_META[type].label}. Change`" @click="toggle">
            <TypeIcon :type="type" />
            <svg viewBox="0 0 12 12" class="h-2.5 w-2.5 text-ink/50" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
          </button>
        </template>
        <template #default="{ close }">
          <button
            v-for="t in types"
            :key="t"
            type="button"
            role="menuitem"
            class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none"
            @click="(type = t), close(false), input?.focus()"
          >
            <TypeIcon :type="t" /> {{ TYPE_META[t].label }}
          </button>
        </template>
      </Dropdown>
      <TypeIcon v-else :type="type" class="mx-1" />
      <label class="min-w-0 flex-1">
        <span class="sr-only">{{ TYPE_META[type].label }} summary</span>
        <input
          ref="input"
          v-model="title"
          class="w-full bg-transparent py-1 text-sm outline-none placeholder:text-ink/40"
          :placeholder="placeholder"
          maxlength="200"
          :disabled="busy"
          @keydown.esc.prevent="cancel"
        />
      </label>
      <button class="btn-ink btn-sm !px-2.5 !py-1" :disabled="busy || !title.trim()">{{ busy ? '…' : 'Create' }}</button>
      <button type="button" class="rounded px-1.5 py-1 text-ink/50 hover:text-ink" aria-label="Cancel" @mousedown.prevent @click="cancel">✕</button>
    </form>
  </div>
</template>
