import { isAxiosError } from 'axios'

export interface Person {
  id: number
  name: string
}
export interface Column {
  id: number
  board: number
  name: string
  position: number
  status: string
}
export interface Board {
  id: number
  project: number
  name: string
  columns: Column[]
}
export interface Project {
  id: number
  name: string
  key: string
  description: string
  lead: number
  members: number[]
  people: Person[]
  boards: Board[]
  start_date: string | null
  due_date: string | null
  archived: boolean
  can_manage: boolean
  progress: { total: number; done: number; percent: number }
}
export interface Task {
  id: number
  key: string
  project: number
  board: number
  title: string
  description: string
  column: number
  status: string
  assignee: number | null
  assignee_name: string | null
  priority: string
  estimate: number | null
  labels: string[]
  position: number
  milestone: number | null
  start_date: string | null
  due_date: string | null
}
export interface Milestone {
  id: number
  project: number
  title: string
  due_date: string
  completed: boolean
}
export interface ProjectLink {
  id: number
  title: string
  kind: string
  url: string
}
export interface Comment {
  id: number
  author: number
  author_name: string
  body: string
  created_at: string
}
export interface Summary {
  projects: number
  tasks: number
  done: number
  active: number
  overdue: number
  assigned_to_me: number
}

export function errorMessage(error: unknown) {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data
    if (typeof data === 'object')
      return Object.entries(data)
        .map(
          ([key, value]) =>
            `${key === 'detail' ? '' : key + ': '}${Array.isArray(value) ? value.join(' ') : String(value)}`,
        )
        .join(' ')
  }
  return 'Could not save your changes. Please try again.'
}
export function dateLabel(date: string | null) {
  return date
    ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
        new Date(date + 'T00:00:00Z'),
      )
    : 'No due date'
}
export function todayNPT() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kathmandu' }).format(new Date())
}
export function isOverdue(task: Task) {
  return !!task.due_date && task.due_date < todayNPT() && task.status !== 'done'
}
