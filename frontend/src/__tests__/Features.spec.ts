import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import AuthForm from '../components/auth/AuthForm.vue'
import ResetForm from '../components/auth/ResetForm.vue'
import DataTable from '../components/app/ui/DataTable.vue'
import NotificationBell from '../components/app/ui/NotificationBell.vue'
import { useServerTable } from '../components/app/ui/serverTable'
import api from '../api/api'

vi.mock('../api/api', () => ({
  default: { get: vi.fn<() => Promise<unknown>>(), post: vi.fn<() => Promise<unknown>>(), patch: vi.fn<() => Promise<unknown>>() },
}))

const blank = { template: '<div />' }
async function makeRouter(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: blank },
      { path: '/login', name: 'login', component: blank },
      { path: '/forgot-password', name: 'forgot-password', component: blank },
      { path: '/reset-password', name: 'reset-password', component: blank },
      { path: '/app/:p(.*)*', component: blank },
    ],
  })
  await router.push(path)
  return router
}
const axiosError = (status: number, data: unknown) => Object.assign(new Error(String(status)), { isAxiosError: true, response: { status, data } })

beforeEach(() => {
  localStorage.clear()
  vi.mocked(api.get).mockReset()
  vi.mocked(api.post).mockReset()
  vi.mocked(api.patch).mockReset()
})
afterEach(() => vi.useRealTimers())

describe('Sign-up is one call', () => {
  it('registers with names, stores the returned tokens, never calls token/ or me PATCH', async () => {
    const router = await makeRouter('/login')
    vi.mocked(api.post).mockResolvedValue({ data: { access: 'acc', refresh: 'ref' } })
    vi.mocked(api.get).mockResolvedValue({ data: { id: 1, role: 'guest', full_name: 'Sita Devi Rai' } })
    const w = mount(AuthForm, { props: { mode: 'signup' }, global: { plugins: [router] } })
    await w.get('input[autocomplete="name"]').setValue('Sita Devi Rai')
    await w.get('input[type="email"]').setValue('Sita@x.co')
    for (const input of w.findAll('input[autocomplete="new-password"]')) await input.setValue('Long-enough-9')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledTimes(1)
    expect(api.post).toHaveBeenCalledWith('register/', { email: 'Sita@x.co', password: 'Long-enough-9', first_name: 'Sita', last_name: 'Devi Rai' })
    expect(api.patch).not.toHaveBeenCalled()
    expect(localStorage.getItem('access_token')).toBe('acc')
    expect(localStorage.getItem('refresh_token')).toBe('ref')
    expect(router.currentRoute.value.path).toBe('/') // guests stay on the public site
  })

  it('links "Forgot password?" with the typed email', async () => {
    const router = await makeRouter('/login')
    const w = mount(AuthForm, { props: { mode: 'login' }, global: { plugins: [router] } })
    await w.get('input[type="email"]').setValue('a@b.co')
    expect(w.get('a[href^="/forgot-password"]').attributes('href')).toBe('/forgot-password?email=a@b.co')
  })
})

describe('Password reset', () => {
  it('request step always confirms, without revealing whether the account exists', async () => {
    const router = await makeRouter('/forgot-password?email=a%40b.co')
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const w = mount(ResetForm, { props: { mode: 'request' }, global: { plugins: [router] } })
    expect((w.get('input[type="email"]').element as HTMLInputElement).value).toBe('a@b.co')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('password-reset/', { email: 'a@b.co' })
    expect(w.get('[role="status"]').text()).toContain('If a@b.co has an account')
  })

  it('confirm step strips the token from the URL, posts it, and returns to sign-in', async () => {
    const router = await makeRouter('/reset-password?uid=MQ&token=abc-123')
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const w = mount(ResetForm, { props: { mode: 'confirm' }, global: { plugins: [router] } })
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/reset-password')
    const [pw, confirm] = w.findAll('input[type="password"]')
    await pw!.setValue('Brand-New-Pass-42')
    await confirm!.setValue('Brand-New-Pass-42')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('password-reset/confirm/', { uid: 'MQ', token: 'abc-123', new_password: 'Brand-New-Pass-42' })
    expect(router.currentRoute.value.fullPath).toBe('/login?reset=1')
  })

  it('shows server password rules and handles a dead link', async () => {
    const router = await makeRouter('/reset-password?uid=MQ&token=t')
    vi.mocked(api.post).mockRejectedValueOnce(axiosError(400, { new_password: ['This password is too common.'] }))
    const w = mount(ResetForm, { props: { mode: 'confirm' }, global: { plugins: [router] } })
    for (const input of w.findAll('input[type="password"]')) await input.setValue('password123')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.text()).toContain('This password is too common.')

    vi.mocked(api.post).mockRejectedValueOnce(axiosError(400, { token: ['This reset link is invalid or has expired.'] }))
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.get('[role="alert"]').text()).toContain('invalid, already used, or expired')
    expect(w.get('a').attributes('href')).toBe('/forgot-password')
  })

  it('a link without uid/token is rejected up front', async () => {
    const router = await makeRouter('/reset-password')
    const w = mount(ResetForm, { props: { mode: 'confirm' }, global: { plugins: [router] } })
    expect(w.find('form').exists()).toBe(false)
    expect(w.text()).toContain('invalid, already used, or expired')
  })
})

describe('DataTable server mode', () => {
  type Row = { id: number; name: string }
  const rows: Row[] = [{ id: 1, name: 'B' }, { id: 2, name: 'A' }]
  const columns = [{ key: 'name', label: 'Name', sortable: true, orderBy: 'employee__first_name' }]

  it('renders the given page as-is and reports the server total', () => {
    const w = mount(DataTable, { props: { rows, columns, rowKey: (r: unknown) => (r as Row).id, caption: 'People', total: 25, pageSize: 10, page: 2 } })
    expect(w.findAll('tbody td').map((td) => td.text())).toEqual(['B', 'A']) // not re-sorted or sliced
    expect(w.text()).toContain('11–20 of 25')
    expect(w.text()).toContain('Page 2 / 3')
  })

  it('emits ordering with the server field, page changes, and a debounced search', async () => {
    vi.useFakeTimers()
    const w = mount(DataTable, { props: { rows, columns, rowKey: (r: unknown) => (r as Row).id, caption: 'People', total: 25, pageSize: 10 } })
    await w.get('th button').trigger('click')
    expect(w.emitted('update:ordering')![0]).toEqual(['employee__first_name'])
    await w.setProps({ ordering: 'employee__first_name' } as never)
    await w.get('th button').trigger('click')
    expect(w.emitted('update:ordering')![1]).toEqual(['-employee__first_name'])

    await w.findAll('nav button').find((b) => b.text().includes('Next'))!.trigger('click')
    expect(w.emitted('update:page')!.slice(-1)[0]).toEqual([2])

    await w.get('input[type="search"]').setValue('si')
    await w.get('input[type="search"]').setValue('sit')
    expect(w.emitted('update:search')).toBeUndefined()
    vi.advanceTimersByTime(300)
    expect(w.emitted('update:search')).toEqual([['sit']])
  })

  it('useServerTable fetches pages with filters and resets to page 1 when they change', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { count: 30, next: null, previous: null, results: [{ id: 1 }] } })
    const { ref } = await import('vue')
    const status = ref<string | undefined>()
    const t = useServerTable<{ id: number }>('finance/expenses/', { pageSize: 10, params: () => ({ status: status.value }) })
    await t.load()
    expect(api.get).toHaveBeenLastCalledWith('finance/expenses/', { params: { page: 1, page_size: 10, search: undefined, ordering: undefined, status: undefined } })
    expect(t.total.value).toBe(30)
    t.page.value = 3
    await flushPromises()
    expect(vi.mocked(api.get).mock.lastCall![1]).toMatchObject({ params: { page: 3 } })
    status.value = 'submitted'
    await flushPromises()
    expect(vi.mocked(api.get).mock.lastCall![1]).toMatchObject({ params: { page: 1, status: 'submitted' } })
  })
})

describe('NotificationBell', () => {
  const items = [
    { id: 1, kind: 'leave_decided', title: 'Your leave request was approved', body: '', link: '/app/leave', read_at: null, created_at: new Date().toISOString() },
    { id: 2, kind: 'payslip_issued', title: 'Payslip issued', body: 'Net pay', link: '', read_at: null, created_at: new Date().toISOString() },
  ]

  it('shows the unread badge, loads on open, marks read and follows the link', async () => {
    const router = await makeRouter('/app')
    vi.mocked(api.get).mockResolvedValue({ data: structuredClone(items) })
    vi.mocked(api.post).mockResolvedValue({ data: {} })
    const w = mount(NotificationBell, { props: { unread: 2 }, global: { plugins: [router] }, attachTo: document.body })
    expect(w.get('button[aria-haspopup]').attributes('aria-label')).toBe('Notifications, 2 unread')
    await w.get('button[aria-haspopup]').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith('notifications/')
    expect(w.findAll('[data-item]')).toHaveLength(2)

    await w.findAll('[data-item]')[0]!.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('notifications/1/read/')
    expect(w.emitted('changed')).toHaveLength(1)
    expect(router.currentRoute.value.path).toBe('/app/leave')
    w.unmount()
  })

  it('marks everything read', async () => {
    const router = await makeRouter('/app')
    vi.mocked(api.get).mockResolvedValue({ data: structuredClone(items) })
    vi.mocked(api.post).mockResolvedValue({ data: { marked: 2 } })
    const w = mount(NotificationBell, { props: { unread: 2 }, global: { plugins: [router] }, attachTo: document.body })
    await w.get('button[aria-haspopup]').trigger('click')
    await flushPromises()
    await w.findAll('button').find((b) => b.text() === 'Mark all read')!.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('notifications/read-all/')
    expect(w.findAll('[data-item] .bg-flag')).toHaveLength(0)
    w.unmount()
  })
})
