<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/api'
import { toast } from '@/components/app/ui/toast'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import TabBar from '@/components/app/ui/TabBar.vue'
import StatusPill from '@/components/app/ui/StatusPill.vue'
import EmptyState from '@/components/app/ui/EmptyState.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import { useAuth } from '@/stores/auth'
import TaskBoard from '@/components/app/pm/TaskBoard.vue'
import TaskTimeline from '@/components/app/pm/TaskTimeline.vue'
import TaskDialog from '@/components/app/pm/TaskDialog.vue'
import ProjectHub from '@/components/app/pm/ProjectHub.vue'
import ProjectSettings from '@/components/app/pm/ProjectSettings.vue'
import ProjectOverview from '@/components/app/pm/ProjectOverview.vue'
import SprintsPanel from '@/components/app/pm/SprintsPanel.vue'
import NotesPanel from '@/components/app/pm/NotesPanel.vue'
import DocumentsPanel from '@/components/app/pm/DocumentsPanel.vue'
import MeetingsPanel from '@/components/app/pm/MeetingsPanel.vue'
import WhiteboardPanel from '@/components/app/pm/WhiteboardPanel.vue'
import ProfileEditor from '@/components/app/pm/ProfileEditor.vue'
import {
  errorMessage,
  HEALTH,
  isOverdue,
  resolveLink,
  type Doc,
  type Meeting,
  type Milestone,
  type Note,
  type Project,
  type ProjectLink,
  type Sprint,
  type Task,
  type Whiteboard,
} from '@/components/app/pm/pm'

const route = useRoute()
const router = useRouter()
const { user } = useAuth()
const project = ref<Project | null>(null)
const tasks = ref<Task[]>([])
const milestones = ref<Milestone[]>([])
const links = ref<ProjectLink[]>([])
const sprints = ref<Sprint[]>([])
const notes = ref<Note[]>([])
const docs = ref<Doc[]>([])
const meetings = ref<Meeting[]>([])
const whiteboards = ref<Whiteboard[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const boardId = ref(0)
const search = ref('')
const onlyMine = ref(false)
const sprintOnly = ref(false)
const dialog = ref(false)
const selected = ref<Task | null>(null)
const newColumn = ref(0)
const focus = ref<Record<string, number | null>>({})

const TABS = ['Overview', 'Board', 'Sprints', 'Timeline', 'Notes', 'Docs', 'Meetings', 'Whiteboard', 'Hub']
const views = computed(() =>
  [...TABS, ...(project.value?.can_manage ? ['Profile', 'Settings'] : [])].map((id) => ({
    id,
    label: id === 'Hub' ? 'Links & milestones' : id === 'Profile' ? 'Public profile' : id,
    count:
      id === 'Board' ? overdue.value || undefined : id === 'Meetings' ? upcomingMeetings.value || undefined : undefined,
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
const board = computed(
  () => project.value?.boards.find((b) => b.id === boardId.value) || project.value?.boards[0],
)
const activeSprint = computed(() => sprints.value.find((s) => s.status === 'active'))
const filtered = computed(() =>
  tasks.value.filter(
    (t) =>
      t.board === board.value?.id &&
      (!onlyMine.value || t.assignee === user.value?.id) &&
      (!sprintOnly.value || t.sprint === activeSprint.value?.id) &&
      `${t.title} ${t.key} ${t.labels.join(' ')}`
        .toLowerCase()
        .includes(search.value.toLowerCase()),
  ),
)
const overdue = computed(() => tasks.value.filter(isOverdue).length)
const upcomingMeetings = computed(
  () => meetings.value.filter((m) => m.status === 'scheduled' && Date.parse(m.end) >= Date.now()).length,
)

const LISTS = {
  tasks: ['pm/tasks/', tasks],
  milestones: ['pm/milestones/', milestones],
  links: ['pm/links/', links],
  sprints: ['pm/sprints/', sprints],
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
  if (initial) loading.value = true
  error.value = ''
  try {
    const [p] = await Promise.all([
      api.get<Project>(`pm/projects/${route.params.id}/`),
      refresh(...(Object.keys(LISTS) as ListKey[])),
    ])
    project.value = p.data
    if (!p.data.boards.some((b) => b.id === boardId.value)) boardId.value = p.data.boards[0]?.id || 0
  } catch {
    error.value = 'Could not load this project. It may be unavailable or you may no longer have access.'
  } finally {
    loading.value = false
  }
}
async function reloadProject() {
  project.value = (await api.get<Project>(`pm/projects/${route.params.id}/`)).data
}
async function afterTaskChange() {
  await Promise.all([refresh('tasks', 'sprints'), reloadProject()])
}

function select(task: Task) {
  selected.value = task
  dialog.value = true
}
function create(column?: number) {
  selected.value = null
  newColumn.value = column || board.value?.columns[0]?.id || 0
  dialog.value = true
}
async function move(task: Task, column: number) {
  busy.value = true
  try {
    await api.patch(`pm/tasks/${task.id}/`, { column })
    await afterTaskChange()
    toast.success(`${task.key} moved.`)
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
async function reschedule(task: Task, start_date: string, due_date: string) {
  try {
    await api.patch(`pm/tasks/${task.id}/`, { start_date, due_date })
    await refresh('tasks')
    toast.success(`${task.key} rescheduled.`)
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
function go(t: string, id?: number) {
  pendingFocus = id ? { [t]: id } : null
  tab.value = t
}
function openLink(target: string) {
  const node = resolveLink(target, notes.value, docs.value, tasks.value, meetings.value)
  if (node.kind === 'note' || node.kind === 'ghost') {
    if (node.kind === 'ghost') return toast.error(`“${target}” isn’t written yet — create it from the Notes tab.`)
    go('Notes', node.ref!)
  } else if (node.kind === 'doc') go('Docs', node.ref!)
  else if (node.kind === 'meeting') go('Meetings', node.ref!)
  else select(tasks.value.find((t) => t.id === node.ref)!)
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
    <div v-if="loading" class="grid gap-4" aria-busy="true" aria-label="Loading project">
      <div class="h-16 w-2/3 rounded-lg bg-panel/70 motion-safe:animate-pulse" />
      <div class="h-80 rounded-xl bg-panel/70 motion-safe:animate-pulse" />
    </div>
    <LoadError v-else-if="error" :message="error" @retry="load(true)" />
    <template v-else-if="project">
      <PageHeader :eyebrow="`Delivery · ${project.key}`" :title="project.name" :description="project.tagline || project.description">
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
          <button
            v-if="project.can_manage && tab === 'Board' && board?.columns.length"
            class="btn-primary"
            @click="create()"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            New task
          </button>
        </template>
      </PageHeader>
      <TabBar v-model="tab" :tabs="views" label="Project views" id-prefix="prj" class="mb-6" />
      <div :id="`prj-panel-${tab}`" role="tabpanel" :aria-labelledby="`prj-tab-${tab}`">
        <ProjectOverview
          v-if="tab === 'Overview'"
          :project="project"
          :tasks="tasks"
          :sprints="sprints"
          :milestones="milestones"
          :meetings="meetings"
          :notes="notes"
          :docs="docs"
          :links="links"
          @go="go"
          @select="select"
          @saved="reloadProject"
        />
        <template v-else-if="tab === 'Board'">
          <h2 class="sr-only">{{ board?.name || 'Project board' }}</h2>
          <div class="mb-5 flex flex-wrap items-center gap-3">
            <label class="field"
              ><span class="sr-only">Board</span
              ><select v-model="boardId" class="input">
                <option :value="0" disabled>Select board</option>
                <option v-for="b in project.boards" :key="b.id" :value="b.id">{{ b.name }}</option>
              </select></label
            ><label class="field min-w-0 flex-1 sm:max-w-xs"
              ><span class="sr-only">Search tasks</span
              ><input v-model="search" class="input" type="search" placeholder="Search tasks or labels…" /></label
            ><label class="flex items-center gap-2 text-xs text-ink/65"
              ><input v-model="onlyMine" type="checkbox" class="accent-ink" /> Assigned to me</label
            ><label v-if="activeSprint" class="flex items-center gap-2 text-xs text-ink/65"
              ><input v-model="sprintOnly" type="checkbox" class="accent-ink" /> {{ activeSprint.name }} only</label
            >
          </div>
          <TaskBoard
            v-if="board"
            :board="board"
            :tasks="filtered"
            :can-manage="project.can_manage"
            :user-id="user?.id"
            :busy="busy"
            @select="select"
            @move="move"
            @create="create"
          />
          <div v-else class="panel">
            <EmptyState title="No boards yet" :hint="project.can_manage ? 'Add a board in the Settings tab to start tracking tasks.' : 'Your project lead has not set up a board yet.'">
              <button v-if="project.can_manage" class="btn-ghost btn-sm" @click="tab = 'Settings'">Open settings</button>
            </EmptyState>
          </div>
        </template>
        <SprintsPanel v-else-if="tab === 'Sprints'" :project="project" :tasks="tasks" :sprints="sprints" @changed="afterTaskChange" @select="select" />
        <TaskTimeline
          v-else-if="tab === 'Timeline'"
          :tasks="tasks"
          :milestones="milestones"
          :sprints="sprints"
          :can-manage="project.can_manage"
          @select="select"
          @reschedule="reschedule"
        />
        <NotesPanel
          v-else-if="tab === 'Notes'"
          :project="project"
          :notes="notes"
          :docs="docs"
          :tasks="tasks"
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
          @changed="refresh('meetings', 'tasks')"
          @wikilink="openLink"
        />
        <WhiteboardPanel v-else-if="tab === 'Whiteboard'" :project="project" :boards="whiteboards" @changed="refresh('whiteboards')" />
        <ProjectHub v-else-if="tab === 'Hub'" :project="project" :milestones="milestones" :links="links" @saved="refresh('milestones', 'links')" />
        <ProfileEditor v-else-if="tab === 'Profile' && project.can_manage" :project="project" :docs="docs" :links="links" @saved="reloadProject" />
        <ProjectSettings v-else-if="tab === 'Settings' && project.can_manage" :project="project" @saved="load()" />
      </div>
      <TaskDialog
        :open="dialog"
        :project="project"
        :task="selected"
        :column="newColumn"
        :milestones="milestones"
        :sprints="sprints"
        @close="dialog = false"
        @saved="afterTaskChange"
      />
    </template>
  </div>
</template>
