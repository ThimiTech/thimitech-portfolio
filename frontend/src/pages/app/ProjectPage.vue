<script setup lang="ts">
/** Project profile (/app/projects/:id): overview, knowledge (notes, docs, meetings, whiteboards), links, finance and
 *  settings. Planning and delivery (backlog, board, modules, timeline, reports) live in the delivery workspace at
 *  /app/projects/:id/work; both read the same issues, so work done there shows here. */
import { computed, onMounted, ref, watch } from 'vue'
import { pageTitle } from '@/components/app/ui/crumb'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/api'
import { toast } from '@/components/app/ui/toast'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import TabBar from '@/components/app/ui/TabBar.vue'
import StatusPill from '@/components/app/ui/StatusPill.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import { useAuth } from '@/stores/auth'
import ProjectHub from '@/components/app/pm/ProjectHub.vue'
import ProjectSettings from '@/components/app/pm/ProjectSettings.vue'
import LinkedFinance from '@/components/app/finance/LinkedFinance.vue'
import ProjectOverview from '@/components/app/pm/ProjectOverview.vue'
import NotesPanel from '@/components/app/pm/NotesPanel.vue'
import DocumentsPanel from '@/components/app/pm/DocumentsPanel.vue'
import MeetingsPanel from '@/components/app/pm/MeetingsPanel.vue'
import WhiteboardPanel from '@/components/app/pm/WhiteboardPanel.vue'
import ProfileEditor from '@/components/app/pm/ProfileEditor.vue'
import IssuePanel from '@/components/app/pm/work/IssuePanel.vue'
import CreateIssue from '@/components/app/pm/work/CreateIssue.vue'
import { createWorkspace } from '@/components/app/pm/work/workspace'
import {
  HEALTH,
  isOverdue,
  resolveLink,
  type Doc,
  type Meeting,
  type Note,
  type ProjectLink,
  type Task,
  type Whiteboard,
} from '@/components/app/pm/pm'

const route = useRoute()
const router = useRouter()
const { hasRole } = useAuth()
const ws = createWorkspace(() => String(route.params.id))
const links = ref<ProjectLink[]>([])
const notes = ref<Note[]>([])
const docs = ref<Doc[]>([])
const meetings = ref<Meeting[]>([])
const whiteboards = ref<Whiteboard[]>([])
const extraError = ref(false)
const focus = ref<Record<string, number | null>>({})
const project = computed(() => ws.project)
const work = computed(() => `/app/projects/${route.params.id}/work`)

watch(() => project.value?.name, (name) => (pageTitle.value = name ?? ''), { immediate: true })

/** The delivery tabs moved to the workspace: old links (?tab=Board …) land on the matching view. */
const MOVED: Record<string, string> = { Plan: 'list', Board: 'board', Sprints: 'backlog', Timeline: 'timeline' }
const TABS = ['Overview', 'Notes', 'Docs', 'Meetings', 'Whiteboard', 'Hub']
const views = computed(() =>
  [...TABS, ...(hasRole('finance') ? ['Finance'] : []), ...(project.value?.can_manage ? ['Profile', 'Settings'] : [])].map((id) => ({
    id,
    label: id === 'Hub' ? 'Links & milestones' : id === 'Profile' ? 'Public profile' : id,
    count: id === 'Meetings' ? upcomingMeetings.value || undefined : undefined,
  })),
)
const tab = computed({
  get: () => {
    const t = String(route.query.tab || 'Overview')
    return views.value.some((v) => v.id === t) ? t : 'Overview'
  },
  set: (t: string) => {
    focus.value = pendingFocus || {} // a plain tab switch opens nothing in particular
    pendingFocus = null
    router.replace({ query: { ...route.query, tab: t === 'Overview' ? undefined : t } })
  },
})
let pendingFocus: Record<string, number> | null = null
watch(
  () => route.query.tab,
  (t) => {
    if (typeof t === 'string' && MOVED[t]) {
      const query = { ...route.query }
      delete query.tab
      router.replace({ path: `${work.value}/${MOVED[t]}`, query })
    }
  },
  { immediate: true },
)
const overdue = computed(() => ws.work.filter(isOverdue).length)
const upcomingMeetings = computed(
  () => meetings.value.filter((m) => m.status === 'scheduled' && Date.parse(m.end) >= Date.now()).length,
)

const LISTS = {
  links: ['pm/links/', links],
  notes: ['pm/notes/', notes],
  docs: ['pm/documents/', docs],
  meetings: ['pm/meetings/', meetings],
  whiteboards: ['pm/whiteboards/', whiteboards],
} as const
type ListKey = keyof typeof LISTS
async function refresh(...keys: ListKey[]) {
  const id = String(route.params.id)
  await Promise.all(
    keys.map(async (k) => {
      const [url, target] = LISTS[k]
      ;(target as { value: unknown }).value = (await api.get(url, { params: { project: id } })).data
    }),
  )
}
async function load(initial = false) {
  extraError.value = false
  await Promise.all([
    ws.load(initial),
    refresh(...(Object.keys(LISTS) as ListKey[])).catch(() => (extraError.value = true)),
  ])
}

const select = (task: Task) => ws.go(task)
function go(t: string, id?: number) {
  if (MOVED[t]) return void router.push(`${work.value}/${MOVED[t]}`)
  pendingFocus = id ? { [t]: id } : null
  tab.value = t
}
function openLink(target: string) {
  const node = resolveLink(target, notes.value, docs.value, ws.tasks, meetings.value)
  if (node.kind === 'note' || node.kind === 'ghost') {
    if (node.kind === 'ghost') return toast.error(`“${target}” isn’t written yet — create it from the Notes tab.`)
    go('Notes', node.ref!)
  } else if (node.kind === 'doc') go('Docs', node.ref!)
  else if (node.kind === 'meeting') go('Meetings', node.ref!)
  else select(ws.byId.get(node.ref!)!)
}
function upsertNote(n: Note) {
  const i = notes.value.findIndex((x) => x.id === n.id)
  if (i >= 0) notes.value.splice(i, 1, n)
  else notes.value.push(n)
  notes.value.sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.title.localeCompare(b.title))
}
watch(
  () => route.params.id,
  (id, old) => id && id !== old && load(true),
)
onMounted(() => load(true))
</script>
<template>
  <div>
    <RouterLink to="/app/projects" class="mb-4 inline-flex items-center gap-1 text-sm text-ink/60 hover:text-ink"
      >← All projects</RouterLink
    >
    <div v-if="ws.loading" class="grid gap-4" aria-busy="true" aria-label="Loading project">
      <div class="h-16 w-2/3 rounded-lg bg-panel/70 motion-safe:animate-pulse" />
      <div class="h-80 rounded-xl bg-panel/70 motion-safe:animate-pulse" />
    </div>
    <LoadError v-else-if="ws.error" :message="ws.error" @retry="load(true)" />
    <template v-else-if="project">
      <PageHeader :eyebrow="`Delivery · ${project.key}`" :title="project.name" :description="project.tagline">
        <template #actions>
          <StatusPill v-if="project.archived" status="neutral" label="Archived" />
          <StatusPill :status="HEALTH[project.health].pill" :label="HEALTH[project.health].label" />
          <a
            v-if="project.visibility === 'public' && project.slug"
            :href="`/work/${project.slug}`"
            target="_blank"
            rel="noopener"
            class="btn-ghost btn-sm"
            >Public page ↗</a
          >
          <RouterLink :to="`${work}/backlog`" class="btn-ghost">Backlog</RouterLink>
          <RouterLink :to="`${work}/board`" class="btn-primary">
            <svg viewBox="0 0 16 16" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 3h3v10h-3zM6.5 3h3v7h-3zM10.5 3h3v5h-3z" /></svg>
            Open board
            <span v-if="overdue" class="readout rounded-full bg-on-accent/20 px-1.5 text-[10.5px]" :aria-label="`${overdue} overdue`">{{ overdue }}</span>
          </RouterLink>
        </template>
      </PageHeader>
      <TabBar v-model="tab" :tabs="views" label="Project views" id-prefix="prj" class="mb-6" />
      <p v-if="extraError" role="alert" class="mb-4 text-sm text-rust">
        Some project content could not be loaded. <button type="button" class="underline" @click="load()">Retry</button>
      </p>
      <div :id="`prj-panel-${tab}`" role="tabpanel" :aria-labelledby="`prj-tab-${tab}`">
        <ProjectOverview
          v-if="tab === 'Overview'"
          :project="project"
          :tasks="ws.work"
          :sprints="ws.sprints"
          :milestones="ws.milestones"
          :meetings="meetings"
          :notes="notes"
          :docs="docs"
          :links="links"
          @go="go"
          @select="select"
          @saved="ws.refreshProject()"
        />
        <NotesPanel
          v-else-if="tab === 'Notes'"
          :project="project"
          :notes="notes"
          :docs="docs"
          :tasks="ws.tasks"
          :meetings="meetings"
          :open-id="focus.Notes"
          @upsert="upsertNote"
          @removed="(id) => (notes = notes.filter((n) => n.id !== id))"
          @open-doc="(id) => go('Docs', id)"
          @open-task="select"
          @open-meeting="(id) => go('Meetings', id)"
        />
        <DocumentsPanel v-else-if="tab === 'Docs'" :project="project" :docs="docs" :open-id="focus.Docs" @changed="refresh('docs')" @wikilink="openLink" />
        <MeetingsPanel
          v-else-if="tab === 'Meetings'"
          :project="project"
          :meetings="meetings"
          :open-id="focus.Meetings"
          @changed="refresh('meetings'), ws.refreshTasks()"
          @wikilink="openLink"
        />
        <WhiteboardPanel v-else-if="tab === 'Whiteboard'" :project="project" :boards="whiteboards" @changed="refresh('whiteboards')" />
        <ProjectHub v-else-if="tab === 'Hub'" :project="project" :milestones="ws.milestones" :links="links" @saved="refresh('links'), ws.refreshMilestones()" />
        <LinkedFinance v-else-if="tab === 'Finance' && hasRole('finance')" :key="project.id" :project="project.id" />
        <ProfileEditor v-else-if="tab === 'Profile' && project.can_manage" :project="project" :docs="docs" :links="links" @saved="ws.refreshProject()" />
        <ProjectSettings v-else-if="tab === 'Settings' && project.can_manage" :project="project" @saved="load()" />
      </div>
      <IssuePanel />
      <CreateIssue />
    </template>
  </div>
</template>
