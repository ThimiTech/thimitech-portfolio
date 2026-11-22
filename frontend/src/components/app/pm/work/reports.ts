/** Sprint charts as pure functions (burndown, velocity), so they unit-test without a browser. */
import { dayNum, type Sprint, type Task } from '../pm'

export const points = (ts: Task[]) => ts.reduce((s, t) => s + (t.estimate ?? 0), 0)
const nptDay = (iso: string) => dayNum(new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kathmandu' }).format(new Date(iso)))

export interface Burndown {
  total: number
  remaining: number
  unit: 'pts' | 'issues'
  ideal: string
  actual: string
  today: number | null
  pct: number
  start: string
  end: string
}
/** Remaining work per day across a sprint, in story points (issue count when nothing is estimated). */
export function burndown(s: Sprint, tasks: Task[], today: string, W = 600, H = 200): Burndown {
  const ts = tasks.filter((t) => t.sprint === s.id && t.type !== 'module' && t.type !== 'epic')
  const byPoints = points(ts) > 0
  const weight = byPoints ? (t: Task) => t.estimate ?? 0 : () => 1
  const total = ts.reduce((a, t) => a + weight(t), 0)
  const d0 = dayNum(s.start_date)
  const days = Math.max(dayNum(s.end_date) - d0, 1)
  const last = s.status === 'completed' && s.completed_at ? Math.min(nptDay(s.completed_at), d0 + days) : Math.min(dayNum(today), d0 + days)
  const X = (d: number) => ((d - d0) / days) * W
  const Y = (v: number) => H - (total ? (v / total) * H : 0)
  const actual: string[] = []
  for (let d = d0; d <= last; d++) {
    const left = total - ts.filter((t) => t.completed_at && nptDay(t.completed_at) <= d).reduce((a, t) => a + weight(t), 0)
    actual.push(`${actual.length ? 'L' : 'M'}${X(d).toFixed(1)} ${Y(left).toFixed(1)}`)
  }
  const remaining = total - ts.filter((t) => t.status === 'done').reduce((a, t) => a + weight(t), 0)
  return {
    total,
    remaining,
    unit: byPoints ? 'pts' : 'issues',
    ideal: `M0 ${Y(total)} L${W} ${H}`,
    actual: actual.join(' '),
    today: last >= d0 ? X(last) : null,
    pct: total ? Math.round(((total - remaining) / total) * 100) : 0,
    start: s.start_date,
    end: s.end_date,
  }
}

/** Points finished in each completed sprint (most recent eight) and the average. */
export function velocity(sprints: Sprint[], tasks: Task[]) {
  const rows = sprints
    .filter((s) => s.status === 'completed')
    .slice(-8)
    .map((s) => {
      const ts = tasks.filter((t) => t.sprint === s.id)
      return { sprint: s, done: points(ts.filter((t) => t.status === 'done')), committed: points(ts) }
    })
  const max = Math.max(...rows.map((r) => Math.max(r.done, r.committed)), 1)
  const avg = rows.length ? Math.round(rows.reduce((a, r) => a + r.done, 0) / rows.length) : 0
  return { rows, max, avg }
}
