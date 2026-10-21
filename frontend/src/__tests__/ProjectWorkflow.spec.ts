import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskBoard from '../components/app/pm/TaskBoard.vue'
import TaskTimeline from '../components/app/pm/TaskTimeline.vue'
import { isOverdue, type Task } from '../components/app/pm/pm'
const board = {
  id: 1,
  project: 1,
  name: 'Main',
  columns: [
    { id: 1, board: 1, name: 'Backlog', position: 0, status: 'backlog' },
    { id: 2, board: 1, name: 'Done', position: 1, status: 'done' },
  ],
}
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
  start_date: '2030-01-02',
  due_date: '2030-01-06',
}
describe('Project board', () => {
  it('lets members drag their assigned tasks and opens task details from a button', async () => {
    const wrapper = mount(TaskBoard, {
      props: { board, tasks: [task], canManage: false, userId: 10, busy: false },
    })
    expect(wrapper.find('article').attributes('draggable')).toBe('true')
    expect(wrapper.text()).not.toContain('Add task')
    await wrapper.get('article button').trigger('click')
    expect(wrapper.emitted('select')?.[0]).toEqual([task])
    await wrapper.get('article').trigger('dragstart', { dataTransfer: { setData: vi.fn<() => void>() } })
    await wrapper.findAll('section')[1]!.trigger('drop')
    expect(wrapper.emitted('move')?.[0]).toEqual([task, 2])
    wrapper.unmount()
  })
  it('prevents dragging another member’s task or moving while saving', async () => {
    const wrapper = mount(TaskBoard, {
      props: { board, tasks: [task], canManage: false, userId: 20, busy: false },
    })
    expect(wrapper.get('article').attributes('draggable')).toBe('false')
    await wrapper.setProps({ canManage: true, busy: true })
    expect(wrapper.get('article').attributes('draggable')).toBe('false')
    wrapper.unmount()
  })
})
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
    expect(wrapper.text()).toContain('1 tasks without dates')
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
