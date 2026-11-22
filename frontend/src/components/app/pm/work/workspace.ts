/** The delivery workspace's shared state: one project's issues, sprints and milestones, plus every action that
 *  changes them. `createWorkspace` is called once by a page (the workspace or the project profile) and provided;
 *  views and the issue panel `useWorkspace()` it, so a change made anywhere shows everywhere at once. */
import { computed, inject, provide, reactive, ref, type InjectionKey, type UnwrapNestedRefs } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/api'
import { useAuth } from '@/stores/auth'
import { toast } from '../../ui/toast'
import { confirmDialog } from '../../ui/confirm'
import { errorMessage, isBlocked, isContainer, type ItemType, type Milestone, type Project, type Sprint, type Task } from '../pm'
import { byRank, childrenMap, rerankLocal } from './meta'

export interface CreateDefaults {
  type?: ItemType
  parent?: number | null
  sprint?: number | null
  column?: number | null
  assignee?: number | null
}
export type SprintDialog = { mode: 'create' | 'edit' | 'complete' | null; sprint: Sprint | null }

function build(projectId: () => string) {
  const route = useRoute()
  const router = useRouter()
  const { user } = useAuth()

  const project = ref<Project | null>(null)
  const tasks = ref<Task[]>([])
  const sprints = ref<Sprint[]>([])
  const milestones = ref<Milestone[]>([])
  const loading = ref(true)
  const error = ref('')
  const boardId = ref(0)

  const byId = computed(() => new Map(tasks.value.map((t) => [t.id, t])))
  const byKey = computed(() => new Map(tasks.value.map((t) => [t.key.toUpperCase(), t])))
  const children = computed(() => childrenMap(tasks.value))
  const board = computed(() => project.value?.boards.find((b) => b.id === boardId.value) || project.value?.boards[0] || null)
  const columns = computed(() => board.value?.columns || [])
  const allColumns = computed(() => project.value?.boards.flatMap((b) => b.columns) || [])
  /** Stories, tasks and bugs in rank order: what boards, sprints and progress count. */
  const work = computed(() => tasks.value.filter((t) => !isContainer(t)).sort(byRank))
  const modules = computed(() => tasks.value.filter((t) => t.type === 'module').sort(byRank))
  const epics = computed(() => tasks.value.filter((t) => t.type === 'epic').sort(byRank))
  const activeSprint = computed(() => sprints.value.find((s) => s.status === 'active') || null)
  const openSprints = computed(() => sprints.value.filter((s) => s.status !== 'completed'))
  const canManage = computed(() => !!project.value?.can_manage)
  const me = computed(() => user.value?.id ?? null)
  const people = computed(() => project.value?.people || [])
  const base = computed(() => `/app/projects/${projectId()}/work`)

  const blocked = (t: Task) => t.status !== 'done' && isBlocked(t, byId.value)
  const canMove = (t: Task) => canManage.value || (t.assignee !== null && t.assignee === me.value)
  const columnsFor = (t: Task) => project.value?.boards.find((b) => b.id === t.board)?.columns || columns.value

  // ───── loading ─────
  const list = <T>(url: string) => api.get<T>(url, { params: { project: projectId() } }).then((r) => r.data)
  async function load(initial = false) {
    if (initial) loading.value = true
    error.value = ''
    try {
      const [p, t, s, m] = await Promise.all([
        api.get<Project>(`pm/projects/${projectId()}/`).then((r) => r.data),
        list<Task[]>('pm/tasks/'),
        list<Sprint[]>('pm/sprints/'),
        list<Milestone[]>('pm/milestones/'),
      ])
      project.value = p
      tasks.value = t
      sprints.value = s
      milestones.value = m
      if (!p.boards.some((b) => b.id === boardId.value)) boardId.value = p.boards[0]?.id || 0
    } catch {
      error.value = 'Could not load this project. It may be unavailable or you may no longer have access.'
    } finally {
      loading.value = false
    }
  }
  const refreshTasks = async () => void (tasks.value = await list<Task[]>('pm/tasks/'))
  const refreshSprints = async () => void (sprints.value = await list<Sprint[]>('pm/sprints/'))
  const refreshMilestones = async () => void (milestones.value = await list<Milestone[]>('pm/milestones/'))
  async function refreshProject() {
    project.value = (await api.get<Project>(`pm/projects/${projectId()}/`)).data
  }
  /** Progress lives on the project; refetch it once after a burst of edits. */
  let projectTimer: ReturnType<typeof setTimeout> | undefined
  function touchProject() {
    clearTimeout(projectTimer)
    projectTimer = setTimeout(() => refreshProject().catch(() => {}), 700)
  }

  // ───── issues ─────
  /** Optimistic edit: the change shows at once and rolls back (with a toast) if the server refuses it. */
  async function patch(task: Task, data: Record<string, unknown>) {
    const t = byId.value.get(task.id) || task
    const before = { ...t, labels: [...t.labels], blocked_by: [...t.blocked_by] }
    const local: Record<string, unknown> = { ...data }
    if ('column' in data) local.status = allColumns.value.find((c) => c.id === data.column)?.status ?? t.status
    if ('assignee' in data) local.assignee_name = people.value.find((p) => p.id === data.assignee)?.name ?? null
    Object.assign(t, local)
    try {
      const saved = (await api.patch<Task>(`pm/tasks/${t.id}/`, data)).data
      Object.assign(t, saved)
      touchProject()
      return t
    } catch (e) {
      Object.assign(t, before)
      toast.error(errorMessage(e))
      return null
    }
  }
  async function create(data: Record<string, unknown>) {
    try {
      const saved = (await api.post<Task>('pm/tasks/', { column: columns.value[0]?.id, ...data })).data
      tasks.value.push(saved)
      touchProject()
      return saved
    } catch (e) {
      toast.error(errorMessage(e))
      return null
    }
  }
  async function remove(task: Task) {
    const kids = children.value.get(task.id)?.length || 0
    const ok = await confirmDialog({
      title: `Delete ${task.key}?`,
      body: kids
        ? `“${task.title}” and its comments will be deleted. Its ${kids} child item${kids === 1 ? '' : 's'} move${kids === 1 ? 's' : ''} up to the top level.`
        : `“${task.title}” and its comments will be deleted. This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    })
    if (!ok) return false
    try {
      await api.delete(`pm/tasks/${task.id}/`)
      if (issueKey.value === task.key.toUpperCase()) closeIssue()
      await refreshTasks()
      touchProject()
      toast.success(`${task.key} deleted.`)
      return true
    } catch (e) {
      toast.error(errorMessage(e))
      return false
    }
  }
  /** Rank `ids` in this order (managers only; the rest of the project keeps its order). */
  async function reorder(ids: number[]) {
    if (!canManage.value || ids.length < 2) return
    rerankLocal(tasks.value, ids)
    try {
      await api.post('pm/tasks/reorder/', { project: Number(projectId()), ids })
    } catch (e) {
      toast.error(errorMessage(e))
    }
    refreshTasks().catch(() => {})
  }
  /** Drag-and-drop: change column/sprint if needed, then rank in the destination list. */
  async function move(task: Task, changes: Record<string, unknown>, order?: number[]) {
    const diff = Object.fromEntries(Object.entries(changes).filter(([k, v]) => (task as unknown as Record<string, unknown>)[k] !== v))
    if (Object.keys(diff).length && !(await patch(task, diff))) return
    if (order) await reorder(order)
  }

  // ───── navigation ─────
  const issueKey = computed(() => (typeof route.query.issue === 'string' ? route.query.issue.toUpperCase() : ''))
  const openIssue = (t: Task | string) => router.push({ query: { ...route.query, issue: typeof t === 'string' ? t : t.key } })
  function closeIssue() {
    const query = { ...route.query }
    delete query.issue
    router.push({ query })
  }
  /** Modules and epics open their own page; everything else opens the issue panel. */
  function go(t: Task) {
    if (t.type === 'module') router.push(`${base.value}/modules/${t.id}`)
    else if (t.type === 'epic') router.push(`${base.value}/epics/${t.id}`)
    else openIssue(t)
  }
  /** Where an item's title links: its own page (modules, epics) or the issue panel over the current view. */
  const linkOf = (t: Task) =>
    t.type === 'module' || t.type === 'epic' ? pathOf(t) : { path: route.path, query: { ...route.query, issue: t.key } }
  const pathOf = (t: Task) =>
    t.type === 'module' ? `${base.value}/modules/${t.id}` : t.type === 'epic' ? `${base.value}/epics/${t.id}` : `${base.value}/list?issue=${t.key}`

  // ───── create dialog ─────
  const creating = reactive({ open: false, defaults: {} as CreateDefaults })
  function openCreate(defaults: CreateDefaults = {}) {
    creating.defaults = defaults
    creating.open = true
  }

  // ───── sprints ─────
  const sprintDialog = reactive<SprintDialog>({ mode: null, sprint: null })
  const openSprint = (mode: SprintDialog['mode'], sprint: Sprint | null = null) => Object.assign(sprintDialog, { mode, sprint })
  async function sprintAction(run: () => Promise<unknown>, ok: string) {
    try {
      await run()
      toast.success(ok)
      await Promise.all([refreshSprints(), refreshTasks()])
      return true
    } catch (e) {
      toast.error(errorMessage(e))
      return false
    }
  }
  const startSprint = (s: Sprint) => sprintAction(() => api.post(`pm/sprints/${s.id}/start/`), `${s.name} started.`)
  async function deleteSprint(s: Sprint) {
    const n = tasks.value.filter((t) => t.sprint === s.id).length
    const ok = await confirmDialog({
      title: `Delete ${s.name}?`,
      body: n ? `Its ${n} issue${n === 1 ? '' : 's'} go back to the backlog.` : 'The sprint has no issues.',
      confirmLabel: 'Delete sprint',
      danger: true,
    })
    return ok && sprintAction(() => api.delete(`pm/sprints/${s.id}/`), `${s.name} deleted.`)
  }

  return {
    project, tasks, sprints, milestones, loading, error, boardId,
    byId, byKey, children, board, columns, allColumns, work, modules, epics, activeSprint, openSprints,
    canManage, me, people, base, issueKey, creating, sprintDialog,
    blocked, canMove, columnsFor,
    load, refreshTasks, refreshSprints, refreshMilestones, refreshProject, touchProject,
    patch, create, remove, reorder, move,
    openIssue, closeIssue, go, pathOf, linkOf, openCreate, openSprint, sprintAction, startSprint, deleteSprint,
  }
}

const KEY: InjectionKey<Workspace> = Symbol('workspace')
/** Refs come back unwrapped (`ws.tasks` is the array), so templates and scripts read the same way. */
export function createWorkspace(projectId: () => string) {
  const ws = reactive(build(projectId))
  provide(KEY, ws)
  return ws
}
export type Workspace = UnwrapNestedRefs<ReturnType<typeof build>>
export function useWorkspace() {
  const ws = inject(KEY)
  if (!ws) throw new Error('useWorkspace() needs a page that called createWorkspace()')
  return ws
}
