import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AuditPage from '../pages/app/AuditPage.vue'
import MonitoringPage from '../pages/app/MonitoringPage.vue'
import AuditDetail from '../components/app/oversight/AuditDetail.vue'
import AttendanceTrend from '../components/app/oversight/AttendanceTrend.vue'
import type { AuditEvent } from '../components/app/oversight/oversight'
import api from '../api/api'

vi.mock('../api/api', () => ({ default: { get: vi.fn<() => Promise<unknown>>() } }))
const event: AuditEvent = {
  id: 71,
  timestamp: '2026-10-17T08:00:00Z',
  actor_id: 3,
  actor_label: 'Reviewer',
  actor_role: 'super_admin',
  action: 'update',
  target_model: 'finance.payslip',
  target_id: '12',
  source: 'api',
  entry_point: 'PATCH api/finance/payslips/<pk>/',
  request_id: 'a0e6c459-e8b1-468a-8a54-827c922365f2',
  diff: {
    deductions: { redacted: true, changed: true },
    status: { before: 'draft', after: 'issued' },
  },
}
const options = {
  modules: ['finance', 'org'],
  actions: ['create', 'update'],
  sources: ['api', 'system'],
  capture_started_at: null,
}
const page = { count: 26, next: 'page2', previous: null, results: [event] }
const global = {
  stubs: {
    RouterLink: { template: '<a><slot /></a>' },
    Modal: { props: ['open'], template: '<div v-if="open"><slot /><slot name="footer" /></div>' },
  },
}
beforeEach(() => {
  vi.mocked(api.get).mockReset()
  vi.mocked(api.get).mockImplementation(async (url) => ({
    data: url === 'audit/options/' ? options : page,
  }))
})
describe('Audit ledger', () => {
  it('paginates using applied filters and resets pagination for new filters', async () => {
    const wrapper = mount(AuditPage, { global })
    await flushPromises()
    await wrapper.get('select').setValue('finance')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('audit/events/', {
      params: { module: 'finance', page: 1 },
    })
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Next →')!
      .trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('audit/events/', {
      params: { module: 'finance', page: 2 },
    })
    await wrapper.get('input[type="search"]').setValue('Reviewer')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('audit/events/', {
      params: { module: 'finance', search: 'Reviewer', page: 1 },
    })
    wrapper.unmount()
  })
  it('traces a request after clearing unrelated filters', async () => {
    const wrapper = mount(AuditPage, { global })
    await flushPromises()
    await wrapper.get('select').setValue('org')
    await wrapper.get('button[aria-label="Inspect event 71"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === "Show this request's events")!
      .trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('audit/events/', {
      params: { request_id: event.request_id, page: 1 },
    })
    expect(wrapper.findComponent(AuditDetail).props('event')).toBeNull()
    wrapper.unmount()
  })
  it('shows a retry on network failure and recovers', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('offline'))
    const wrapper = mount(AuditPage, { global })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Could not load')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Retry')!
      .trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Reviewer')
    wrapper.unmount()
  })
  it('explains an empty filtered result without offering invalid pagination', async () => {
    vi.mocked(api.get).mockImplementation(async (url) => ({
      data:
        url === 'audit/options/' ? options : { count: 0, next: null, previous: null, results: [] },
    }))
    const wrapper = mount(AuditPage, { global })
    await flushPromises()
    expect(wrapper.text()).toContain('No events match these filters')
    expect(
      wrapper
        .findAll('button')
        .find((b) => b.text() === 'Next →')!
        .attributes('disabled'),
    ).toBeDefined()
    wrapper.unmount()
  })
  it('renders redactions and escapes stored content in field changes', () => {
    const wrapper = mount(AuditDetail, {
      props: {
        event: {
          ...event,
          diff: { ...event.diff, name: { before: '', after: '<script>unsafe()</script>' } },
        },
      },
      global,
    })
    expect(wrapper.text()).toContain('Value redacted · changed')
    expect(wrapper.text()).toContain('<script>unsafe()</script>')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('draft')
    expect(wrapper.text()).toContain('issued')
    wrapper.unmount()
  })
})
describe('Organization monitoring', () => {
  it('shows an actionable initial load error and allows another attempt', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('offline'))
    const wrapper = mount(MonitoringPage, { global })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('up to 93 days')
    const refresh = wrapper.findAll('button').find((b) => b.text() === 'Refresh overview')!
    expect(refresh.attributes('disabled')).toBeUndefined()
    await refresh.trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
})
describe('Attendance visualization', () => {
  it('offers the exact counts in a table and scales zero-count days without invalid SVG geometry', () => {
    const wrapper = mount(AttendanceTrend, {
      props: {
        days: [
          {
            date: '2026-10-17',
            kind: 'weekend',
            present: 0,
            late: 0,
            absent: 0,
            on_leave: 0,
            not_checked_in: 0,
            expected: 0,
            attended: 0,
          },
        ],
      },
    })
    expect(wrapper.get('summary').text()).toContain('Daily register')
    expect(wrapper.get('tbody').text()).toContain('weekend')
    expect(wrapper.html()).not.toMatch(/NaN|Infinity/)
    expect(wrapper.get('svg').attributes('aria-label')).toContain('attendance')
    wrapper.unmount()
  })
})
