<script setup lang="ts">
/** The project at a glance: last-7-days counters, status donut, recent activity, priorities, types and modules. */
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/api'
import Avatar from '../../../ui/Avatar.vue'
import { dayNum, todayNPT, type Activity } from '../../pm'
import TypeIcon from '../TypeIcon.vue'
import PriorityIcon from '../PriorityIcon.vue'
import { CATEGORY_META, FIELD_LABEL, PRIORITIES, PRIORITY_META, TYPE_META, WORK_TYPES, ago, categoryOf, rollup, type Category } from '../meta'
import { useWorkspace } from '../workspace'

const ws = useWorkspace()
const WEEK = 7 * 86_400_000
const within = (iso?: string | null) => !!iso && Date.now() - Date.parse(iso) <= WEEK
const today = dayNum(todayNPT())
const cards = computed(() => [
  { label: 'completed', n: ws.work.filter((t) => within(t.completed_at)).length, hint: 'in the last 7 days', icon: 'M3.5 8.5l3 3 6-7' },
  { label: 'updated', n: ws.tasks.filter((t) => within(t.updated_at)).length, hint: 'in the last 7 days', icon: 'M8 3.5v4.5l3 2' },
  { label: 'created', n: ws.tasks.filter((t) => within(t.created_at)).length, hint: 'in the last 7 days', icon: 'M8 3v10M3 8h10' },
  { label: 'due soon', n: ws.work.filter((t) => t.due_date && t.status !== 'done' && dayNum(t.due_date) - today >= 0 && dayNum(t.due_date) - today <= 7).length, hint: 'in the next 7 days', icon: 'M3 5h10v8H3zM3 7.5h10M6 3v3M10 3v3' },
])
const cats = computed(() => {
  const out: Record<Category, number> = { todo: 0, progress: 0, done: 0 }
  for (const t of ws.work) out[categoryOf(t.status)]++
  return out
})
const R = 52
const C = 2 * Math.PI * R
const arcs = computed(() => {
  const total = ws.work.length || 1
  let offset = 0
  return (['done', 'progress', 'todo'] as Category[]).map((k) => {
    const len = (cats.value[k] / total) * C
    const arc = { k, len, offset }
    offset += len
    return arc
  })
})
const COLOR: Record<Category, string> = { done: 'var(--color-moss)', progress: 'var(--color-sky)', todo: 'color-mix(in srgb, var(--color-ink) 22%, transparent)' }
const priorities = computed(() => {
  const open = ws.work.filter((t) => t.status !== 'done')
  const rows = PRIORITIES.map((p) => ({ p, n: open.filter((t) => t.priority === p).length }))
  return { rows, max: Math.max(...rows.map((r) => r.n), 1) }
})
const types = computed(() => {
  const all = ws.tasks.length || 1
  return (['module', 'epic', ...WORK_TYPES] as const).map((t) => ({ t, n: ws.tasks.filter((x) => x.type === t).length })).map((r) => ({ ...r, pct: Math.round((r.n / all) * 100) }))
})

const feed = ref<Activity[]>([])
async function loadFeed() {
  if (!ws.project) return
  try {
    feed.value = (await api.get<Activity[]>('pm/activity/', { params: { project: ws.project.id } })).data
  } catch {
    feed.value = []
  }
}
onMounted(loadFeed)
watch(() => ws.tasks.map((t) => t.updated_at).join(), () => loadFeed())
const say = (a: Activity) =>
  a.field === 'created' ? `created ${a.new.toLowerCase()}` : a.field === 'description' ? 'updated the description of' : `changed ${(FIELD_LABEL[a.field] || a.field).toLowerCase()} to “${a.new || 'None'}” on`
</script>

<template>
  <div class="grid grid-cols-1 gap-5">
    <section class="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Last 7 days">
      <div v-for="c in cards" :key="c.label" class="panel flex items-center gap-3 p-4">
        <span class="grid grid-cols-1 h-10 w-10 shrink-0 place-items-center rounded-full bg-panel text-ink/70" aria-hidden="true">
          <svg viewBox="0 0 16 16" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path :d="c.icon" /></svg>
        </span>
        <div class="min-w-0">
          <p class="truncate text-sm font-medium"><span class="readout text-lg">{{ c.n }}</span> {{ c.label }}</p>
          <p class="truncate text-xs text-ink/55">{{ c.hint }}</p>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <section class="panel min-w-0" aria-labelledby="sum-status">
        <div class="panel-head"><h2 id="sum-status" class="font-medium">Status overview</h2><RouterLink :to="`${ws.base}/list`" class="text-xs text-river hover:underline">View all →</RouterLink></div>
        <div class="panel-body flex flex-wrap items-center gap-8">
          <svg viewBox="0 0 140 140" class="h-36 w-36 shrink-0 -rotate-90" role="img" :aria-label="`${cats.done} done, ${cats.progress} in progress, ${cats.todo} to do`">
            <circle cx="70" cy="70" :r="R" fill="none" stroke="var(--color-panel)" stroke-width="16" />
            <circle v-for="a in arcs" :key="a.k" cx="70" cy="70" :r="R" fill="none" :stroke="COLOR[a.k]" stroke-width="16" :stroke-dasharray="`${a.len} ${C - a.len}`" :stroke-dashoffset="-a.offset" />
            <text x="70" y="68" text-anchor="middle" transform="rotate(90 70 70)" class="fill-ink font-display" font-size="26">{{ ws.work.length }}</text>
            <text x="70" y="88" text-anchor="middle" transform="rotate(90 70 70)" class="fill-ink/55" font-size="11">issues</text>
          </svg>
          <ul class="grid grid-cols-1 gap-2 text-sm">
            <li v-for="k in (['todo', 'progress', 'done'] as Category[])" :key="k" class="flex items-center gap-2">
              <span class="h-3 w-3 rounded-sm" :style="{ background: COLOR[k] }" />{{ CATEGORY_META[k].label }}<strong class="readout ml-2">{{ cats[k] }}</strong>
            </li>
          </ul>
        </div>
      </section>

      <section class="panel min-w-0" aria-labelledby="sum-feed">
        <div class="panel-head"><h2 id="sum-feed" class="font-medium">Recent activity</h2></div>
        <ol class="max-h-80 overflow-y-auto px-5 py-3">
          <li v-if="!feed.length" class="py-3 text-sm text-ink/55">Changes to issues show up here.</li>
          <li v-for="a in feed.slice(0, 25)" :key="a.id" class="flex gap-3 py-2 text-sm">
            <Avatar :name="a.actor_name || 'Someone'" :size="26" />
            <p class="min-w-0 flex-1 leading-snug break-words">
              <span class="font-medium">{{ a.actor_name || 'Someone' }}</span> {{ say(a) }}
              <button type="button" class="text-river hover:underline" @click="ws.byId.get(a.task) ? ws.go(ws.byId.get(a.task)!) : ws.openIssue(a.task_key)">{{ a.task_key }}: {{ a.task_title }}</button>
              <span class="ml-1 text-xs text-ink/50">{{ ago(a.at) }}</span>
            </p>
          </li>
        </ol>
      </section>

      <section class="panel min-w-0" aria-labelledby="sum-prio">
        <div class="panel-head"><h2 id="sum-prio" class="font-medium">Priority breakdown</h2><span class="text-xs text-ink/55">open issues</span></div>
        <div class="flex h-48 items-end gap-6 px-6 pt-4 pb-3" role="img" :aria-label="priorities.rows.map((r) => `${PRIORITY_META[r.p]!.label} ${r.n}`).join(', ')">
          <div v-for="r in priorities.rows" :key="r.p" class="flex flex-1 flex-col items-center gap-1.5">
            <span class="readout text-xs">{{ r.n }}</span>
            <div class="w-full max-w-14 rounded-t" :style="{ height: `${(r.n / priorities.max) * 110}px`, background: PRIORITY_META[r.p]!.color, opacity: 0.8 }" />
            <span class="flex items-center gap-1 text-[11px] text-ink/60"><PriorityIcon :priority="r.p" :size="13" />{{ PRIORITY_META[r.p]!.label }}</span>
          </div>
        </div>
      </section>

      <section class="panel min-w-0" aria-labelledby="sum-types">
        <div class="panel-head"><h2 id="sum-types" class="font-medium">Types of work</h2></div>
        <ul class="panel-body grid grid-cols-1 gap-3">
          <li v-for="r in types" :key="r.t" class="grid grid-cols-[7rem_minmax(0,1fr)_3rem] items-center gap-3 text-sm">
            <span class="flex items-center gap-2"><TypeIcon :type="r.t" />{{ TYPE_META[r.t].label }}</span>
            <span class="h-2 overflow-hidden rounded-full bg-panel"><span class="block h-full rounded-full bg-river" :style="{ width: `${r.pct}%` }" /></span>
            <span class="readout text-right text-xs text-ink/60">{{ r.n }}</span>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="ws.modules.length" class="panel min-w-0" aria-labelledby="sum-mods">
      <div class="panel-head"><h2 id="sum-mods" class="font-medium">Modules</h2><RouterLink :to="`${ws.base}/modules`" class="text-xs text-river hover:underline">All modules →</RouterLink></div>
      <ul class="divide-y divide-ink/5">
        <li v-for="m in ws.modules" :key="m.id">
          <RouterLink :to="ws.pathOf(m)" class="grid grid-cols-[minmax(0,1fr)_minmax(6rem,12rem)_4rem] items-center gap-4 px-5 py-3 text-sm hover:bg-panel/40">
            <span class="flex min-w-0 items-center gap-2"><TypeIcon type="module" /><span class="truncate">{{ m.title }}</span></span>
            <span class="h-1.5 overflow-hidden rounded-full bg-ink/10"><span class="block h-full rounded-full bg-moss" :style="{ width: `${rollup(m.id, ws.children).percent}%` }" /></span>
            <span class="readout text-right text-xs text-ink/60">{{ rollup(m.id, ws.children).percent }}%</span>
          </RouterLink>
        </li>
      </ul>
    </section>
  </div>
</template>
