<script setup lang="ts">
import Avatar from '../../ui/Avatar.vue'
import { TYPE_META } from './meta'
import { useFilters } from './useFilters'
import { useWorkspace } from './workspace'
withDefaults(defineProps<{ types?: boolean; within?: boolean }>(), { types: true, within: true })
const ws = useWorkspace()
const f = useFilters()
</script>
<template>
  <div class="flex flex-wrap items-center gap-2.5">
    <label class="relative w-full sm:w-56">
      <span class="sr-only">Search issues</span>
      <svg viewBox="0 0 16 16" class="pointer-events-none absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2 text-ink/40" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" /></svg>
      <input :value="f.search.value" class="input !py-1.5 !pl-8 text-sm" type="search" placeholder="Search issues" @input="f.search.value = ($event.target as HTMLInputElement).value" />
    </label>
    <div v-if="ws.people.length" class="flex items-center -space-x-1.5" role="group" aria-label="Filter by assignee">
      <button
        v-for="p in ws.people.slice(0, 8)"
        :key="p.id"
        type="button"
        class="rounded-full ring-2 transition hover:z-10 hover:-translate-y-0.5"
        :class="f.people.value.includes(p.id) ? 'z-10 ring-flag' : 'ring-sheet'"
        :aria-pressed="f.people.value.includes(p.id)"
        :aria-label="`Show ${p.name}'s issues`"
        :title="p.name"
        @click="f.togglePerson(p.id)"
      >
        <Avatar :name="p.name" :size="30" />
      </button>
    </div>
    <button type="button" class="rounded-full px-3 py-1.5 text-xs font-medium transition" :class="f.mine.value ? 'bg-ink text-paper' : 'text-ink/70 hover:bg-panel'" :aria-pressed="f.mine.value" @click="f.mine.value = !f.mine.value">Only my issues</button>
    <button type="button" class="rounded-full px-3 py-1.5 text-xs font-medium transition" :class="f.recent.value ? 'bg-ink text-paper' : 'text-ink/70 hover:bg-panel'" :aria-pressed="f.recent.value" @click="f.recent.value = !f.recent.value">Recently updated</button>
    <label v-if="types">
      <span class="sr-only">Issue type</span>
      <select v-model="f.type.value" class="input !w-auto !py-1.5 text-xs">
        <option value="">All types</option>
        <option v-for="t in ['story', 'task', 'bug']" :key="t" :value="t">{{ TYPE_META[t as 'story'].label }}</option>
      </select>
    </label>
    <label v-if="within && (ws.epics.length || ws.modules.length)">
      <span class="sr-only">Module or epic</span>
      <select v-model="f.within.value" class="input !w-auto max-w-52 !py-1.5 text-xs">
        <option value="">All modules & epics</option>
        <optgroup v-if="ws.modules.length" label="Modules">
          <option v-for="m in ws.modules" :key="m.id" :value="String(m.id)">{{ m.title }}</option>
        </optgroup>
        <optgroup v-if="ws.epics.length" label="Epics">
          <option v-for="e in ws.epics" :key="e.id" :value="String(e.id)">{{ e.title }}</option>
        </optgroup>
      </select>
    </label>
    <button v-if="f.active.value" type="button" class="text-xs text-river hover:underline" @click="f.clear()">Clear filters</button>
    <slot />
  </div>
</template>
