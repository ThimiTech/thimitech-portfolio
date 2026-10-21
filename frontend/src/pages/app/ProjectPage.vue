<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
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
import {
  errorMessage,
  isOverdue,
  type Project,
  type Task,
  type Milestone,
  type ProjectLink,
} from '@/components/app/pm/pm'

const route = useRoute()
const { user } = useAuth()
const project = ref<Project | null>(null)
const tasks = ref<Task[]>([])
const milestones = ref<Milestone[]>([])
const links = ref<ProjectLink[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const tab = ref('Board')
const boardId = ref(0)
const search = ref('')
const onlyMine = ref(false)
const dialog = ref(false)
const selected = ref<Task | null>(null)
const newColumn = ref(0)
const board = computed(
  () => project.value?.boards.find((b) => b.id === boardId.value) || project.value?.boards[0],
)
const filtered = computed(() =>
  tasks.value.filter(
    (t) =>
      t.board === board.value?.id &&
      (!onlyMine.value || t.assignee === user.value?.id) &&
      `${t.title} ${t.key} ${t.labels.join(' ')}`
        .toLowerCase()
        .includes(search.value.toLowerCase()),
  ),
)
const views = computed(() =>
  ['Board', 'Timeline', 'Project hub', ...(project.value?.can_manage ? ['Settings'] : [])].map((id) => ({
    id,
    label: id,
  })),
)
const overdue = computed(() => tasks.value.filter(isOverdue).length)
async function load(initial = false) {
  if (initial) loading.value = true
  error.value = ''
  try {
    const id = String(route.params.id)
    const [p, t, m, l] = await Promise.all([
      api.get<Project>(`pm/projects/${id}/`),
      api.get<Task[]>('pm/tasks/', { params: { project: id } }),
      api.get<Milestone[]>('pm/milestones/', { params: { project: id } }),
      api.get<ProjectLink[]>('pm/links/', { params: { project: id } }),
    ])
    project.value = p.data
    tasks.value = t.data
    milestones.value = m.data
    links.value = l.data
    if (!p.data.boards.some((b) => b.id === boardId.value))
      boardId.value = p.data.boards[0]?.id || 0
  } catch {
    error.value =
      'Could not load this project. It may be unavailable or you may no longer have access.'
  } finally {
    loading.value = false
  }
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
    await load()
    toast.success(`${task.key} moved.`)
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
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
      <PageHeader :eyebrow="`Delivery · ${project.key}`" :title="project.name" :description="project.description">
        <template #actions>
          <StatusPill v-if="project.archived" status="neutral" label="Archived" />
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
      <div class="mb-6 flex flex-wrap gap-x-8 gap-y-3 rounded-xl border border-ink/10 bg-sheet px-5 py-3.5 text-sm">
        <span
          ><strong class="readout">{{ project.progress.percent }}%</strong> complete</span
        ><span
          ><strong class="readout">{{ project.progress.done }}/{{ project.progress.total }}</strong>
          tasks done</span
        ><span
          ><strong class="readout">{{ project.people.length }}</strong> members</span
        ><span :class="overdue ? 'text-rust' : 'text-ink/60'"
          ><strong class="readout">{{ overdue }}</strong> overdue</span
        >
      </div>
      <TabBar v-model="tab" :tabs="views" label="Project views" id-prefix="prj" class="mb-6" />
      <div :id="`prj-panel-${tab}`" role="tabpanel" :aria-labelledby="`prj-tab-${tab}`">
      <template v-if="tab === 'Board'">
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
            ><input
              v-model="search"
              class="input"
              type="search"
              placeholder="Search tasks or labels…" /></label
          ><label class="flex items-center gap-2 text-xs text-ink/65"
            ><input v-model="onlyMine" type="checkbox" class="accent-ink" /> Assigned to me</label
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
      <TaskTimeline
        v-else-if="tab === 'Timeline'"
        :tasks="tasks"
        :milestones="milestones"
        @select="select"
      />
      <ProjectHub
        v-else-if="tab === 'Project hub'"
        :project="project"
        :milestones="milestones"
        :links="links"
        @saved="load()"
      />
      <ProjectSettings
        v-else-if="tab === 'Settings' && project.can_manage"
        :project="project"
        @saved="load()"
      />
      </div>
      <TaskDialog
        :open="dialog"
        :project="project"
        :task="selected"
        :column="newColumn"
        :milestones="milestones"
        @close="dialog = false"
        @saved="load()"
      />
    </template>
  </div>
</template>
