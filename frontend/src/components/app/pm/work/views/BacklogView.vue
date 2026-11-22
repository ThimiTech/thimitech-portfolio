<script setup lang="ts">
/** Backlog: the active and planned sprints, then the backlog. Drag issues between them and rank them; plan, start and
 *  complete sprints; filter by epic from the side panel. */
import { computed, ref } from 'vue'
import { dateLabel, type Sprint, type Task } from '../../pm'
import IssueRow from '../IssueRow.vue'
import InlineCreate from '../InlineCreate.vue'
import FilterBar from '../FilterBar.vue'
import TypeIcon from '../TypeIcon.vue'
import Dropdown from '../Dropdown.vue'
import { CATEGORY_META, categoryOf, moveInList, rollup, swatch, WORK_TYPES, type Category } from '../meta'
import { useFilters } from '../useFilters'
import { useWorkspace } from '../workspace'

const ws = useWorkspace()
const f = useFilters()
const showEpics = ref(true)

interface Section {
  key: string
  sprint: Sprint | null
  tasks: Task[]
  all: Task[]
}
const sections = computed<Section[]>(() => {
  const open = ws.sprints.filter((s) => s.status !== 'completed').sort((a, b) => (a.status === 'active' ? -1 : b.status === 'active' ? 1 : a.start_date.localeCompare(b.start_date)))
  const of = (s: Sprint) => ws.work.filter((t) => t.sprint === s.id)
  return [
    ...open.map((s) => ({ key: `s${s.id}`, sprint: s, all: of(s), tasks: of(s).filter(f.matches) })),
    {
      key: 'backlog',
      sprint: null,
      all: ws.work.filter((t) => !t.sprint && t.status !== 'done'),
      tasks: ws.work.filter((t) => !t.sprint && t.status !== 'done' && f.matches(t)),
    },
  ]
})
const collapsed = ref(new Set<string>())
function toggle(key: string) {
  const next = new Set(collapsed.value)
  if (!next.delete(key)) next.add(key)
  collapsed.value = next
}
function totals(ts: Task[]) {
  const out: Record<Category, number> = { todo: 0, progress: 0, done: 0 }
  for (const t of ts) out[categoryOf(t.status)] += t.estimate ?? 0
  return out
}

// ───── epics panel ─────
const epicGroups = computed(() => {
  const groups = ws.modules.map((m) => ({ module: m, epics: ws.epics.filter((e) => e.parent === m.id) }))
  const loose = ws.epics.filter((e) => !e.parent || ws.byId.get(e.parent)?.type !== 'module')
  return [...groups.filter((g) => g.epics.length), ...(loose.length ? [{ module: null, epics: loose }] : [])]
})
const pickEpic = (id: number) => (f.within.value = f.within.value === String(id) ? '' : String(id))

// ───── drag and drop ─────
const dragging = ref<number | null>(null)
const target = ref<{ section: string; index: number } | null>(null)
function onDragStart(t: Task, e: DragEvent) {
  dragging.value = t.id
  e.dataTransfer?.setData('text/plain', t.key)
}
function onDragEnd() {
  dragging.value = null
  target.value = null
}
function overRow(s: Section, index: number, e: DragEvent) {
  if (dragging.value === null) return
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
  target.value = { section: s.key, index: e.clientY > r.top + r.height / 2 ? index + 1 : index }
}
function overSection(s: Section) {
  if (dragging.value !== null && target.value?.section !== s.key) target.value = { section: s.key, index: s.tasks.length }
}
function drop(s: Section) {
  const t = dragging.value !== null ? ws.byId.get(dragging.value) : undefined
  const to = target.value
  onDragEnd()
  if (!t || !to || !ws.canManage) return
  const ids = s.tasks.map((x) => x.id)
  const from = ids.indexOf(t.id)
  const order = moveInList(ids, t.id, from >= 0 && from < to.index ? to.index - 1 : to.index)
  ws.move(t, { sprint: s.sprint?.id ?? null }, order)
}
const line = (s: Section, i: number) => target.value?.section === s.key && target.value.index === i
</script>

<template>
  <div class="grid grid-cols-1 gap-4">
    <FilterBar :within="false">
      <button type="button" class="ml-auto rounded-full px-3 py-1.5 text-xs font-medium" :class="showEpics ? 'bg-panel text-ink' : 'text-ink/65 hover:bg-panel'" :aria-pressed="showEpics" @click="showEpics = !showEpics">
        Epics panel
      </button>
      <button v-if="ws.canManage" type="button" class="btn-ghost btn-sm" @click="ws.openSprint('create')">Create sprint</button>
    </FilterBar>

    <div class="grid grid-cols-1 items-start gap-4" :class="showEpics ? 'lg:grid-cols-[16rem_minmax(0,1fr)]' : ''">
      <!-- epics panel -->
      <aside v-if="showEpics" class="panel min-w-0 p-2 lg:sticky lg:top-4" aria-label="Epics">
        <div class="flex items-center justify-between px-2 py-1.5">
          <h2 class="text-sm font-semibold">Epics</h2>
          <button type="button" class="text-ink/50 hover:text-ink" aria-label="Close epics panel" @click="showEpics = false">✕</button>
        </div>
        <button type="button" class="mb-1 w-full rounded-md px-2 py-1.5 text-left text-sm" :class="!f.within.value ? 'bg-panel font-medium' : 'hover:bg-panel/60'" @click="f.within.value = ''">All issues</button>
        <div v-for="g in epicGroups" :key="g.module?.id ?? 'loose'" class="mt-2">
          <p class="truncate px-2 pb-1 font-mono text-[10px] tracking-[0.1em] text-ink/50 uppercase">{{ g.module ? g.module.title : 'No module' }}</p>
          <div v-for="e in g.epics" :key="e.id" class="rounded-md" :class="f.within.value === String(e.id) ? 'bg-panel' : 'hover:bg-panel/60'">
            <button type="button" class="w-full px-2 pt-1.5 text-left" :aria-pressed="f.within.value === String(e.id)" @click="pickEpic(e.id)">
              <span class="flex min-w-0 items-center gap-2 text-sm">
                <span class="h-2.5 w-2.5 shrink-0 rounded-sm" :style="{ background: swatch(e.id) }" aria-hidden="true" />
                <span class="truncate">{{ e.title }}</span>
              </span>
            </button>
            <div class="flex items-center gap-2 px-2 pt-1 pb-1.5">
              <span class="h-1 flex-1 overflow-hidden rounded-full bg-ink/10"><span class="block h-full bg-moss" :style="{ width: `${rollup(e.id, ws.children).percent}%` }" /></span>
              <span class="font-mono text-[10px] text-ink/50">{{ rollup(e.id, ws.children).percent }}%</span>
              <button type="button" class="text-[11px] text-river hover:underline" :aria-label="`Open epic ${e.title}`" @click="ws.go(e)">Open</button>
            </div>
          </div>
        </div>
        <p v-if="!ws.epics.length" class="px-2 py-2 text-xs text-ink/55">No epics yet. Epics group related stories, like a feature.</p>
        <InlineCreate class="mt-2" :types="['epic']" label="Create epic" placeholder="Epic name" />
      </aside>

      <div class="grid grid-cols-1 min-w-0 gap-4">
        <section
          v-for="s in sections"
          :key="s.key"
          class="rounded-xl border bg-sheet transition-colors"
          :class="target?.section === s.key ? 'border-river/60 ring-2 ring-river/20' : 'border-ink/10'"
          :aria-label="s.sprint ? s.sprint.name : 'Backlog'"
          @dragover.prevent="overSection(s)"
          @drop.prevent="drop(s)"
        >
          <header class="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5">
            <button type="button" class="flex min-w-0 items-center gap-2 text-left" :aria-expanded="!collapsed.has(s.key)" @click="toggle(s.key)">
              <svg viewBox="0 0 12 12" class="h-3 w-3 shrink-0 text-ink/50 transition" :class="collapsed.has(s.key) ? '-rotate-90' : ''" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
              <h2 class="truncate text-sm font-semibold">{{ s.sprint ? s.sprint.name : 'Backlog' }}</h2>
            </button>
            <span v-if="s.sprint" class="text-xs text-ink/55">{{ dateLabel(s.sprint.start_date) }} – {{ dateLabel(s.sprint.end_date) }}</span>
            <span v-if="s.sprint?.status === 'active'" class="rounded bg-sky/15 px-1.5 py-0.5 font-mono text-[10px] text-sky uppercase">Active</span>
            <span class="text-xs text-ink/55">({{ s.all.length }} issue{{ s.all.length === 1 ? '' : 's' }}<template v-if="s.tasks.length !== s.all.length">, {{ s.tasks.length }} shown</template>)</span>
            <span class="ml-auto flex items-center gap-1" :title="'Story points: to do · in progress · done'">
              <span v-for="(n, cat) in totals(s.all)" :key="cat" class="min-w-6 rounded-full px-1.5 py-0.5 text-center font-mono text-[10.5px]" :class="CATEGORY_META[cat].lozenge" :aria-label="`${CATEGORY_META[cat].label}: ${n} points`">{{ n }}</span>
            </span>
            <template v-if="ws.canManage">
              <button v-if="s.sprint?.status === 'active'" type="button" class="btn-ghost btn-sm" @click="ws.openSprint('complete', s.sprint)">Complete sprint</button>
              <button v-else-if="s.sprint" type="button" class="btn-primary btn-sm" :disabled="!!ws.activeSprint || !s.all.length" :title="ws.activeSprint ? 'Complete the active sprint first' : !s.all.length ? 'Add issues first' : ''" @click="ws.startSprint(s.sprint)">Start sprint</button>
              <button v-else type="button" class="btn-ghost btn-sm" @click="ws.openSprint('create')">Create sprint</button>
              <Dropdown v-if="s.sprint" :label="`${s.sprint.name} actions`" :width="170" align="right">
                <template #trigger="{ toggle: t, open }">
                  <button type="button" class="rounded px-2 py-1 text-ink/55 hover:bg-panel" :aria-label="`${s.sprint.name} actions`" aria-haspopup="menu" :aria-expanded="open" @click="t">•••</button>
                </template>
                <template #default="{ close }">
                  <button type="button" role="menuitem" class="block w-full px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none" @click="close(false), ws.openSprint('edit', s.sprint)">Edit sprint</button>
                  <button v-if="s.sprint.status === 'planned'" type="button" role="menuitem" class="block w-full px-3 py-1.5 text-left text-rust hover:bg-panel focus-visible:bg-panel focus-visible:outline-none" @click="close(false), ws.deleteSprint(s.sprint)">Delete sprint</button>
                </template>
              </Dropdown>
            </template>
          </header>
          <p v-if="s.sprint?.goal && !collapsed.has(s.key)" class="-mt-1 px-9 pb-2 text-xs text-ink/65 break-words">{{ s.sprint.goal }}</p>
          <template v-if="!collapsed.has(s.key)">
            <ul class="border-t border-ink/10">
              <template v-for="(t, i) in s.tasks" :key="t.id">
                <li v-if="line(s, i)" class="h-0.5 bg-river" aria-hidden="true" />
                <li
                  class="cursor-pointer border-b border-ink/5 transition-colors hover:bg-panel/40"
                  :class="[dragging === t.id ? 'opacity-40' : '', ws.canManage ? 'active:cursor-grabbing' : '']"
                  :draggable="ws.canManage"
                  @dragstart="onDragStart(t, $event)"
                  @dragend="onDragEnd"
                  @dragover.prevent.stop="overRow(s, i, $event)"
                >
                  <IssueRow :task="t" />
                </li>
              </template>
              <li v-if="line(s, s.tasks.length)" class="h-0.5 bg-river" aria-hidden="true" />
              <li v-if="!s.tasks.length" class="m-2 rounded-lg border-2 border-dashed border-ink/15 px-4 py-5 text-center text-sm text-ink/55">
                <template v-if="f.active.value && s.all.length">No issues here match the filters.</template>
                <template v-else-if="s.sprint">Plan this sprint: drag issues here from the backlog, or create them below.</template>
                <template v-else>Your backlog is empty.</template>
              </li>
            </ul>
            <div class="p-1.5">
              <InlineCreate :types="WORK_TYPES" :defaults="{ sprint: s.sprint?.id ?? null, ...(f.within.value ? { parent: Number(f.within.value) } : {}) }" />
            </div>
          </template>
        </section>
        <p class="flex items-center gap-2 text-xs text-ink/50">
          <TypeIcon type="story" :size="14" /> Drag issues to plan sprints and set their order. Done issues leave the backlog; modules and epics are planned on their own pages.
        </p>
      </div>
    </div>
  </div>
</template>
