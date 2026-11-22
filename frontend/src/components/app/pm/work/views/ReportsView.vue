<script setup lang="ts">
/** Burndown and sprint report for any sprint, velocity across sprints, and open work per person. */
import { computed, ref, watch } from 'vue'
import Avatar from '../../../ui/Avatar.vue'
import EmptyState from '../../../ui/EmptyState.vue'
import { dateLabel, isOverdue, todayNPT } from '../../pm'
import IssueRow from '../IssueRow.vue'
import { categoryOf } from '../meta'
import { burndown, points, velocity } from '../reports'
import { useWorkspace } from '../workspace'

const ws = useWorkspace()
const W = 600
const H = 200
const chosen = ref<number | null>(null)
const reportable = computed(() => ws.sprints.filter((s) => s.status !== 'planned').slice().reverse())
watch(
  reportable,
  (list) => {
    if (!list.some((s) => s.id === chosen.value)) chosen.value = list[0]?.id ?? null
  },
  { immediate: true },
)
const sprint = computed(() => ws.sprints.find((s) => s.id === chosen.value) || null)
const chart = computed(() => (sprint.value ? burndown(sprint.value, ws.work, todayNPT(), W, H) : null))
const inSprint = computed(() => (sprint.value ? ws.work.filter((t) => t.sprint === sprint.value!.id) : []))
const finished = computed(() => inSprint.value.filter((t) => categoryOf(t.status) === 'done'))
const unfinished = computed(() => inSprint.value.filter((t) => categoryOf(t.status) !== 'done'))
const vel = computed(() => velocity(ws.sprints, ws.work))
const workload = computed(() => {
  const open = ws.work.filter((t) => categoryOf(t.status) !== 'done')
  const rows = ws.people.map((p) => {
    const mine = open.filter((t) => t.assignee === p.id)
    return { p, n: mine.length, pts: points(mine), late: mine.filter(isOverdue).length }
  })
  const unassigned = open.filter((t) => !t.assignee).length
  return { rows: rows.sort((a, b) => b.n - a.n), max: Math.max(...rows.map((r) => r.n), unassigned, 1), unassigned }
})
</script>

<template>
  <div class="grid grid-cols-1 gap-6">
    <section class="panel min-w-0" aria-labelledby="rep-burn">
      <div class="panel-head flex-wrap">
        <h2 id="rep-burn" class="font-medium">Burndown</h2>
        <label v-if="reportable.length">
          <span class="sr-only">Sprint</span>
          <select v-model="chosen" class="input !w-auto !py-1 text-sm">
            <option v-for="s in reportable" :key="s.id" :value="s.id">{{ s.name }}{{ s.status === 'active' ? ' (active)' : '' }}</option>
          </select>
        </label>
      </div>
      <div v-if="!sprint || !chart" class="panel-body">
        <EmptyState title="No sprint to report on" hint="Start a sprint from the backlog to see its burndown here." />
      </div>
      <div v-else class="grid gap-6 p-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <figure class="min-w-0">
          <svg :viewBox="`-8 -8 ${W + 16} ${H + 26}`" class="h-auto w-full" role="img" :aria-label="`Burndown for ${sprint.name}: ${chart.remaining} of ${chart.total} ${chart.unit} remaining`">
            <line v-for="i in 4" :key="i" x1="0" :x2="W" :y1="(H / 4) * i" :y2="(H / 4) * i" stroke="var(--color-ink)" stroke-opacity=".07" />
            <path :d="chart.ideal" stroke="var(--color-ink)" stroke-opacity=".3" stroke-dasharray="5 5" fill="none" />
            <path :d="chart.actual" stroke="var(--color-flag)" stroke-width="2.5" fill="none" stroke-linejoin="round" />
            <line v-if="chart.today !== null" :x1="chart.today" :x2="chart.today" y1="0" :y2="H" stroke="var(--color-flag)" stroke-opacity=".35" />
            <text x="0" :y="H + 16" class="fill-ink/50 font-mono" font-size="11">{{ dateLabel(chart.start) }}</text>
            <text :x="W" :y="H + 16" text-anchor="end" class="fill-ink/50 font-mono" font-size="11">{{ dateLabel(chart.end) }}</text>
          </svg>
          <figcaption class="mt-1 flex gap-4 text-[11px] text-ink/60">
            <span class="flex items-center gap-1.5"><span class="h-0.5 w-4 bg-flag" />Remaining {{ chart.unit }}</span>
            <span class="flex items-center gap-1.5"><span class="h-0 w-4 border-t border-dashed border-ink/40" />Guideline</span>
          </figcaption>
        </figure>
        <dl class="grid grid-cols-3 content-start gap-4">
          <div><dt class="ledger-label">Committed</dt><dd class="readout mt-1 text-2xl">{{ chart.total }}<span class="text-xs text-ink/50"> {{ chart.unit }}</span></dd></div>
          <div><dt class="ledger-label">Remaining</dt><dd class="readout mt-1 text-2xl">{{ chart.remaining }}</dd></div>
          <div><dt class="ledger-label">Complete</dt><dd class="readout mt-1 text-2xl">{{ chart.pct }}%</dd></div>
          <p v-if="sprint.goal" class="col-span-3 text-sm break-words text-ink/70"><span class="ledger-label mr-1">Goal</span>{{ sprint.goal }}</p>
        </dl>
      </div>
    </section>

    <div v-if="sprint" class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section class="panel min-w-0" aria-labelledby="rep-done">
        <div class="panel-head"><h2 id="rep-done" class="font-medium">Completed issues</h2><span class="readout text-xs text-ink/55">{{ finished.length }} · {{ points(finished) }} pts</span></div>
        <ul class="max-h-96 divide-y divide-ink/5 overflow-y-auto">
          <li v-for="t in finished" :key="t.id" class="cursor-pointer hover:bg-panel/40"><IssueRow :task="t" /></li>
          <li v-if="!finished.length" class="p-5 text-sm text-ink/55">Nothing finished in this sprint yet.</li>
        </ul>
      </section>
      <section class="panel min-w-0" aria-labelledby="rep-open">
        <div class="panel-head"><h2 id="rep-open" class="font-medium">Not completed</h2><span class="readout text-xs text-ink/55">{{ unfinished.length }} · {{ points(unfinished) }} pts</span></div>
        <ul class="max-h-96 divide-y divide-ink/5 overflow-y-auto">
          <li v-for="t in unfinished" :key="t.id" class="cursor-pointer hover:bg-panel/40"><IssueRow :task="t" /></li>
          <li v-if="!unfinished.length" class="p-5 text-sm text-ink/55">{{ sprint.status === 'completed' ? 'Open issues were moved out when the sprint closed.' : 'Everything is done.' }}</li>
        </ul>
      </section>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section class="panel min-w-0" aria-labelledby="rep-vel">
        <div class="panel-head"><h2 id="rep-vel" class="font-medium">Velocity</h2><span class="text-xs text-ink/60">avg <strong class="readout">{{ vel.avg }}</strong> pts / sprint</span></div>
        <div v-if="vel.rows.length" class="flex h-52 items-end gap-4 overflow-x-auto p-5" role="img" :aria-label="`Velocity of the last ${vel.rows.length} sprints, average ${vel.avg} points`">
          <div v-for="r in vel.rows" :key="r.sprint.id" class="flex min-w-12 flex-1 flex-col items-center gap-1.5">
            <span class="readout text-[11px]">{{ r.done }}/{{ r.committed }}</span>
            <div class="flex h-32 w-full max-w-16 items-end gap-1">
              <div class="flex-1 rounded-t bg-ink/15" :style="{ height: `${(r.committed / vel.max) * 100}%` }" :title="`Committed ${r.committed}`" />
              <div class="flex-1 rounded-t bg-moss/80" :style="{ height: `${(r.done / vel.max) * 100}%` }" :title="`Completed ${r.done}`" />
            </div>
            <span class="max-w-full truncate text-[10.5px] text-ink/55">{{ r.sprint.name }}</span>
          </div>
        </div>
        <p v-else class="panel-body text-sm text-ink/60">Complete a sprint to start tracking velocity.</p>
        <p v-if="vel.rows.length" class="flex gap-4 px-5 pb-4 text-[11px] text-ink/60">
          <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm bg-ink/15" />Committed</span>
          <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm bg-moss/80" />Completed</span>
        </p>
      </section>
      <section class="panel min-w-0" aria-labelledby="rep-load">
        <div class="panel-head"><h2 id="rep-load" class="font-medium">Open work by person</h2></div>
        <ul class="panel-body grid grid-cols-1 gap-3">
          <li v-for="r in workload.rows" :key="r.p.id" class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto] items-center gap-3 text-sm">
            <span class="flex min-w-0 items-center gap-2"><Avatar :name="r.p.name" :size="22" /><span class="truncate">{{ r.p.name }}</span></span>
            <span class="h-2 overflow-hidden rounded-full bg-panel"><span class="block h-full rounded-full bg-river" :style="{ width: `${(r.n / workload.max) * 100}%` }" /></span>
            <span class="readout text-right text-xs text-ink/60">{{ r.n }} · {{ r.pts }}pt<span v-if="r.late" class="text-rust"> · {{ r.late }} late</span></span>
          </li>
          <li v-if="workload.unassigned" class="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto] items-center gap-3 text-sm text-ink/60">
            <span class="truncate">Unassigned</span>
            <span class="h-2 overflow-hidden rounded-full bg-panel"><span class="block h-full rounded-full bg-ink/30" :style="{ width: `${(workload.unassigned / workload.max) * 100}%` }" /></span>
            <span class="readout text-right text-xs">{{ workload.unassigned }}</span>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
