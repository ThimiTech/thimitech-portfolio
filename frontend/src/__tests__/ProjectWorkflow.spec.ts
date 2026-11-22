import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskTimeline from '../components/app/pm/TaskTimeline.vue'
import { isOverdue, type Task } from '../components/app/pm/pm'
const task: Task = {
  id: 1,
  key: 'GIS-1',
  title: 'Publish catchments',
  description: '',
  project: 1,
  board: 1,
  column: 1,
  status: 'backlog',
  assignee: 10,
  assignee_name: 'Team member',
  priority: 'high',
  estimate: 3,
  labels: ['GIS'],
  position: 0,
  milestone: null,
  sprint: null,
  start_date: '2030-01-02',
  due_date: '2030-01-06',
  completed_at: null,
  type: 'task',
  parent: null,
  blocked_by: [],
  blocker: '',
}
describe('Timeline and deadlines', () => {
  it('renders a milestone-only timeline without invalid geometry', () => {
    const wrapper = mount(TaskTimeline, {
      props: {
        tasks: [],
        milestones: [
          { id: 1, project: 1, title: 'Launch', due_date: '2030-01-06', completed: false },
        ],
      },
    })
    expect(wrapper.text()).toContain('Launch')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
  })
  it('keeps undated tasks visible in its count', () => {
    const wrapper = mount(TaskTimeline, {
      props: { tasks: [{ ...task, start_date: null, due_date: null }], milestones: [] },
    })
    expect(wrapper.text()).toContain('1 work item without dates')
    expect(wrapper.text()).toContain('Add dates')
  })
  it('marks overdue work using Nepal’s date and excludes completed tasks', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2030-01-06T19:00:00Z'))
    expect(isOverdue(task)).toBe(true)
    expect(isOverdue({ ...task, status: 'done' })).toBe(false)
    expect(isOverdue({ ...task, due_date: null })).toBe(false)
    vi.useRealTimers()
  })
})
