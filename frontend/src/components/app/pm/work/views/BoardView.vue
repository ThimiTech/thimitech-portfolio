<script setup lang="ts">
/** The board: the active sprint's issues by column (or every issue, kanban style), optional swimlanes, drag to move and rank. */
import { computed, ref, watch } from 'vue'
import EmptyState from '../../../ui/EmptyState.vue'
import Avatar from '../../../ui/Avatar.vue'
import { dateLabel, dayNum, todayNPT, type Task } from '../../pm'
import IssueCard from '../IssueCard.vue'
import InlineCreate from '../InlineCreate.vue'
import FilterBar from '../FilterBar.vue'
import TypeIcon from '../TypeIcon.vue'
import { byRank, categoryOf, moveInList, nearest, swatch, WORK_TYPES } from '../meta'
import { useFilters } from '../useFilters'
import { useWorkspace, type CreateDefaults } from '../workspace'

const ws = useWorkspace()
const f = useFilters()
const STORE = `thimi.board.${ws.project?.id}`
const saved = (() => {
  try {
    return JSON.parse(localStorage.getItem(STORE) || '{}') as { swim?: Swim; mode?: Mode }
  } catch {
    return {}
  }
})()
type Swim = 'none' | 'epic' | 'module' | 'assignee'
type Mode = 'sprint' | 'all'
const swim = ref<Swim>(saved.swim || 'none')
const mode = ref<Mode>(saved.mode || 'sprint')
watch([swim, mode], () => {
  try {
    localStorage.setItem(STORE, JSON.stringify({ swim: swim.value, mode: mode.value }))
  } catch {
    /* storage blocked */
  }
})

const sprint = computed(() => ws.activeSprint)
const sprintMode = computed(() => mode.value === 'sprint' && !!sprint.value)
const RECENT_DONE_DAYS = 14
const scope = computed(() => {
  const today = dayNum(todayNPT())
  return ws.work.filter((t) => {
    if (t.board !== ws.board?.id || !f.matches(t)) return false
    if (sprintMode.value) return t.sprint === sprint.value!.id
    // kanban: older finished work drops off the board (as in Jira)
    return t.status !== 'done' || !t.completed_at || today - dayNum(t.completed_at.slice(0, 10)) <= RECENT_DONE_DAYS
  })
})

interface Lane {
  key: string
  label: string
  item?: Task
  person?: string
  tasks: Task[]
  defaults: CreateDefaults
}
const lanes = computed<Lane[]>(() => {
  const all = scope.value
  if (swim.value === 'none') return [{ key: 'all', label: '', tasks: all, defaults: {} }]
  const groups = new Map<string, Lane>()
  const add = (key: string, make: () => Omit<Lane, 'tasks'>, t: Task) => {
    if (!groups.has(key)) groups.set(key, { ...make(), tasks: [] })
    groups.get(key)!.tasks.push(t)
  }
  for (const t of all) {
    if (swim.value === 'assignee') {
      const p = ws.people.find((x) => x.id === t.assignee)
      add(p ? `p${p.id}` : 'none', () => (p ? { key: `p${p.id}`, label: p.name, person: p.name, defaults: { assignee: p.id } } : { key: 'none', label: 'Unassigned', defaults: {} }), t)
    } else {
      const c = nearest(t, ws.byId, swim.value)
      add(c ? `c${c.id}` : 'none', () => (c ? { key: `c${c.id}`, label: c.title, item: c, defaults: { parent: c.id } } : { key: 'none', label: swim.value === 'epic' ? 'Issues without an epic' : 'Issues outside modules', defaults: {} }), t)
    }
  }
  const order = (l: Lane) => (l.key === 'none' ? Infinity : l.item ? l.item.position : ws.people.findIndex((p) => `p${p.id}` === l.key))
  return [...groups.values()].sort((a, b) => order(a) - order(b))
})
const cell = (lane: Lane, column: number) => lane.tasks.filter((t) => t.column === column).sort(byRank)
const collapsed = ref(new Set<string>())
function toggleLane(key: string) {
  const next = new Set(collapsed.value)
  if (!next.delete(key)) next.add(key)
  collapsed.value = next
}
const points = (ts: Task[]) => ts.reduce((s, t) => s + (t.estimate ?? 0), 0)
const daysLeft = computed(() => (sprint.value ? Math.max(dayNum(sprint.value.end_date) - dayNum(todayNPT()), 0) : 0))
const sprintStats = computed(() => (sprint.value ? rollupOf(ws.work.filter((t) => t.sprint === sprint.value!.id)) : null))
function rollupOf(ts: Task[]) {
  const done = ts.filter((t) => categoryOf(t.status) === 'done').length
  return { total: ts.length, done, percent: ts.length ? Math.round((done / ts.length) * 100) : 0 }
}

// ───── drag and drop ─────
const dragging = ref<number | null>(null)
const target = ref<{ lane: string; column: number; index: number } | null>(null)
function onDragStart(t: Task, e: DragEvent) {
  dragging.value = t.id
  e.dataTransfer?.setData('text/plain', t.key)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}
function onDragEnd() {
  dragging.value = null
  target.value = null
}
function overCard(lane: Lane, column: number, index: number, e: DragEvent) {
  if (dragging.value === null) return
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
  target.value = { lane: lane.key, column, index: e.clientY > r.top + r.height / 2 ? index + 1 : index }
}
function overColumn(lane: Lane, column: number) {
  if (dragging.value === null) return
  if (target.value?.lane !== lane.key || target.value.column !== column) target.value = { lane: lane.key, column, index: cell(lane, column).length }
}
function drop(lane: Lane) {
  const t = dragging.value !== null ? ws.byId.get(dragging.value) : undefined
  const to = target.value
  onDragEnd()
  if (!t || !to || !ws.canMove(t)) return
  const ids = cell(lane, to.column).map((x) => x.id)
  const from = ids.indexOf(t.id)
  const index = from >= 0 && from < to.index ? to.index - 1 : to.index
  const order = moveInList(ids, t.id, index)
  const changes: Record<string, unknown> = { column: to.column }
  if (ws.canManage && swim.value === 'assignee' && lane.key !== (t.assignee ? `p${t.assignee}` : 'none')) changes.assignee = lane.defaults.assignee ?? null
  ws.move(t, changes, ws.canManage ? order : undefined)
}
const dropLine = (lane: Lane, column: number, index: number) =>
  target.value?.lane === lane.key && target.value.column === column && target.value.index === index
</script>

<template>
  <div class="grid grid-cols-1 gap-4">
    <!-- sprint header -->
    <section v-if="sprintMode && sprint" class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink/60">
          <span>{{ dateLabel(sprint.start_date) }} – {{ dateLabel(sprint.end_date) }}</span>
          <span :class="daysLeft <= 2 ? 'font-medium text-rust' : ''">{{ daysLeft }} day{{ daysLeft === 1 ? '' : 's' }} remaining</span>
          <span v-if="sprintStats">{{ sprintStats.done }}/{{ sprintStats.total }} done · {{ sprintStats.percent }}%</span>
        </p>
        <p v-if="sprint.goal" class="mt-1 max-w-3xl text-sm text-ink/75 break-words"><span class="font-medium">Goal:</span> {{ sprint.goal }}</p>
      </div>
      <button v-if="ws.canManage" type="button" class="btn-ghost btn-sm" @click="ws.openSprint('complete', sprint)">Complete sprint</button>
    </section>

    <FilterBar>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <label v-if="(ws.project?.boards.length || 0) > 1">
          <span class="sr-only">Board</span>
          <select v-model="ws.boardId" class="input !w-auto !py-1.5 text-xs">
            <option v-for="b in ws.project!.boards" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </label>
        <label>
          <span class="sr-only">Group by</span>
          <select v-model="swim" class="input !w-auto !py-1.5 text-xs">
            <option value="none">No swimlanes</option>
            <option value="epic">Swimlanes: Epics</option>
            <option value="module">Swimlanes: Modules</option>
            <option value="assignee">Swimlanes: Assignees</option>
          </select>
        </label>
        <div v-if="ws.activeSprint" class="flex rounded-full border border-ink/15 p-0.5 text-xs" role="group" aria-label="Board scope">
          <button type="button" class="rounded-full px-3 py-1" :class="mode === 'sprint' ? 'bg-ink text-paper' : 'text-ink/65'" :aria-pressed="mode === 'sprint'" @click="mode = 'sprint'">Sprint</button>
          <button type="button" class="rounded-full px-3 py-1" :class="mode === 'all' ? 'bg-ink text-paper' : 'text-ink/65'" :aria-pressed="mode === 'all'" @click="mode = 'all'">All issues</button>
        </div>
      </div>
    </FilterBar>

    <div v-if="!ws.board" class="panel">
      <EmptyState title="No board yet" hint="Add a board in the project’s Settings to start tracking issues." />
    </div>
    <template v-else>
      <p v-if="mode === 'sprint' && !ws.activeSprint" class="rounded-lg border border-dashed border-ink/20 bg-panel/40 px-4 py-3 text-sm text-ink/70">
        No sprint is running, so the board shows every issue.
        <RouterLink :to="`${ws.base}/backlog`" class="text-river underline">Plan and start a sprint in the backlog →</RouterLink>
      </p>
      <div class="relative overflow-x-auto pb-2">
        <div class="grid grid-cols-1 gap-x-3" :style="{ gridTemplateColumns: `repeat(${ws.columns.length}, minmax(0, 1fr))`, minWidth: `${ws.columns.length * 15.5}rem` }">
          <!-- column headers -->
          <div v-for="c in ws.columns" :key="c.id" class="flex items-center gap-2 rounded-t-lg bg-panel/60 px-3 pt-3 pb-2">
            <h3 class="font-mono text-[11px] font-medium tracking-[0.08em] text-ink/65 uppercase">{{ c.name }}</h3>
            <span class="font-mono text-[11px] text-ink/50">{{ scope.filter((t) => t.column === c.id).length }}</span>
            <svg v-if="c.status === 'done'" viewBox="0 0 16 16" class="h-3.5 w-3.5 text-moss" fill="none" stroke="currentColor" stroke-width="2" aria-label="Done column"><path d="m3.5 8.5 3 3 6-7" /></svg>
            <span class="ml-auto font-mono text-[10.5px] text-ink/45" :title="`${points(scope.filter((t) => t.column === c.id))} story points`">{{ points(scope.filter((t) => t.column === c.id)) }} pt</span>
          </div>

          <template v-for="lane in lanes" :key="lane.key">
            <!-- lane header -->
            <div v-if="swim !== 'none'" class="col-span-full mt-3 flex min-w-0 items-center gap-2 border-b border-ink/10 bg-paper px-1 py-1.5">
              <button type="button" class="flex min-w-0 items-center gap-2 text-left text-sm" :aria-expanded="!collapsed.has(lane.key)" @click="toggleLane(lane.key)">
                <svg viewBox="0 0 12 12" class="h-3 w-3 shrink-0 text-ink/50 transition" :class="collapsed.has(lane.key) ? '-rotate-90' : ''" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
                <TypeIcon v-if="lane.item" :type="lane.item.type" />
                <Avatar v-else-if="lane.person" :name="lane.person" :size="20" />
                <span class="truncate font-medium" :style="lane.item ? { color: swatch(lane.item.id) } : {}">{{ lane.label }}</span>
                <span class="shrink-0 text-xs text-ink/50">{{ lane.tasks.length }} issue{{ lane.tasks.length === 1 ? '' : 's' }}</span>
              </button>
              <button v-if="lane.item" type="button" class="ml-1 shrink-0 text-xs text-river hover:underline" @click="ws.go(lane.item)">Open</button>
            </div>
            <template v-if="!collapsed.has(lane.key)">
              <div
                v-for="c in ws.columns"
                :key="`${lane.key}-${c.id}`"
                class="flex min-h-24 flex-col gap-2 bg-panel/60 p-2 transition-colors"
                :class="[target?.lane === lane.key && target.column === c.id ? 'bg-river/10 ring-2 ring-river/30 ring-inset' : '', swim === 'none' ? 'min-h-[60vh] rounded-b-lg' : '']"
                @dragover.prevent="overColumn(lane, c.id)"
                @drop.prevent="drop(lane)"
              >
                <template v-for="(t, i) in cell(lane, c.id)" :key="t.id">
                  <div v-if="dropLine(lane, c.id, i)" class="h-0.5 rounded bg-river" aria-hidden="true" />
                  <IssueCard
                    :task="t"
                    :dragging="dragging === t.id"
                    :draggable="ws.canMove(t)"
                    :class="ws.canMove(t) ? 'cursor-grab active:cursor-grabbing' : ''"
                    @dragstart="onDragStart(t, $event)"
                    @dragend="onDragEnd"
                    @dragover.prevent.stop="overCard(lane, c.id, i, $event)"
                  />
                </template>
                <div v-if="dropLine(lane, c.id, cell(lane, c.id).length)" class="h-0.5 rounded bg-river" aria-hidden="true" />
                <InlineCreate
                  class="mt-auto"
                  :types="WORK_TYPES"
                  :defaults="{ ...lane.defaults, column: c.id, sprint: sprintMode ? sprint!.id : null }"
                />
              </div>
            </template>
          </template>
        </div>
      </div>
      <p v-if="!scope.length" class="text-center text-sm text-ink/55">
        {{ f.active.value ? 'No issues match these filters.' : sprintMode ? 'This sprint has no issues yet. Add some from the backlog.' : 'No issues yet. Create one to get started.' }}
      </p>
      <p v-if="!sprintMode" class="text-xs text-ink/50">Issues finished more than {{ RECENT_DONE_DAYS }} days ago are hidden from the board. Find them in the list view.</p>
    </template>
  </div>
</template>
