/** Delivery workspace vocabulary: issue types, priorities, status categories, colours and hierarchy helpers.
 *  Pure (no browser or API imports) so it unit-tests in the node environment. */
import type { ItemType } from '../plan'
import type { Column, Task } from '../pm'

// ───────────── Issue types ─────────────
/** Glyphs drawn on a 16×16 grid, white on the type colour (as in Jira's issue-type icons). */
export const TYPE_META: Record<ItemType, { label: string; color: string; glyph: string }> = {
  module: { label: 'Module', color: 'var(--color-ink)', glyph: 'M3 5.5 8 3l5 2.5L8 8 3 5.5Zm0 3L8 11l5-2.5M3 11.5 8 14l5-2.5' },
  epic: { label: 'Epic', color: '#8a5cc2', glyph: 'M9 2.5 4.5 9H8l-1 4.5L11.5 7H8l1-4.5Z' },
  story: { label: 'Story', color: 'var(--color-moss)', glyph: 'M5 3h6v10l-3-2.2L5 13V3Z' },
  task: { label: 'Task', color: 'var(--color-sky)', glyph: 'm4.5 8.2 2.3 2.3 4.7-5' },
  bug: { label: 'Bug', color: 'var(--color-rust)', glyph: 'M8 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z' },
}
/** What may sit directly under each type (the hierarchy Module › Epic › Story › Task/Bug). */
export const CHILD_TYPES: Record<ItemType, ItemType[]> = {
  module: ['epic', 'story', 'task', 'bug'],
  epic: ['story', 'task', 'bug'],
  story: ['task', 'bug'],
  task: [],
  bug: [],
}
export const WORK_TYPES: ItemType[] = ['story', 'task', 'bug']

// ───────────── Priorities ─────────────
export const PRIORITIES = ['urgent', 'high', 'medium', 'low'] as const
export type Priority = (typeof PRIORITIES)[number]
export const PRIORITY_META: Record<string, { label: string; color: string; path: string }> = {
  urgent: { label: 'Urgent', color: 'var(--color-rust)', path: 'M4 9.5 8 6l4 3.5M4 13 8 9.5l4 3.5' },
  high: { label: 'High', color: 'var(--color-flag)', path: 'M4 10.5 8 7l4 3.5' },
  medium: { label: 'Medium', color: 'var(--color-contour)', path: 'M4 7h8M4 10h8' },
  low: { label: 'Low', color: 'var(--color-sky)', path: 'M4 6.5 8 10l4-3.5' },
}

// ───────────── Status categories ─────────────
/** Board columns map onto three categories, which drive colours and roll-ups (To do · In progress · Done). */
export type Category = 'todo' | 'progress' | 'done'
export const categoryOf = (status: string): Category =>
  status === 'done' ? 'done' : status === 'active' || status === 'review' ? 'progress' : 'todo'
export const CATEGORY_META: Record<Category, { label: string; lozenge: string; bar: string }> = {
  todo: { label: 'To do', lozenge: 'bg-ink/[0.08] text-ink/75', bar: 'bg-ink/25' },
  progress: { label: 'In progress', lozenge: 'bg-sky/15 text-sky', bar: 'bg-sky' },
  done: { label: 'Done', lozenge: 'bg-moss/15 text-moss', bar: 'bg-moss' },
}
export const columnLabel = (columns: Column[], id: number) => columns.find((c) => c.id === id)?.name || ''

// ───────────── Colours for epics / modules ─────────────
const SWATCHES = ['#8a5cc2', '#4f6d7a', '#5d7a4f', '#aa4825', '#b08d5b', '#3f7f8f', '#9a4f6b', '#6b6450']
/** A stable colour per container, used for its chips and lane headers. */
export const swatch = (id: number) => SWATCHES[Math.abs(id) % SWATCHES.length]!

// ───────────── Hierarchy ─────────────
export function childrenMap(tasks: Task[]) {
  const map = new Map<number, Task[]>()
  for (const t of tasks) if (t.parent) (map.get(t.parent) || map.set(t.parent, []).get(t.parent)!).push(t)
  for (const list of map.values()) list.sort(byRank)
  return map
}
/** Workspace order: the project-wide rank, then id (matches the API's ordering). */
export const byRank = (a: Task, b: Task) => a.position - b.position || a.id - b.id

/** Nearest-first chain of parents (guards against a broken cycle in stale data). */
export function ancestors(task: Task, byId: Map<number, Task>) {
  const out: Task[] = []
  const seen = new Set([task.id])
  for (let p = task.parent ? byId.get(task.parent) : undefined; p && !seen.has(p.id); p = p.parent ? byId.get(p.parent) : undefined) {
    out.push(p)
    seen.add(p.id)
  }
  return out
}
export const nearest = (task: Task, byId: Map<number, Task>, type: ItemType) => ancestors(task, byId).find((a) => a.type === type) || null

/** Every item below `id`, depth-first in rank order, with its depth relative to `id` (children are depth 0). */
export function descendants(id: number, children: Map<number, Task[]>, depth = 0, seen = new Set<number>()): { task: Task; depth: number }[] {
  if (seen.has(id)) return []
  seen.add(id)
  return (children.get(id) || []).flatMap((t) => [{ task: t, depth }, ...descendants(t.id, children, depth + 1, seen)])
}

export interface Rollup {
  total: number
  done: number
  progress: number
  points: number
  donePoints: number
  blocked: number
  due: string | null
  percent: number
}
/** Progress of everything under a container: work items only (stories, tasks, bugs), as the project progress counts. */
export function rollup(id: number, children: Map<number, Task[]>, isBlockedFn: (t: Task) => boolean = () => false): Rollup {
  const r: Rollup = { total: 0, done: 0, progress: 0, points: 0, donePoints: 0, blocked: 0, due: null, percent: 0 }
  for (const { task: t } of descendants(id, children)) {
    if (t.due_date && (!r.due || t.due_date > r.due)) r.due = t.due_date
    if (t.type === 'module' || t.type === 'epic') continue
    const cat = categoryOf(t.status)
    r.total++
    r.points += t.estimate ?? 0
    if (cat === 'done') {
      r.done++
      r.donePoints += t.estimate ?? 0
    } else {
      if (cat === 'progress') r.progress++
      if (isBlockedFn(t)) r.blocked++
    }
  }
  r.percent = r.total ? Math.round((r.done / r.total) * 100) : 0
  return r
}

/** Valid parents for an item of `type`: anything ranked higher, except the item itself and its own subtree. */
export function parentOptions(type: ItemType, tasks: Task[], self?: Task | null) {
  const rank: Record<ItemType, number> = { module: 0, epic: 1, story: 2, task: 3, bug: 3 }
  if (!self) return tasks.filter((t) => rank[t.type] < rank[type])
  const kids = childrenMap(tasks)
  const below = new Set(descendants(self.id, kids).map((d) => d.task.id))
  return tasks.filter((t) => rank[t.type] < rank[type] && t.id !== self.id && !below.has(t.id))
}

/** New order for a list after moving `id` to `index` (index counts positions in the list without the item). */
export function moveInList(ids: number[], id: number, index: number) {
  const rest = ids.filter((x) => x !== id)
  rest.splice(Math.max(0, Math.min(index, rest.length)), 0, id)
  return rest
}

/** Mirror of the API's rerank: the listed items swap rank slots among themselves; everything else stays put. */
export function rerankLocal(tasks: Task[], ids: number[]) {
  const byId = new Map(tasks.map((t) => [t.id, t]))
  const picked = ids.map((i) => byId.get(i)).filter((t): t is Task => !!t)
  const slots = picked.map((t) => t.position).sort((a, b) => a - b)
  // equal slots (legacy data) still need a strict order: nudge by a fraction, the server normalises on its side
  picked.forEach((t, i) => (t.position = slots[i]! + i / 1000))
}

/** "3d ago", "5h ago", "just now". */
export function ago(iso: string, now = Date.now()) {
  const m = Math.round((now - Date.parse(iso)) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  if (m < 1440) return `${Math.round(m / 60)}h ago`
  if (m < 43200) return `${Math.round(m / 1440)}d ago`
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso))
}

/** History field names as people say them. */
export const FIELD_LABEL: Record<string, string> = {
  column: 'Status',
  assignee: 'Assignee',
  priority: 'Priority',
  estimate: 'Story points',
  parent: 'Parent',
  sprint: 'Sprint',
  milestone: 'Milestone',
  start_date: 'Start date',
  due_date: 'Due date',
  blocker: 'Impediment',
  labels: 'Labels',
  blocked_by: 'Blocked by',
  description: 'Description',
  title: 'Summary',
  type: 'Issue type',
}
