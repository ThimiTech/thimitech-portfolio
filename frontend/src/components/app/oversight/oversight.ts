import type { FinanceSummary } from '../finance/finance'
import type { InventorySummary } from '../inventory/inventory'

export interface AuditEvent {
  id: number
  timestamp: string
  actor_id: number | null
  actor_label: string
  actor_role: string
  action: string
  target_model: string
  target_id: string
  diff: Record<string, { redacted?: boolean; changed?: boolean; before?: unknown; after?: unknown }>
  source: string
  entry_point: string
  request_id: string | null
}
export interface AuditPage {
  count: number
  next: string | null
  previous: string | null
  results: AuditEvent[]
}
export interface AuditOptions {
  modules: string[]
  actions: string[]
  sources: string[]
  capture_started_at: string | null
}
export interface AttendanceDay {
  date: string
  kind: string
  present: number
  late: number
  absent: number
  on_leave: number
  not_checked_in: number
  expected: number
  attended: number
}
export interface ProjectHealth {
  id: number
  key: string
  name: string
  due_date: string | null
  total: number
  done: number
  overdue: number
  percent: number
  health: 'complete' | 'at_risk' | 'unplanned' | 'on_track'
}
export interface Overview {
  as_of: string
  generated_at: string
  timezone: string
  attendance_window: { start: string; end: string }
  headcount: {
    total: number
    unassigned: number
    joined_this_month: number
    by_department: { id: number; name: string; count: number }[]
    by_role: { role: string; count: number }[]
  }
  attendance: {
    days: AttendanceDay[]
    totals: Omit<AttendanceDay, 'date' | 'kind'>
    rate: number | null
    roster_basis: string
  }
  leave: {
    year: number
    remaining_paid_days: string
    pending_paid_days: string
    pending_requests: number
    by_type: {
      id: number
      name: string
      quota_days: string | null
      used_days: string
      pending_days: string
      remaining_days: string | null
    }[]
  }
  projects: {
    active: number
    archived: number
    total_tasks: number
    overdue_tasks: number
    unassigned_tasks: number
    by_project: ProjectHealth[]
  }
  finance: FinanceSummary
  inventory: InventorySummary
  audit: { capture_started_at: string | null; last_24h: number; recent: AuditEvent[] }
}
export function readable(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string') return value || '(empty)'
  return JSON.stringify(value)
}
export function label(value: string) {
  return value.replace(/_/g, ' ')
}
