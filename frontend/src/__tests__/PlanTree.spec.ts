// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { buildTree, isBlocked } from '@/components/app/pm/plan'
import type { Task } from '@/components/app/pm/pm'

let id = 0
const item = (type: Task['type'], parent: number | null, extra: Partial<Task> = {}): Task =>
  ({ id: ++id, key: `K-${id}`, type, parent, title: `${type} ${id}`, status: 'backlog', position: 0, blocked_by: [], blocker: '',
     start_date: null, due_date: null, ...extra }) as Task

describe('buildTree', () => {
  it('rolls work-item progress and the latest deadline up through modules and epics', () => {
    const mod = item('module', null)
    const epic = item('epic', mod.id)
    const story = item('story', epic.id, { status: 'done', due_date: '2026-12-01' })
    const task = item('task', story.id, { due_date: '2026-12-20' })
    const loose = item('task', mod.id) // directly under the module, no epic
    const [root] = buildTree([task, loose, story, epic, mod])
    expect(root!.task.id).toBe(mod.id)
    expect(root!.children.map((c) => c.task.id)).toEqual([epic.id, loose.id]) // higher levels first
    const epicNode = root!.children[0]!
    expect([epicNode.done, epicNode.total, epicNode.due]).toEqual([1, 2, '2026-12-20'])
    expect([root!.done, root!.total]).toEqual([1, 3]) // containers don't count
    expect(epicNode.children[0]!.children[0]!.depth).toBe(3)
  })

  it('treats items with a missing parent as roots, and only open blockers as blocking', () => {
    const orphan = item('story', 9999)
    expect(buildTree([orphan]).map((n) => n.task.id)).toEqual([orphan.id])
    const done = item('task', null, { status: 'done' })
    const open = item('task', null)
    const byId = new Map([done, open].map((t) => [t.id, t]))
    expect(isBlocked(item('task', null, { blocked_by: [done.id] }), byId)).toBe(false)
    expect(isBlocked(item('task', null, { blocked_by: [open.id] }), byId)).toBe(true)
    expect(isBlocked(item('task', null, { blocker: 'Waiting on data' }), byId)).toBe(true)
  })
})
