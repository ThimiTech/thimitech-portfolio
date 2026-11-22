<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/api'
import MarkdownView from './MarkdownView.vue'
import TypeIcon from './work/TypeIcon.vue'
import { ago as since, FIELD_LABEL, rollup, swatch } from './work/meta'
import { useWorkspace } from './work/workspace'
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
  type Activity,
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

const ws = useWorkspace()
const today = todayNPT()
const work = computed(() => `/app/projects/${props.project.id}/work`)
const aboutOpen = ref(false)
const longAbout = computed(() => props.project.description.length > 360 || props.project.description.split('\n').length > 5)
const modules = computed(() => ws.modules.map((m) => ({ m, r: rollup(m.id, ws.children, ws.blocked) })))
const feed = ref<Activity[]>([])
async function loadFeed() {
  try {
    feed.value = (await api.get<Activity[]>('pm/activity/', { params: { project: props.project.id } })).data
  } catch {
    feed.value = []
  }
}
onMounted(loadFeed)
watch(() => props.tasks.map((t) => t.updated_at).join(), loadFeed)
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
/** Notes, documents, meetings and issue changes, newest first (an issue appears once, with its latest change). */
const recent = computed(() => {
  const seen = new Set<number>()
  const issues = feed.value
    .filter((a) => !seen.has(a.task) && seen.add(a.task))
    .map((a) => ({
      kind: 'Issue', label: a.task_key, id: a.task, title: a.task_title, at: a.at, who: a.actor_name || '',
      what: a.field === 'created' ? 'created' : `${(FIELD_LABEL[a.field] || a.field).toLowerCase()} changed`,
    }))
  return [
    ...props.notes.map((n) => ({ kind: 'Notes', label: 'Note', id: n.id, title: n.title, at: n.updated_at, who: n.updated_by_name || n.author_name, what: '' })),
    ...props.docs.map((d) => ({ kind: 'Docs', label: 'Doc', id: d.id, title: d.title, at: d.updated_at, who: d.uploaded_by_name, what: '' })),
    ...props.meetings.map((m) => ({ kind: 'Meetings', label: 'Meeting', id: m.id, title: m.title, at: m.updated_at, who: m.created_by_name, what: '' })),
    ...issues,
  ]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, 7)
})
function openRecent(r: { kind: string; id: number }) {
  if (r.kind !== 'Issue') return emit('go', r.kind, r.id)
  const t = ws.byId.get(r.id)
  if (t) ws.go(t)
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
  <div class="grid grid-cols-1 gap-5">
    <!-- headline strip -->
    <section class="panel grid min-w-0 gap-6 p-5 md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-center">
      <div class="flex items-center gap-4">
        <svg viewBox="0 0 80 80" class="h-20 w-20 shrink-0 -rotate-90" role="img" :aria-label="`${project.progress.percent}% complete`">
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
        <div><dt class="ledger-label">Open issues</dt><dd class="readout mt-1 text-2xl">{{ open.length }}</dd></div>
        <div><dt class="ledger-label">Overdue</dt><dd class="readout mt-1 text-2xl" :class="overdue.length ? 'text-rust' : ''">{{ overdue.length }}</dd></div>
        <div><dt class="ledger-label">Team</dt><dd class="readout mt-1 text-2xl">{{ project.people.length }}</dd></div>
        <div>
          <dt class="ledger-label">Due</dt>
          <dd class="readout mt-1 text-2xl" :class="daysToDue !== null && daysToDue < 0 ? 'text-rust' : ''">
            {{ daysToDue === null ? '—' : daysToDue < 0 ? `${-daysToDue}d late` : `${daysToDue}d` }}
          </dd>
        </div>
      </dl>
      <div class="flex flex-wrap -space-x-2">
        <Avatar v-for="p in project.people.slice(0, 6)" :key="p.id" :name="p.name" :size="34" class="ring-2 ring-sheet" />
        <span v-if="project.people.length > 6" class="grid grid-cols-1 h-[34px] w-[34px] place-items-center rounded-full bg-panel text-xs ring-2 ring-sheet">+{{ project.people.length - 6 }}</span>
      </div>
    </section>

    <!-- about -->
    <section v-if="project.description" class="panel min-w-0" aria-labelledby="ov-about">
      <div class="panel-head">
        <h3 id="ov-about" class="font-medium">About this project</h3>
        <span v-if="project.start_date || project.due_date" class="text-xs text-ink/55">{{ project.start_date ? dateLabel(project.start_date) : '…' }} → {{ project.due_date ? dateLabel(project.due_date) : '…' }}</span>
      </div>
      <div class="panel-body">
        <div class="relative overflow-hidden" :class="longAbout && !aboutOpen ? 'max-h-28' : ''">
          <MarkdownView :source="project.description" class="max-w-4xl text-ink/80" />
          <div v-if="longAbout && !aboutOpen" class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-sheet" />
        </div>
        <button v-if="longAbout" type="button" class="mt-2 text-xs text-river hover:underline" :aria-expanded="aboutOpen" @click="aboutOpen = !aboutOpen">{{ aboutOpen ? 'Show less' : 'Show more' }}</button>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <!-- status mix + workload -->
      <section class="panel min-w-0 lg:col-span-2">
        <div class="panel-head"><h3 class="font-medium">Work in flight</h3><RouterLink :to="`${work}/board`" class="text-xs text-river hover:underline">Open board →</RouterLink></div>
        <div class="panel-body grid grid-cols-1 gap-6">
          <div class="min-w-0">
            <div class="flex h-3 overflow-hidden rounded-full bg-panel" role="img" :aria-label="mix.map((m) => `${m.label} ${m.n}`).join(', ')">
              <div v-for="m in mix" :key="m.id" :class="m.cls" :style="{ width: `${tasks.length ? (m.n / tasks.length) * 100 : 0}%` }" />
            </div>
            <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink/65">
              <span v-for="m in mix" :key="m.id" class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :class="m.cls" />{{ m.label }} <strong class="readout">{{ m.n }}</strong></span>
            </div>
          </div>
          <div class="min-w-0">
            <p class="ledger-label mb-3">Open work by person</p>
            <p v-if="!workload.rows.length" class="text-sm text-ink/55">No team members yet.</p>
            <div v-for="r in workload.rows" :key="r.p.id" class="mb-2 grid grid-cols-[minmax(0,8.75rem)_minmax(0,1fr)_7.5rem] items-center gap-3 text-sm">
              <span class="truncate" :title="r.p.name">{{ r.p.name }}</span>
              <div class="h-2 overflow-hidden rounded-full bg-panel"><div class="h-full rounded-full bg-river" :style="{ width: `${(r.n / workload.max) * 100}%` }" /></div>
              <span class="readout text-right text-xs whitespace-nowrap text-ink/60">{{ r.n }} · {{ r.pts }}pt<span v-if="r.late" class="text-rust"> · {{ r.late }} late</span></span>
            </div>
          </div>
        </div>
      </section>

      <!-- sprint -->
      <section class="panel min-w-0">
        <div class="panel-head"><h3 class="font-medium">Sprint</h3><RouterLink :to="`${work}/backlog`" class="text-xs text-river hover:underline">Backlog →</RouterLink></div>
        <div class="panel-body">
          <template v-if="sprint">
            <p class="truncate font-display text-lg" :title="sprint.s.name">{{ sprint.s.name }}</p>
            <p v-if="sprint.s.goal" class="mt-1 line-clamp-2 text-sm break-words text-ink/65">{{ sprint.s.goal }}</p>
            <div class="mt-4 grid grid-cols-1 gap-3 text-xs">
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
            <RouterLink :to="`${work}/reports`" class="mt-4 inline-block text-xs text-river hover:underline">Burndown and velocity →</RouterLink>
          </template>
          <p v-else class="text-sm text-ink/60">No sprint running. <RouterLink :to="`${work}/backlog`" class="text-river underline">Plan one in the backlog</RouterLink> to get a burndown and velocity.</p>
        </div>
      </section>
    </div>

    <!-- modules -->
    <section v-if="modules.length" class="panel min-w-0" aria-labelledby="ov-modules">
      <div class="panel-head"><h3 id="ov-modules" class="font-medium">Modules</h3><RouterLink :to="`${work}/modules`" class="text-xs text-river hover:underline">Plan modules & epics →</RouterLink></div>
      <ul class="grid grid-cols-1 divide-y divide-ink/5">
        <li v-for="{ m, r } in modules" :key="m.id" class="min-w-0">
          <RouterLink :to="ws.pathOf(m)" class="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 px-5 py-3 text-sm hover:bg-panel/40 sm:grid-cols-[minmax(0,1fr)_minmax(8rem,14rem)_auto]">
            <span class="flex min-w-0 items-center gap-2">
              <span class="h-2.5 w-2.5 shrink-0 rounded-sm" :style="{ background: swatch(m.id) }" aria-hidden="true" />
              <TypeIcon type="module" />
              <span class="truncate" :title="m.title">{{ m.title }}</span>
              <span v-if="r.blocked" class="shrink-0 text-[11px] text-rust">{{ r.blocked }} blocked</span>
            </span>
            <span class="col-span-2 h-1.5 overflow-hidden rounded-full bg-ink/10 sm:col-span-1 sm:row-start-1 sm:col-start-2"><span class="block h-full rounded-full bg-moss" :style="{ width: `${r.percent}%` }" /></span>
            <span class="readout row-start-1 text-right text-xs whitespace-nowrap text-ink/60 sm:col-start-3">{{ r.done }}/{{ r.total }} · {{ r.percent }}%</span>
          </RouterLink>
        </li>
      </ul>
    </section>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <section class="panel min-w-0">
        <div class="panel-head"><h3 class="font-medium">Next milestones</h3><RouterLink :to="`${work}/timeline`" class="text-xs text-river hover:underline">Timeline →</RouterLink></div>
        <ul class="panel-body grid grid-cols-1 gap-3">
          <li v-if="!nextMilestones.length" class="text-sm text-ink/55">No open milestones.</li>
          <li v-for="m in nextMilestones" :key="m.id" class="flex min-w-0 items-start gap-3 text-sm">
            <span class="mt-0.5 shrink-0 text-flag" aria-hidden="true">◆</span>
            <span class="line-clamp-2 min-w-0 flex-1 break-words" :title="m.title">{{ m.title }}</span>
            <span class="readout mt-0.5 shrink-0 text-xs whitespace-nowrap" :class="m.due_date < today ? 'text-rust' : 'text-ink/55'">{{ dateLabel(m.due_date) }}</span>
          </li>
        </ul>
      </section>
      <section class="panel min-w-0">
        <div class="panel-head"><h3 class="font-medium">Upcoming meetings</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Meetings')">All →</button></div>
        <ul class="panel-body grid grid-cols-1 gap-3">
          <li v-if="!nextMeetings.length" class="text-sm text-ink/55">Nothing scheduled.</li>
          <li v-for="m in nextMeetings" :key="m.id" class="min-w-0">
            <button class="block w-full min-w-0 text-left text-sm hover:text-river" @click="emit('go', 'Meetings', m.id)">
              <span class="line-clamp-2 font-medium break-words" :title="m.title">{{ m.title }}</span><span class="text-xs text-ink/55">{{ dateTimeLabel(m.start) }}</span>
            </button>
          </li>
        </ul>
      </section>
      <section class="panel min-w-0">
        <div class="panel-head"><h3 class="font-medium">Recently updated</h3><RouterLink :to="`${work}/summary`" class="text-xs text-river hover:underline">Activity →</RouterLink></div>
        <ul class="panel-body grid grid-cols-1 gap-3">
          <li v-if="!recent.length" class="text-sm text-ink/55">Issues, notes, documents and meetings show up here.</li>
          <li v-for="r in recent" :key="`${r.kind}${r.id}`" class="grid min-w-0 grid-cols-[4.25rem_minmax(0,1fr)_auto] items-baseline gap-x-3 text-sm">
            <span class="truncate font-mono text-[10px] text-ink/45 uppercase" :title="r.kind">{{ r.label }}</span>
            <button class="min-w-0 truncate text-left hover:text-river" :title="r.title" @click="openRecent(r)">{{ r.title }}</button>
            <span class="text-[11px] whitespace-nowrap text-ink/50">{{ since(r.at) }}</span>
            <span v-if="r.who || r.what" class="col-start-2 col-end-4 truncate text-[11px] text-ink/50">{{ [r.who, r.what].filter(Boolean).join(' · ') }}</span>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="links.length" class="panel min-w-0">
      <div class="panel-head"><h3 class="font-medium">Quick links</h3><button class="text-xs text-river hover:underline" @click="emit('go', 'Hub')">Manage →</button></div>
      <div class="panel-body flex flex-wrap gap-2">
        <a v-for="l in links" :key="l.id" :href="l.url" target="_blank" rel="noopener noreferrer" class="flex max-w-full min-w-0 items-center gap-2 rounded-full border border-ink/15 px-3 py-1.5 text-sm hover:border-ink/30 hover:bg-panel">
          <span class="shrink-0 font-mono text-[10px] text-ink/50 uppercase">{{ linkLabel(l.kind) }}</span><span class="truncate">{{ l.title }}</span> ↗
        </a>
      </div>
    </section>
  </div>
</template>
