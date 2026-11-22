import { describe, expect, it } from 'vitest'
import type { Sprint, Task } from '@/components/app/pm/pm'
import {
  ancestors,
  categoryOf,
  childrenMap,
  descendants,
  moveInList,
  nearest,
  parentOptions,
  rerankLocal,
  rollup,
} from '@/components/app/pm/work/meta'
import { burndown, velocity } from '@/components/app/pm/work/reports'

let id = 0
const item = (type: Task['type'], parent: number | null, extra: Partial<Task> = {}): Task =>
  ({ id: ++id, key: `K-${id}`, type, parent, title: `${type} ${id}`, status: 'backlog', position: id * 10, blocked_by: [], blocker: '',
     estimate: null, sprint: null, start_date: null, due_date: null, completed_at: null, labels: [], ...extra }) as Task

describe('workspace hierarchy', () => {
  const mod = item('module', null)
  const epic = item('epic', mod.id)
  const story = item('story', epic.id, { status: 'done', estimate: 5, due_date: '2026-12-01' })
  const sub = item('task', story.id, { status: 'active', estimate: 2, due_date: '2026-12-20', blocker: 'waiting' })
  const loose = item('bug', mod.id, { estimate: 1 })
  const all = [mod, epic, story, sub, loose]
  const kids = childrenMap(all)
  const byId = new Map(all.map((t) => [t.id, t]))

  it('walks up and down the tree', () => {
    expect(ancestors(sub, byId).map((t) => t.id)).toEqual([story.id, epic.id, mod.id])
    expect(nearest(sub, byId, 'epic')?.id).toBe(epic.id)
    expect(nearest(loose, byId, 'epic')).toBeNull()
    expect(descendants(mod.id, kids).map((d) => [d.task.id, d.depth])).toEqual([[epic.id, 0], [story.id, 1], [sub.id, 2], [loose.id, 0]])
  })

  it('rolls up work items only, with points, blockers and the latest deadline', () => {
    const r = rollup(mod.id, kids, (t) => !!t.blocker)
    expect([r.total, r.done, r.progress, r.points, r.donePoints, r.blocked, r.due, r.percent]).toEqual([3, 1, 1, 8, 5, 1, '2026-12-20', 33])
    expect(categoryOf('review')).toBe('progress')
  })

  it('offers only higher-ranked parents outside the item’s own subtree', () => {
    expect(parentOptions('story', all).map((t) => t.id)).toEqual([mod.id, epic.id])
    // an epic can't move under itself or its own descendants; only the module remains
    expect(parentOptions('epic', all, epic).map((t) => t.id)).toEqual([mod.id])
  })

  it('reorders lists and swaps rank slots without touching other items', () => {
    expect(moveInList([1, 2, 3, 4], 4, 1)).toEqual([1, 4, 2, 3])
    expect(moveInList([1, 2, 3], 1, 99)).toEqual([2, 3, 1])
    const a = item('task', null, { position: 10 }), b = item('task', null, { position: 20 }), c = item('task', null, { position: 30 })
    rerankLocal([a, b, c], [c.id, a.id])
    expect([a.position, b.position, c.position].map(Math.floor)).toEqual([30, 20, 10])
  })
})

describe('sprint reports', () => {
  const sprint: Sprint = { id: 7, project: 1, name: 'S1', goal: '', start_date: '2030-01-01', end_date: '2030-01-11', status: 'active', completed_at: null }

  it('burns down story points and never yields invalid geometry', () => {
    const done = item('story', null, { sprint: 7, estimate: 3, status: 'done', completed_at: '2030-01-03T06:00:00Z' })
    const open = item('story', null, { sprint: 7, estimate: 5 })
    const chart = burndown(sprint, [done, open, item('epic', null, { sprint: 7 })], '2030-01-06')
    expect([chart.total, chart.remaining, chart.unit, chart.pct]).toEqual([8, 5, 'pts', 38])
    expect(chart.actual.split(' L').length).toBe(6) // one point per day from the 1st to the 6th
    expect(`${chart.actual} ${chart.ideal}`).not.toMatch(/NaN|Infinity/)
    expect(burndown(sprint, [item('task', null, { sprint: 7 })], '2030-01-06').unit).toBe('issues')
  })

  it('reports velocity as completed vs committed points', () => {
    const past = { ...sprint, id: 9, status: 'completed' as const }
    const v = velocity([past, sprint], [item('task', null, { sprint: 9, estimate: 3, status: 'done' }), item('task', null, { sprint: 9, estimate: 2 })])
    expect(v.rows.map((r) => [r.done, r.committed])).toEqual([[3, 5]])
    expect(v.avg).toBe(3)
  })
})
