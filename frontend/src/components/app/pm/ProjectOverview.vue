<script setup lang="ts">
import { computed } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import Avatar from '../ui/Avatar.vue'
import {
  dateLabel,
  dateTimeLabel,
  dayNum,
  errorMessage,
  HEALTH,
  isOverdue,
  linkLabel,
  todayNPT,
  type Doc,
  type Health,
  type Meeting,
  type Milestone,
  type Note,
  type Project,
  type ProjectLink,
  type Sprint,
  type Task,
} from './pm'
const props = defineProps<{
  project: Project
  tasks: Task[]
  sprints: Sprint[]
  milestones: Milestone[]
  meetings: Meeting[]
  notes: Note[]
  docs: Doc[]
  links: ProjectLink[]
}>()
const emit = defineEmits<{ go: [tab: string, id?: number]; select: [task: Task]; saved: [] }>()

const today = todayNPT()
const open = computed(() => props.tasks.filter((t) => t.status !== 'done'))
const overdue = computed(() => props.tasks.filter(isOverdue))
const STATUSES = [
  { id: 'backlog', label: 'Backlog', cls: 'bg-ink/25' },
  { id: 'active', label: 'In progress', cls: 'bg-flag' },
  { id: 'review', label: 'Review', cls: 'bg-contour' },
  { id: 'done', label: 'Done', cls: 'bg-moss' },
]
const mix = computed(() => STATUSES.map((s) => ({ ...s, n: props.tasks.filter((t) => t.status === s.id).length })))
const daysToDue = computed(() => (props.project.due_date ? dayNum(props.project.due_date) - dayNum(today) : null))
const sprint = computed(() => {
  const s = props.sprints.find((x) => x.status === 'active')
  if (!s) return null
  const ts = props.tasks.filter((t) => t.sprint === s.id)
  const total = ts.reduce((a, t) => a + (t.estimate ?? 1), 0)
  const done = ts.filter((t) => t.status === 'done').reduce((a, t) => a + (t.estimate ?? 1), 0)
  const elapsed = Math.min(Math.max((dayNum(today) - dayNum(s.start_date)) / Math.max(dayNum(s.end_date) - dayNum(s.start_date), 1), 0), 1)
  return { s, pct: total ? Math.round((done / total) * 100) : 0, time: Math.round(elapsed * 100), left: Math.max(dayNum(s.end_date) - dayNum(today), 0) }
})
const workload = computed(() => {
  const rows = props.project.people.map((p) => {
    const mine = open.value.filter((t) => t.assignee === p.id)
    return { p, n: mine.length, pts: mine.reduce((a, t) => a + (t.estimate ?? 0), 0), late: mine.filter(isOverdue).length }
  })
  const max = Math.max(...rows.map((r) => r.n), 1)
  return { rows: rows.sort((a, b) => b.n - a.n), max }
})
const nextMilestones = computed(() => props.milestones.filter((m) => !m.completed).slice(0, 4))
const nextMeetings = computed(() =>
  props.meetings
    .filter((m) => m.status === 'scheduled' && Date.parse(m.end) >= Date.now())
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, 3),
)
const recent = computed(() =>
  [
    ...props.notes.map((n) => ({ kind: 'Notes', id: n.id, title: n.title, at: n.updated_at, who: n.updated_by_name || n.author_name })),
    ...props.docs.map((d) => ({ kind: 'Docs', id: d.id, title: d.title, at: d.updated_at, who: d.uploaded_by_name })),
    ...props.meetings.map((m) => ({ kind: 'Meetings', id: m.id, title: m.title, at: m.updated_at, who: m.created_by_name })),
  ]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, 6),
)
const ago = (iso: string) => {
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000)
  return m < 60 ? `${Math.max(m, 1)}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`
}
async function setHealth(health: Health) {
  try {
    await api.patch(`pm/projects/${props.project.id}/`, { health })
    emit('saved')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const R = 34
const C = 2 * Math.PI * R
</script>
<template>
  <div class="grid gap-5">
    <!-- headline strip -->
    <section class="panel grid gap-6 p-5 md:grid-cols-[auto_1fr_auto] md:items-center">
      <div class="flex items-center gap-4">
        <svg viewBox="0 0 80 80" class="h-20 w-20 -rotate-90" role="img" :aria-label="`${project.progress.percent}% complete`">
          <circle cx="40" cy="40" :r="R" fill="none" stroke="var(--color-panel)" stroke-width="8" />
          <circle cx="40" cy="40" :r="R" fill="none" stroke="var(--color-moss)" stroke-width="8" stroke-linecap="round" :stroke-dasharray="C" :stroke-dashoffset="C * (1 - project.progress.percent / 100)" />
          <text x="40" y="45" text-anchor="middle" class="fill-ink font-mono" font-size="16" transform="rotate(90 40 40)">{{ project.progress.percent }}%</text>
        </svg>
        <div>
          <p class="ledger-label">Health</p>
          <select
            v-if="project.can_manage"
            :value="project.health"
            class="input mt-1 !w-36 !py-1 text-sm"
            aria-label="Project health"
            @change="setHealth(($event.target as HTMLSelectElement).value as Health)"
          >
            <option v-for="(h, k) in HEALTH" :key="k" :value="k">{{ h.label }}</option>
          </select>
          <p v-else class="mt-1 text-sm font-medium">{{ HEALTH[project.health].label }}</p>
        </div>
      </div>
      <dl class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div><dt class="ledger-label">Open tasks</dt><dd class="readout mt-1 text-2xl">{{ open.length }}</dd></div>
        <div><dt class="ledger-label">Overdue</dt><dd class="readout mt-1 text-2xl" :class="overdue.length ? 'text-rust' : ''">{{ overdue.length }}</dd></div>
        <div><dt class="ledger-label">Team</dt><dd class="readout mt-1 text-2xl">{{ project.people.length }}</dd></div>
        <div>
          <dt class="ledger-label">Due</dt>
          <dd class="readout mt-1 text-2xl" :class="daysToDue !== null && daysToDue < 0 ? 'text-rust' : ''">
            {{ daysToDue === null ? '—' : daysToDue < 0 ? `${-daysToDue}d late` : `${daysToDue}d` }}
          </dd>
        </div>
      </dl>
      <div class="flex -space-x-2">
        <Avatar v-for="p in project.people.slice(0, 6)" :key="p.id" :name="p.name" :size="34" class="ring-2 ring-sheet" />
        <span v-if="project.people.length > 6" class="grid h-[34px] w-[34px] place-items-center rounded-full bg-panel text-xs ring-2 ring-sheet">+{{ project.people.length - 6 }}</span>
      </div>
    </section>

    <div class="grid gap-5 lg:grid-cols-3">
      <!-- status mix + workload -->
      <section class="panel lg:col-span-2">
        <div class="panel-head"><h3 class="font-medium">Work in flight</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Board')">Open board →</button></div>
        <div class="panel-body grid gap-6">
          <div>
            <div class="flex h-3 overflow-hidden rounded-full bg-panel" role="img" :aria-label="mix.map((m) => `${m.label} ${m.n}`).join(', ')">
              <div v-for="m in mix" :key="m.id" :class="m.cls" :style="{ width: `${tasks.length ? (m.n / tasks.length) * 100 : 0}%` }" />
            </div>
            <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink/65">
              <span v-for="m in mix" :key="m.id" class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :class="m.cls" />{{ m.label }} <strong class="readout">{{ m.n }}</strong></span>
            </div>
          </div>
          <div>
            <p class="ledger-label mb-3">Open work by person</p>
            <p v-if="!workload.rows.length" class="text-sm text-ink/55">No team members yet.</p>
            <div v-for="r in workload.rows" :key="r.p.id" class="mb-2 grid grid-cols-[140px_1fr_auto] items-center gap-3 text-sm">
              <span class="truncate">{{ r.p.name }}</span>
              <div class="h-2 overflow-hidden rounded-full bg-panel"><div class="h-full rounded-full bg-river" :style="{ width: `${(r.n / workload.max) * 100}%` }" /></div>
              <span class="readout w-24 text-right text-xs text-ink/60">{{ r.n }} · {{ r.pts }}pt<span v-if="r.late" class="text-rust"> · {{ r.late }} late</span></span>
            </div>
          </div>
        </div>
      </section>

      <!-- sprint -->
      <section class="panel">
        <div class="panel-head"><h3 class="font-medium">Sprint</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Sprints')">Plan →</button></div>
        <div class="panel-body">
          <template v-if="sprint">
            <p class="font-display text-lg">{{ sprint.s.name }}</p>
            <p v-if="sprint.s.goal" class="mt-1 line-clamp-2 text-sm text-ink/65">{{ sprint.s.goal }}</p>
            <div class="mt-4 grid gap-3 text-xs">
              <div>
                <div class="mb-1 flex justify-between"><span>Work done</span><span class="readout">{{ sprint.pct }}%</span></div>
                <div class="h-2 rounded-full bg-panel"><div class="h-full rounded-full bg-moss" :style="{ width: `${sprint.pct}%` }" /></div>
              </div>
              <div>
                <div class="mb-1 flex justify-between"><span>Time elapsed</span><span class="readout">{{ sprint.time }}%</span></div>
                <div class="h-2 rounded-full bg-panel"><div class="h-full rounded-full bg-ink/40" :style="{ width: `${sprint.time}%` }" /></div>
              </div>
              <p :class="sprint.pct + 10 < sprint.time ? 'text-rust' : 'text-ink/60'">
                {{ sprint.left }} days left{{ sprint.pct + 10 < sprint.time ? ' · behind pace' : '' }}
              </p>
            </div>
          </template>
          <p v-else class="text-sm text-ink/60">No sprint running. Work in sprints to get burndown and velocity.</p>
        </div>
      </section>
    </div>

    <div class="grid gap-5 lg:grid-cols-3">
      <section class="panel">
        <div class="panel-head"><h3 class="font-medium">Next milestones</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Timeline')">Timeline →</button></div>
        <ul class="panel-body grid gap-3">
          <li v-if="!nextMilestones.length" class="text-sm text-ink/55">No open milestones.</li>
          <li v-for="m in nextMilestones" :key="m.id" class="flex items-center gap-3 text-sm">
            <span class="text-flag" aria-hidden="true">◆</span><span class="min-w-0 flex-1 truncate">{{ m.title }}</span>
            <span class="readout text-xs" :class="m.due_date < today ? 'text-rust' : 'text-ink/55'">{{ dateLabel(m.due_date) }}</span>
          </li>
        </ul>
      </section>
      <section class="panel">
        <div class="panel-head"><h3 class="font-medium">Upcoming meetings</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Meetings')">All →</button></div>
        <ul class="panel-body grid gap-3">
          <li v-if="!nextMeetings.length" class="text-sm text-ink/55">Nothing scheduled.</li>
          <li v-for="m in nextMeetings" :key="m.id">
            <button class="w-full text-left text-sm hover:text-river" @click="emit('go', 'Meetings', m.id)">
              <span class="block truncate font-medium">{{ m.title }}</span><span class="text-xs text-ink/55">{{ dateTimeLabel(m.start) }}</span>
            </button>
          </li>
        </ul>
      </section>
      <section class="panel">
        <div class="panel-head"><h3 class="font-medium">Recently updated</h3></div>
        <ul class="panel-body grid gap-3">
          <li v-if="!recent.length" class="text-sm text-ink/55">Notes, documents and meetings show up here.</li>
          <li v-for="r in recent" :key="`${r.kind}${r.id}`" class="flex items-center gap-3 text-sm">
            <span class="w-16 shrink-0 font-mono text-[10px] uppercase text-ink/45">{{ r.kind }}</span>
            <button class="min-w-0 flex-1 truncate text-left hover:text-river" @click="emit('go', r.kind, r.id)">{{ r.title }}</button>
            <span class="shrink-0 text-[11px] text-ink/50">{{ ago(r.at) }}</span>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="links.length" class="panel">
      <div class="panel-head"><h3 class="font-medium">Quick links</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Hub')">Manage →</button></div>
      <div class="panel-body flex flex-wrap gap-2">
        <a v-for="l in links" :key="l.id" :href="l.url" target="_blank" rel="noopener noreferrer" class="flex items-center gap-2 rounded-full border border-ink/15 px-3 py-1.5 text-sm hover:border-ink/30 hover:bg-panel">
          <span class="font-mono text-[10px] uppercase text-ink/50">{{ linkLabel(l.kind) }}</span>{{ l.title }} ↗
        </a>
      </div>
    </section>
  </div>
</template>
