<script setup lang="ts">
/** Delivery workspace (/app/projects/:id/work/…): Jira-style scrum views over one project. Everything here writes to
 *  the same API the project profile reads, so its overview, timeline and progress update with it. */
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { pageTitle } from '@/components/app/ui/crumb'
import LoadError from '@/components/app/org/LoadError.vue'
import { createWorkspace } from '@/components/app/pm/work/workspace'
import IssuePanel from '@/components/app/pm/work/IssuePanel.vue'
import CreateIssue from '@/components/app/pm/work/CreateIssue.vue'
import SprintDialogs from '@/components/app/pm/work/SprintDialogs.vue'
import { rollup, swatch } from '@/components/app/pm/work/meta'
import { dayNum, todayNPT } from '@/components/app/pm/pm'

const route = useRoute()
const ws = createWorkspace(() => String(route.params.id))

const VIEWS = [
  { id: 'summary', label: 'Summary', icon: 'M3 3h4v4H3zM9 3h4v4H9zM3 9h4v4H3zM9 9h4v4H9z' },
  { id: 'backlog', label: 'Backlog', icon: 'M3 4h10M3 8h10M3 12h6' },
  { id: 'board', label: 'Board', icon: 'M2.5 3h3v10h-3zM6.5 3h3v7h-3zM10.5 3h3v5h-3z' },
  { id: 'list', label: 'List', icon: 'M5.5 4h8M5.5 8h8M5.5 12h8M2.5 4h.5M2.5 8h.5M2.5 12h.5' },
  { id: 'modules', label: 'Modules & epics', icon: 'M3 5.5 8 3l5 2.5L8 8 3 5.5Zm0 3L8 11l5-2.5M3 11.5 8 14l5-2.5' },
  { id: 'timeline', label: 'Timeline', icon: 'M3 4.5h6M5 8h7M3 11.5h5' },
  { id: 'reports', label: 'Reports', icon: 'M3 13V9M6.5 13V6M10 13V8M13.5 13V3' },
] as const
const view = computed(() => String(route.meta.view || 'board'))
const current = computed(() => VIEWS.find((v) => v.id === view.value || (view.value === 'item' && v.id === 'modules')))
const profile = computed(() => `/app/projects/${route.params.id}`)
const sprintLeft = computed(() => (ws.activeSprint ? Math.max(dayNum(ws.activeSprint.end_date) - dayNum(todayNPT()), 0) : 0))

watch(
  () => [ws.project?.name, view.value] as const,
  ([name, v]) => {
    if (name && v !== 'item') pageTitle.value = `${current.value?.label} · ${name}`
  },
  { immediate: true },
)
watch(
  () => route.params.id,
  (id, old) => id && id !== old && ws.load(true),
)

/** Jira's "C" opens Create (managers), unless you're typing or a dialog is open. */
function onKey(e: KeyboardEvent) {
  if (e.key !== 'c' || e.ctrlKey || e.metaKey || e.altKey || !ws.canManage) return
  const el = e.target as HTMLElement
  if (el.closest('input, textarea, select, [contenteditable="true"]') || document.querySelector('[role="dialog"]')) return
  e.preventDefault()
  ws.openCreate()
}
onMounted(() => {
  ws.load(true)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[14.5rem_minmax(0,1fr)]">
    <!-- project sidebar -->
    <aside class="min-w-0 lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:self-start lg:overflow-y-auto" aria-label="Project navigation">
      <RouterLink :to="profile" class="mb-4 flex min-w-0 items-center gap-3 rounded-lg p-1.5 hover:bg-panel/70">
        <span class="grid grid-cols-1 h-10 w-10 shrink-0 place-items-center rounded-lg font-mono text-xs font-semibold text-on-accent" :style="{ background: ws.project ? swatch(ws.project.id + 3) : 'var(--color-river)' }" aria-hidden="true">
          {{ (ws.project?.key || '··').slice(0, 3) }}
        </span>
        <span class="min-w-0">
          <span class="block truncate text-sm font-semibold">{{ ws.project?.name || 'Loading…' }}</span>
          <span class="block text-xs text-ink/55">Delivery workspace</span>
        </span>
      </RouterLink>
      <nav aria-label="Workspace views">
        <ul class="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
          <li v-for="v in VIEWS" :key="v.id" class="shrink-0">
            <RouterLink
              :to="{ path: `${ws.base}/${v.id}` }"
              class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm whitespace-nowrap transition-colors"
              :class="current?.id === v.id ? 'bg-flag/10 font-medium text-flag' : 'text-ink/70 hover:bg-panel hover:text-ink'"
              :aria-current="current?.id === v.id ? 'page' : undefined"
            >
              <svg viewBox="0 0 16 16" class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="v.icon" /></svg>
              {{ v.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>
      <div v-if="ws.modules.length" class="mt-5 hidden lg:block">
        <p class="px-2.5 pb-1.5 font-mono text-[10px] tracking-[0.12em] text-ink/50 uppercase">Modules</p>
        <ul class="grid grid-cols-1 gap-0.5">
          <li v-for="m in ws.modules" :key="m.id">
            <RouterLink
              :to="ws.pathOf(m)"
              class="flex min-w-0 items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-ink/70 hover:bg-panel hover:text-ink"
              active-class="bg-panel font-medium text-ink"
            >
              <span class="h-2 w-2 shrink-0 rounded-sm" :style="{ background: swatch(m.id) }" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate">{{ m.title }}</span>
              <span class="font-mono text-[10px] text-ink/45">{{ rollup(m.id, ws.children).percent }}%</span>
            </RouterLink>
          </li>
        </ul>
      </div>
      <div class="mt-5 hidden border-t border-dashed border-ink/15 pt-4 lg:block">
        <p class="px-2.5 pb-1.5 font-mono text-[10px] tracking-[0.12em] text-ink/50 uppercase">Project</p>
        <ul class="grid grid-cols-1 gap-0.5 text-sm">
          <li v-for="l in [{ label: 'Overview', tab: '' }, { label: 'Notes', tab: 'Notes' }, { label: 'Docs', tab: 'Docs' }, { label: 'Meetings', tab: 'Meetings' }, { label: 'Links & milestones', tab: 'Hub' }]" :key="l.label">
            <RouterLink :to="{ path: profile, query: l.tab ? { tab: l.tab } : {} }" class="block rounded-md px-2.5 py-1.5 text-ink/70 hover:bg-panel hover:text-ink">{{ l.label }}</RouterLink>
          </li>
          <li v-if="ws.canManage"><RouterLink :to="{ path: profile, query: { tab: 'Settings' } }" class="block rounded-md px-2.5 py-1.5 text-ink/70 hover:bg-panel hover:text-ink">Project settings</RouterLink></li>
        </ul>
      </div>
    </aside>

    <!-- view -->
    <section class="min-w-0">
      <div v-if="view !== 'item'" class="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-0">
          <h1 class="font-display text-[26px] leading-tight font-medium tracking-tight">
            {{ view === 'board' && ws.activeSprint ? `${ws.project?.key} · ${ws.activeSprint.name}` : current?.label }}
          </h1>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <RouterLink v-if="ws.activeSprint && view !== 'board'" :to="`${ws.base}/board`" class="hidden items-center gap-2 rounded-full border border-ink/15 px-3 py-1.5 text-xs hover:bg-panel sm:flex">
            <span class="h-1.5 w-1.5 rounded-full bg-sky" aria-hidden="true" />{{ ws.activeSprint.name }} · {{ sprintLeft }}d left
          </RouterLink>
          <button v-if="ws.canManage" type="button" class="btn-primary" title="Create issue (C)" @click="ws.openCreate()">
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            Create
          </button>
        </div>
      </div>

      <div v-if="ws.loading" class="grid grid-cols-1 gap-3" aria-busy="true" aria-label="Loading workspace">
        <div class="h-10 w-1/2 rounded-lg bg-panel/70 motion-safe:animate-pulse" />
        <div class="h-[60vh] rounded-xl bg-panel/70 motion-safe:animate-pulse" />
      </div>
      <LoadError v-else-if="ws.error" :message="ws.error" @retry="ws.load(true)" />
      <RouterView v-else-if="ws.project" />
    </section>

    <IssuePanel />
    <CreateIssue />
    <SprintDialogs />
  </div>
</template>
