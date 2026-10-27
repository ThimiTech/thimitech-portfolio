<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import { confirmDialog } from '../ui/confirm'
import Modal from '../ui/Modal.vue'
import StatusPill from '../ui/StatusPill.vue'
import { dateLabel, dayNum, errorMessage, todayNPT, ymdOf, type Project, type Sprint, type Task } from './pm'
const props = defineProps<{ project: Project; tasks: Task[]; sprints: Sprint[] }>()
const emit = defineEmits<{ changed: []; select: [task: Task] }>()

const busy = ref(false)
const points = (ts: Task[]) => ts.reduce((s, t) => s + (t.estimate ?? 0), 0)
const active = computed(() => props.sprints.find((s) => s.status === 'active') || null)
const planned = computed(() => props.sprints.filter((s) => s.status === 'planned'))
const completed = computed(() => props.sprints.filter((s) => s.status === 'completed'))
const backlog = computed(() => props.tasks.filter((t) => !t.sprint && t.status !== 'done'))
const inSprint = (s: Sprint) => props.tasks.filter((t) => t.sprint === s.id)
const lanes = computed(() => [...(active.value ? [active.value] : []), ...planned.value])

async function run(action: () => Promise<unknown>, ok?: string) {
  busy.value = true
  try {
    await action()
    if (ok) toast.success(ok)
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
const assign = (task: Task, sprint: number | null) => run(() => api.patch(`pm/tasks/${task.id}/`, { sprint }))

// drag between backlog and sprint lanes
const dragging = ref<number | null>(null)
const over = ref<string | null>(null)
function drop(sprint: number | null) {
  const task = props.tasks.find((t) => t.id === dragging.value)
  over.value = dragging.value = null
  if (task && props.project.can_manage && task.sprint !== sprint) assign(task, sprint)
}

// new sprint
const modal = ref(false)
const form = reactive({ name: '', goal: '', start_date: '', end_date: '' })
function openNew() {
  const last = props.sprints[props.sprints.length - 1]
  const start = last ? Math.max(dayNum(last.end_date) + 1, dayNum(todayNPT())) : dayNum(todayNPT())
  Object.assign(form, { name: `Sprint ${props.sprints.length + 1}`, goal: '', start_date: ymdOf(start), end_date: ymdOf(start + 13) })
  modal.value = true
}
const create = () =>
  run(async () => {
    await api.post('pm/sprints/', { ...form, project: props.project.id })
    modal.value = false
  }, 'Sprint planned.')
const start = (s: Sprint) => run(() => api.post(`pm/sprints/${s.id}/start/`), `${s.name} started.`)
async function remove(s: Sprint) {
  if (await confirmDialog({ title: `Delete ${s.name}?`, body: 'Its tasks return to the backlog.', confirmLabel: 'Delete sprint', danger: true }))
    run(() => api.delete(`pm/sprints/${s.id}/`))
}

// complete
const completing = ref(false)
const carryTo = ref<number | null>(null)
const unfinished = computed(() => (active.value ? inSprint(active.value).filter((t) => t.status !== 'done') : []))
const finish = () =>
  run(async () => {
    const { data } = await api.post(`pm/sprints/${active.value!.id}/complete/`, { carry_to: carryTo.value })
    completing.value = false
    toast.success(`${active.value!.name} completed · ${data.carried} task${data.carried === 1 ? '' : 's'} carried over.`)
  })

// burndown (story points; falls back to task count when nothing is estimated)
const nptDay = (iso: string) => dayNum(new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kathmandu' }).format(new Date(iso)))
const W = 600
const H = 200
const burndown = computed(() => {
  const s = active.value
  if (!s) return null
  const ts = inSprint(s)
  const weight = points(ts) ? (t: Task) => t.estimate ?? 0 : () => 1
  const total = ts.reduce((a, t) => a + weight(t), 0)
  const d0 = dayNum(s.start_date)
  const days = Math.max(dayNum(s.end_date) - d0, 1)
  const now = Math.min(dayNum(todayNPT()), d0 + days)
  const X = (d: number) => ((d - d0) / days) * W
  const Y = (v: number) => H - (total ? (v / total) * H : 0)
  const actual: string[] = []
  for (let d = d0; d <= now; d++) {
    const left = total - ts.filter((t) => t.completed_at && nptDay(t.completed_at) <= d).reduce((a, t) => a + weight(t), 0)
    actual.push(`${actual.length ? 'L' : 'M'}${X(d).toFixed(1)} ${Y(left).toFixed(1)}`)
  }
  const remaining = total - ts.filter((t) => t.status === 'done').reduce((a, t) => a + weight(t), 0)
  return {
    total,
    remaining,
    unit: points(ts) ? 'pts' : 'tasks',
    ideal: `M0 ${Y(total)} L${W} ${H}`,
    actual: actual.join(' '),
    today: now >= d0 ? X(now) : null,
    daysLeft: Math.max(dayNum(s.end_date) - dayNum(todayNPT()), 0),
    pct: total ? Math.round(((total - remaining) / total) * 100) : 0,
  }
})
const velocity = computed(() => {
  const rows = completed.value.slice(-8).map((s) => ({ s, done: points(inSprint(s).filter((t) => t.status === 'done')) }))
  const max = Math.max(...rows.map((r) => r.done), 1)
  const avg = rows.length ? Math.round(rows.reduce((a, r) => a + r.done, 0) / rows.length) : 0
  return { rows, max, avg }
})
</script>
<template>
  <div class="grid gap-6">
    <!-- active sprint -->
    <section class="panel overflow-hidden">
      <div class="panel-head flex-wrap">
        <div class="min-w-0">
          <p class="ledger-label">Current sprint</p>
          <h2 class="mt-1 font-display text-xl font-medium">{{ active?.name || 'No sprint running' }}</h2>
        </div>
        <div v-if="project.can_manage" class="flex gap-2">
          <button v-if="active" class="btn-ink btn-sm" :disabled="busy" @click="(carryTo = planned[0]?.id ?? null), (completing = true)">Complete sprint</button>
          <button class="btn-ghost btn-sm" :disabled="busy" @click="openNew">Plan a sprint</button>
        </div>
      </div>
      <div v-if="active && burndown" class="grid gap-6 p-5 lg:grid-cols-[1fr_1.4fr]">
        <div>
          <p v-if="active.goal" class="text-sm leading-relaxed"><span class="ledger-label mr-2">Goal</span>{{ active.goal }}</p>
          <dl class="mt-5 grid grid-cols-3 gap-3">
            <div><dt class="ledger-label">Days left</dt><dd class="readout mt-1 text-2xl">{{ burndown.daysLeft }}</dd></div>
            <div><dt class="ledger-label">Remaining</dt><dd class="readout mt-1 text-2xl">{{ burndown.remaining }}<span class="text-xs text-ink/50"> {{ burndown.unit }}</span></dd></div>
            <div><dt class="ledger-label">Complete</dt><dd class="readout mt-1 text-2xl">{{ burndown.pct }}%</dd></div>
          </dl>
          <p class="mt-4 text-xs text-ink/60">{{ dateLabel(active.start_date) }} → {{ dateLabel(active.end_date) }}</p>
        </div>
        <figure>
          <svg :viewBox="`-8 -8 ${W + 16} ${H + 24}`" class="h-auto w-full" role="img" :aria-label="`Burndown: ${burndown.remaining} of ${burndown.total} ${burndown.unit} remaining`">
            <line v-for="i in 4" :key="i" x1="0" :x2="W" :y1="(H / 4) * i" :y2="(H / 4) * i" stroke="var(--color-ink)" stroke-opacity=".07" />
            <path :d="burndown.ideal" stroke="var(--color-ink)" stroke-opacity=".3" stroke-dasharray="5 5" fill="none" />
            <path :d="burndown.actual" stroke="var(--color-flag)" stroke-width="2.5" fill="none" stroke-linejoin="round" />
            <line v-if="burndown.today !== null" :x1="burndown.today" :x2="burndown.today" y1="0" :y2="H" stroke="var(--color-flag)" stroke-opacity=".35" />
            <text x="0" :y="H + 14" class="fill-ink/50 font-mono" font-size="10">{{ dateLabel(active.start_date) }}</text>
            <text :x="W" :y="H + 14" text-anchor="end" class="fill-ink/50 font-mono" font-size="10">{{ dateLabel(active.end_date) }}</text>
          </svg>
          <figcaption class="mt-1 flex gap-4 text-[11px] text-ink/60">
            <span class="flex items-center gap-1.5"><span class="h-0.5 w-4 bg-flag" />Remaining</span>
            <span class="flex items-center gap-1.5"><span class="h-0 w-4 border-t border-dashed border-ink/40" />Ideal</span>
          </figcaption>
        </figure>
      </div>
      <p v-else class="p-5 text-sm text-ink/60">
        Plan a sprint, pull tasks in from the backlog, then start it to track a burndown.
      </p>
    </section>

    <!-- planning -->
    <div class="grid items-start gap-4 lg:grid-cols-2">
      <section
        class="panel transition-shadow"
        :class="over === 'backlog' ? 'ring-2 ring-river/50' : ''"
        @dragover.prevent="over = 'backlog'"
        @dragleave.self="over = null"
        @drop.prevent="drop(null)"
      >
        <div class="panel-head">
          <h3 class="font-medium">Backlog</h3>
          <span class="readout text-xs text-ink/60">{{ backlog.length }} · {{ points(backlog) }} pts</span>
        </div>
        <ul class="max-h-[60vh] divide-y divide-ink/5 overflow-y-auto">
          <li v-if="!backlog.length" class="p-5 text-sm text-ink/55">Backlog is clear.</li>
          <li
            v-for="t in backlog"
            :key="t.id"
            :draggable="project.can_manage"
            class="flex items-center gap-3 px-5 py-2.5"
            :class="project.can_manage ? 'cursor-grab' : ''"
            @dragstart="dragging = t.id"
            @dragend="dragging = null"
          >
            <span class="font-mono text-[10px] text-ink/50">{{ t.key }}</span>
            <button class="min-w-0 flex-1 truncate text-left text-sm hover:text-river" @click="emit('select', t)">{{ t.title }}</button>
            <span class="readout text-[11px] text-ink/50">{{ t.estimate ?? '–' }}</span>
            <label v-if="project.can_manage && lanes.length" class="shrink-0">
              <span class="sr-only">Move {{ t.key }} to sprint</span>
              <select class="input !w-28 !py-0.5 text-xs" :value="''" :disabled="busy" @change="assign(t, Number(($event.target as HTMLSelectElement).value))">
                <option value="" disabled>Add to…</option>
                <option v-for="s in lanes" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </label>
          </li>
        </ul>
      </section>
      <div class="grid gap-4">
        <section
          v-for="s in lanes"
          :key="s.id"
          class="panel transition-shadow"
          :class="over === `s${s.id}` ? 'ring-2 ring-river/50' : ''"
          @dragover.prevent="over = `s${s.id}`"
          @dragleave.self="over = null"
          @drop.prevent="drop(s.id)"
        >
          <div class="panel-head">
            <div class="min-w-0">
              <h3 class="flex items-center gap-2 font-medium">{{ s.name }} <StatusPill :status="s.status === 'active' ? 'active' : 'scheduled'" :label="s.status" /></h3>
              <p class="mt-0.5 text-xs text-ink/55">{{ dateLabel(s.start_date) }} → {{ dateLabel(s.end_date) }}</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="readout text-xs text-ink/60">{{ inSprint(s).length }} · {{ points(inSprint(s)) }} pts</span>
              <button v-if="project.can_manage && s.status === 'planned' && !active" class="btn-primary btn-sm" :disabled="busy" @click="start(s)">Start</button>
              <button v-if="project.can_manage && s.status === 'planned'" class="text-xs text-rust" :disabled="busy" @click="remove(s)">Delete</button>
            </div>
          </div>
          <ul class="divide-y divide-ink/5">
            <li v-if="!inSprint(s).length" class="p-5 text-sm text-ink/55">{{ project.can_manage ? 'Drag tasks here from the backlog.' : 'No tasks yet.' }}</li>
            <li
              v-for="t in inSprint(s)"
              :key="t.id"
              :draggable="project.can_manage"
              class="flex items-center gap-3 px-5 py-2.5"
              @dragstart="dragging = t.id"
              @dragend="dragging = null"
            >
              <span class="h-2 w-2 shrink-0 rounded-full" :class="t.status === 'done' ? 'bg-moss' : t.status === 'active' ? 'bg-flag' : t.status === 'review' ? 'bg-contour' : 'bg-ink/25'" :title="t.status" />
              <span class="font-mono text-[10px] text-ink/50">{{ t.key }}</span>
              <button class="min-w-0 flex-1 truncate text-left text-sm hover:text-river" :class="t.status === 'done' ? 'text-ink/50 line-through' : ''" @click="emit('select', t)">{{ t.title }}</button>
              <span class="truncate text-[11px] text-ink/50">{{ t.assignee_name || '' }}</span>
              <span class="readout text-[11px] text-ink/50">{{ t.estimate ?? '–' }}</span>
              <button v-if="project.can_manage && t.status !== 'done'" class="text-xs text-ink/50 hover:text-rust" :aria-label="`Return ${t.key} to backlog`" :disabled="busy" @click="assign(t, null)">✕</button>
            </li>
          </ul>
        </section>
        <p v-if="!lanes.length" class="panel p-5 text-sm text-ink/60">No sprints planned.</p>
      </div>
    </div>

    <!-- velocity -->
    <section v-if="velocity.rows.length" class="panel">
      <div class="panel-head">
        <h3 class="font-medium">Velocity</h3>
        <span class="text-xs text-ink/60">avg <strong class="readout">{{ velocity.avg }}</strong> pts / sprint</span>
      </div>
      <div class="flex h-44 items-end gap-3 p-5" role="img" :aria-label="`Velocity of the last ${velocity.rows.length} sprints, average ${velocity.avg} points`">
        <div v-for="r in velocity.rows" :key="r.s.id" class="flex flex-1 flex-col items-center gap-1.5">
          <span class="readout text-[11px]">{{ r.done }}</span>
          <div class="w-full max-w-12 rounded-t bg-moss/70" :style="{ height: `${(r.done / velocity.max) * 100}px` }" />
          <span class="max-w-full truncate text-[10px] text-ink/55">{{ r.s.name }}</span>
        </div>
      </div>
    </section>

    <Modal :open="modal" title="Plan a sprint" @close="modal = false">
      <form class="grid gap-4" @submit.prevent="create">
        <label class="field"><span class="ledger-label">Name</span><input v-model="form.name" required maxlength="120" class="input" /></label>
        <label class="field"><span class="ledger-label">Sprint goal</span><textarea v-model="form.goal" rows="2" class="input" placeholder="What should this sprint deliver?" /></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="ledger-label">Start</span><input v-model="form.start_date" type="date" required class="input" /></label>
          <label class="field"><span class="ledger-label">End</span><input v-model="form.end_date" type="date" required :min="form.start_date" class="input" /></label>
        </div>
        <button class="btn-ink justify-self-end" :disabled="busy">Plan sprint</button>
      </form>
    </Modal>
    <Modal :open="completing" :title="`Complete ${active?.name || 'sprint'}`" @close="completing = false">
      <div class="grid gap-4">
        <p class="text-sm">
          {{ unfinished.length ? `${unfinished.length} unfinished task${unfinished.length === 1 ? '' : 's'} (${points(unfinished)} pts) will move to:` : 'Every task is done. Nice work.' }}
        </p>
        <label v-if="unfinished.length" class="field">
          <span class="sr-only">Carry unfinished tasks to</span>
          <select v-model="carryTo" class="input">
            <option :value="null">The backlog</option>
            <option v-for="s in planned" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </label>
        <button class="btn-ink justify-self-end" :disabled="busy" @click="finish">Complete sprint</button>
      </div>
    </Modal>
  </div>
</template>
