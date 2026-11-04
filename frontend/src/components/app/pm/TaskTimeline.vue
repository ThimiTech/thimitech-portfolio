<script setup lang="ts">
import { computed, ref } from 'vue'
import { dateLabel, dayNum, ymdOf, todayNPT, isOverdue, type Task, type Milestone, type Sprint } from './pm'
const props = withDefaults(
  defineProps<{ tasks: Task[]; milestones: Milestone[]; sprints?: Sprint[]; canManage?: boolean }>(),
  { sprints: () => [], canManage: false },
)
const emit = defineEmits<{
  select: [task: Task]
  reschedule: [task: Task, start: string, due: string]
}>()

const ZOOM = { Days: 34, Weeks: 14, Months: 5 } as const
const zoom = ref<keyof typeof ZOOM>('Weeks')
const px = computed(() => ZOOM[zoom.value])
const groupBy = ref<'none' | 'milestone' | 'assignee'>('none')

const dated = computed(() =>
  props.tasks
    .filter((t) => t.start_date || t.due_date)
    .sort((a, b) => (a.start_date || a.due_date!).localeCompare(b.start_date || b.due_date!)),
)
const range = computed(() => {
  const days = [
    ...dated.value.flatMap((t) => [t.start_date, t.due_date].filter((d): d is string => !!d)),
    ...props.milestones.map((m) => m.due_date),
    ...props.sprints.flatMap((s) => [s.start_date, s.end_date]),
  ].map(dayNum)
  const start = Math.min(...days) - 3
  const end = Math.max(...days) + 7
  return { start, span: Math.max(end - start + 1, 21) }
})
const width = computed(() => range.value.span * px.value)
const x = (ymd: string) => (dayNum(ymd) - range.value.start) * px.value
const today = computed(() => {
  const d = dayNum(todayNPT()) - range.value.start
  return d >= 0 && d < range.value.span ? d * px.value : null
})

// header: month bands + ticks (every day, every Monday, or every 1st)
const months = computed(() => {
  const out: { label: string; left: number; width: number }[] = []
  for (let d = range.value.start; d < range.value.start + range.value.span; d++) {
    const ymd = ymdOf(d)
    const label = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(ymd + 'T00:00:00Z'))
    const last = out[out.length - 1]
    if (last?.label === label) last.width += px.value
    else out.push({ label, left: (d - range.value.start) * px.value, width: px.value })
  }
  return out
})
const ticks = computed(() => {
  const out: { left: number; label: string; weekend: boolean }[] = []
  for (let d = range.value.start; d < range.value.start + range.value.span; d++) {
    const date = new Date(ymdOf(d) + 'T00:00:00Z')
    const dow = date.getUTCDay()
    const show = zoom.value === 'Days' || (zoom.value === 'Weeks' && dow === 1) || (zoom.value === 'Months' && date.getUTCDate() === 1)
    if (show || zoom.value === 'Days')
      out.push({ left: (d - range.value.start) * px.value, label: show ? String(date.getUTCDate()) : '', weekend: dow === 6 })
  }
  return out
})

const groups = computed(() => {
  if (groupBy.value === 'none') return [{ key: 'all', label: '', tasks: dated.value }]
  const map = new Map<string, { key: string; label: string; tasks: Task[] }>()
  for (const t of dated.value) {
    const key = groupBy.value === 'milestone' ? String(t.milestone ?? '') : String(t.assignee ?? '')
    const label =
      groupBy.value === 'milestone'
        ? props.milestones.find((m) => m.id === t.milestone)?.title || 'No milestone'
        : t.assignee_name || 'Unassigned'
    if (!map.has(key)) map.set(key, { key, label, tasks: [] })
    map.get(key)!.tasks.push(t)
  }
  return [...map.values()]
})

// drag to move (body) or resize (right handle); one day per step
const drag = ref<{ id: number; mode: 'move' | 'end'; x0: number; delta: number } | null>(null)
function span(task: Task) {
  const s = task.start_date || task.due_date!
  const e = task.due_date || task.start_date!
  const d = drag.value?.id === task.id ? drag.value.delta : 0
  const mode = drag.value?.id === task.id ? drag.value.mode : null
  const start = dayNum(s) + (mode === 'move' ? d : 0)
  const end = Math.max(dayNum(e) + d, start)
  return { start, end }
}
function barStyle(task: Task) {
  const { start, end } = span(task)
  return { left: `${(start - range.value.start) * px.value}px`, width: `${Math.max((end - start + 1) * px.value, 8)}px` }
}
function onDown(task: Task, mode: 'move' | 'end', e: PointerEvent) {
  if (!props.canManage || e.button !== 0) return
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  drag.value = { id: task.id, mode, x0: e.clientX, delta: 0 }
  e.stopPropagation()
}
function onMove(e: PointerEvent) {
  if (drag.value) drag.value.delta = Math.round((e.clientX - drag.value.x0) / px.value)
}
let dragged = false // swallow the click that follows a real drag
function onUp(task: Task) {
  const d = drag.value
  drag.value = null
  if (!d || d.delta === 0) return
  dragged = true
  commit(task, d.mode, d.delta)
}
function onClick(task: Task) {
  if (dragged) dragged = false
  else emit('select', task)
}
function commit(task: Task, mode: 'move' | 'end', delta: number) {
  const s = dayNum(task.start_date || task.due_date!)
  const e = dayNum(task.due_date || task.start_date!)
  const start = mode === 'move' ? s + delta : s
  emit('reschedule', task, ymdOf(start), ymdOf(Math.max(e + delta, start)))
}
function onKey(task: Task, e: KeyboardEvent) {
  if (!props.canManage || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return
  e.preventDefault()
  commit(task, e.shiftKey ? 'end' : 'move', e.key === 'ArrowRight' ? 1 : -1)
}
const barTone = (t: Task) =>
  t.status === 'done' ? 'bg-moss' : isOverdue(t) ? 'bg-rust' : t.status === 'active' ? 'bg-flag' : t.status === 'review' ? 'bg-contour' : 'bg-river'
</script>
<template>
  <section class="panel overflow-hidden" aria-label="Project timeline">
    <div class="panel-head flex-wrap">
      <div>
        <h2 class="font-medium">Delivery timeline</h2>
        <span class="text-xs text-ink/60">{{ tasks.length - dated.length }} tasks without dates</span>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-2 text-xs text-ink/60"
          >Group
          <select v-model="groupBy" class="input !w-auto !py-1 text-xs">
            <option value="none">None</option>
            <option value="milestone">Milestone</option>
            <option value="assignee">Assignee</option>
          </select></label
        >
        <div class="flex rounded-full border border-ink/15 p-0.5" role="group" aria-label="Zoom">
          <button
            v-for="z in Object.keys(ZOOM) as (keyof typeof ZOOM)[]"
            :key="z"
            type="button"
            class="rounded-full px-3 py-1 text-xs"
            :class="zoom === z ? 'bg-ink text-paper' : 'text-ink/60 hover:text-ink'"
            :aria-pressed="zoom === z"
            @click="zoom = z"
          >
            {{ z }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="!dated.length && !milestones.length" class="p-10 text-center text-sm text-ink/60">
      Add dates to tasks or a milestone to start your timeline.
    </div>
    <div v-else class="flex max-h-[70vh] overflow-auto" @pointermove="onMove">
      <!-- left: labels -->
      <div class="sticky left-0 z-20 w-44 shrink-0 border-r border-ink/10 bg-sheet sm:w-56">
        <div class="sticky top-0 z-10 h-14 border-b border-ink/10 bg-sheet px-3 pt-8 ledger-label">Work item</div>
        <div v-if="sprints.length" class="flex h-8 items-center border-b border-dashed border-ink/10 px-3 text-xs text-ink/60">Sprints</div>
        <template v-for="g in groups" :key="g.key">
          <div v-if="g.label" class="flex h-8 items-center bg-panel/50 px-3 text-xs font-medium">{{ g.label }}</div>
          <button
            v-for="t in g.tasks"
            :key="t.id"
            class="flex h-10 w-full items-center gap-2 border-b border-ink/5 px-3 text-left text-sm hover:text-river"
            @click="emit('select', t)"
          >
            <span class="shrink-0 font-mono text-[10px] text-ink/50">{{ t.key }}</span>
            <span class="truncate">{{ t.title }}</span>
          </button>
        </template>
        <div
          v-for="m in milestones"
          :key="`ml${m.id}`"
          class="flex h-9 items-center gap-2 border-b border-dashed border-ink/10 px-3 text-sm"
        >
          <span class="text-flag" aria-hidden="true">{{ m.completed ? '✓' : '◆' }}</span>
          <span class="truncate" :class="m.completed ? 'text-ink/50 line-through' : ''">{{ m.title }}</span>
        </div>
      </div>
      <!-- right: chart -->
      <div class="relative shrink-0" :style="{ width: `${width}px` }">
        <div class="sticky top-0 z-10 h-14 border-b border-ink/10 bg-sheet">
          <div
            v-for="m in months"
            :key="m.label"
            class="absolute top-0 h-7 truncate border-l border-ink/10 px-2 pt-1.5 text-xs font-medium"
            :style="{ left: `${m.left}px`, width: `${m.width}px` }"
          >
            {{ m.label }}
          </div>
          <span
            v-for="t in ticks"
            :key="t.left"
            class="absolute bottom-1 font-mono text-[10px] text-ink/50"
            :style="{ left: `${t.left + 2}px` }"
            >{{ t.label }}</span
          >
        </div>
        <!-- grid + weekends + today -->
        <div class="pointer-events-none absolute inset-x-0 bottom-0 top-14">
          <template v-for="t in ticks" :key="`g${t.left}`">
            <div v-if="t.label" class="absolute inset-y-0 border-l border-ink/[0.06]" :style="{ left: `${t.left}px` }" />
            <div
              v-if="t.weekend && zoom === 'Days'"
              class="absolute inset-y-0 bg-ink/[0.03]"
              :style="{ left: `${t.left}px`, width: `${px * 2}px` }"
            />
          </template>
          <div v-if="today !== null" class="absolute inset-y-0 z-10 w-px bg-flag" :style="{ left: `${today}px` }">
            <span class="absolute -left-4 -top-0 rounded bg-flag px-1 font-mono text-[9px] text-on-accent">today</span>
          </div>
        </div>
        <div v-if="sprints.length" class="relative h-8 border-b border-dashed border-ink/10">
          <div
            v-for="s in sprints"
            :key="s.id"
            class="absolute top-1.5 h-5 truncate rounded border px-1.5 text-[10px] leading-[18px]"
            :class="s.status === 'active' ? 'border-flag/40 bg-flag/10 text-flag' : s.status === 'completed' ? 'border-moss/30 bg-moss/10 text-moss' : 'border-ink/15 bg-panel text-ink/60'"
            :style="{ left: `${x(s.start_date)}px`, width: `${(dayNum(s.end_date) - dayNum(s.start_date) + 1) * px}px` }"
            :title="`${s.name}: ${dateLabel(s.start_date)} – ${dateLabel(s.end_date)}`"
          >
            {{ s.name }}
          </div>
        </div>
        <template v-for="g in groups" :key="`r${g.key}`">
          <div v-if="g.label" class="h-8 bg-panel/50" />
          <div v-for="t in g.tasks" :key="t.id" class="relative h-10 border-b border-ink/5">
            <button
              class="group absolute top-2 flex h-6 items-center overflow-hidden rounded-md px-2 text-left text-[10px] text-on-accent shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/50"
              :class="[barTone(t), canManage ? 'cursor-grab touch-none active:cursor-grabbing' : '', drag?.id === t.id ? 'opacity-80 ring-2 ring-ink/30' : '']"
              :style="barStyle(t)"
              :aria-label="`${t.key} ${t.title}: ${dateLabel(t.start_date)} to ${dateLabel(t.due_date)}${canManage ? '. Arrow keys move by a day; Shift+Arrow changes the end date.' : ''}`"
              @pointerdown="onDown(t, 'move', $event)"
              @pointerup="onUp(t)"
              @click="onClick(t)"
              @keydown="onKey(t, $event)"
            >
              <span class="truncate">{{ t.key }} · {{ t.assignee_name || 'Unassigned' }}</span>
              <span
                v-if="canManage"
                class="absolute inset-y-0 right-0 w-2 cursor-ew-resize bg-ink/0 group-hover:bg-ink/25"
                aria-hidden="true"
                @pointerdown="onDown(t, 'end', $event)"
              />
            </button>
          </div>
        </template>
        <div v-for="m in milestones" :key="`m${m.id}`" class="relative h-9 border-b border-dashed border-ink/10">
          <span
            class="absolute top-1.5 -ml-2 text-base"
            :class="m.completed ? 'text-moss' : 'text-flag'"
            :style="{ left: `${x(m.due_date) + px / 2}px` }"
            :title="`${m.title} · ${dateLabel(m.due_date)}`"
            :aria-label="`${m.title} due ${dateLabel(m.due_date)}`"
            >◆</span
          >
        </div>
      </div>
    </div>
    <div class="flex flex-wrap gap-4 border-t border-dashed border-ink/15 px-5 py-2.5 text-[11px] text-ink/60">
      <span v-for="[c, l] in [['bg-river', 'Backlog'], ['bg-flag', 'In progress'], ['bg-contour', 'Review'], ['bg-moss', 'Done'], ['bg-rust', 'Overdue']]" :key="l" class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm" :class="c" />{{ l }}</span>
      <span v-if="canManage" class="ml-auto">Drag a bar to reschedule · drag its right edge to change the end</span>
    </div>
  </section>
</template>
