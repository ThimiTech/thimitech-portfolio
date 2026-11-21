/** Work hierarchy (Module › Epic › Story › Task/Bug): pure logic, no browser imports, so it unit-tests in node. */
import type { Task } from './pm'

export type ItemType = 'module' | 'epic' | 'story' | 'task' | 'bug'
/** Hierarchy Module › Epic › Story › Task/Bug. A parent must have a lower rank. */
export const TYPES: Record<ItemType, { label: string; rank: number; badge: string }> = {
  module: { label: 'Module', rank: 0, badge: 'bg-ink text-paper' },
  epic: { label: 'Epic', rank: 1, badge: 'bg-contour/20 text-contour-ink' },
  story: { label: 'Story', rank: 2, badge: 'bg-moss/15 text-moss' },
  task: { label: 'Task', rank: 3, badge: 'bg-sky/15 text-sky' },
  bug: { label: 'Bug', rank: 3, badge: 'bg-rust/15 text-rust' },
}
/** Planning containers: kept off the board and sprints, and out of progress counts. */
export const isContainer = (t: Task) => t.type === 'module' || t.type === 'epic'
/** Blocked = a free-text blocker, or a linked item that isn't done yet. */
export const isBlocked = (t: Task, byId: Map<number, Task>) =>
  !!t.blocker || t.blocked_by.some((id) => byId.get(id) && byId.get(id)!.status !== 'done')

export interface TreeNode {
  task: Task
  depth: number
  children: TreeNode[]
  /** Work items (stories/tasks/bugs) in this subtree, itself included. */
  total: number
  done: number
  /** Latest due date in the subtree. */
  due: string | null
}
/** Build the hierarchy; items whose parent isn't in `tasks` become roots. */
export function buildTree(tasks: Task[]): TreeNode[] {
  const nodes = new Map(tasks.map((t) => [t.id, { task: t, depth: 0, children: [] as TreeNode[], total: 0, done: 0, due: null as string | null }]))
  const roots: TreeNode[] = []
  for (const n of nodes.values()) (n.task.parent && nodes.get(n.task.parent)?.children || roots).push(n)
  const order = (a: TreeNode, b: TreeNode) => TYPES[a.task.type].rank - TYPES[b.task.type].rank || a.task.position - b.task.position || a.task.id - b.task.id
  const roll = (n: TreeNode, depth: number) => {
    n.depth = depth
    n.children.sort(order)
    const own = !isContainer(n.task)
    n.total = own ? 1 : 0
    n.done = own && n.task.status === 'done' ? 1 : 0
    n.due = n.task.due_date
    for (const c of n.children) {
      roll(c, depth + 1)
      n.total += c.total
      n.done += c.done
      if (c.due && (!n.due || c.due > n.due)) n.due = c.due
    }
  }
  roots.sort(order).forEach((r) => roll(r, 0))
  return roots
}
