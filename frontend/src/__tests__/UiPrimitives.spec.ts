import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import DataTable from '../components/app/ui/DataTable.vue'
import CommandPalette from '../components/app/ui/CommandPalette.vue'
import TabBar from '../components/app/ui/TabBar.vue'
import ToastHost from '../components/app/ui/ToastHost.vue'
import { toast, toasts } from '../components/app/ui/toast'
import AuthForm from '../components/auth/AuthForm.vue'
import api from '../api/api'

vi.mock('../api/api', () => ({
  default: { get: vi.fn<() => Promise<unknown>>(), post: vi.fn<() => Promise<unknown>>(), patch: vi.fn<() => Promise<unknown>>() },
}))

type Row = { id: number; name: string; qty: number }
const rows: Row[] = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, name: `Item ${String.fromCharCode(76 - i)}`, qty: (i * 7) % 5 }))
const columns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'qty', label: 'Qty', sortable: true },
]

describe('DataTable', () => {
  const mountTable = () =>
    mount(DataTable, {
      props: { rows, columns, rowKey: (r: unknown) => (r as Row).id, caption: 'Items', searchText: (r: unknown) => (r as Row).name, pageSize: 5 },
    })

  it('paginates, sorts with aria-sort, and searches', async () => {
    const w = mountTable()
    expect(w.findAll('tbody tr')).toHaveLength(5)
    expect(w.text()).toContain('1–5 of 12')

    await w.findAll('th button')[0]!.trigger('click')
    expect(w.findAll('th')[0]!.attributes('aria-sort')).toBe('ascending')
    expect(w.find('tbody td').text()).toBe('Item A')
    await w.findAll('th button')[0]!.trigger('click')
    expect(w.findAll('th')[0]!.attributes('aria-sort')).toBe('descending')
    expect(w.find('tbody td').text()).toBe('Item L')

    await w.findAll('nav button').find((b) => b.text().includes('Next'))!.trigger('click')
    expect(w.text()).toContain('6–10 of 12')

    await w.get('input[type="search"]').setValue('item c')
    expect(w.findAll('tbody tr')).toHaveLength(1)
    expect(w.find('nav').exists()).toBe(false) // single page, back to page 1
  })

  it('shows an empty state with a clear-search action', async () => {
    const w = mountTable()
    await w.get('input[type="search"]').setValue('zzz')
    expect(w.find('table').exists()).toBe(false)
    expect(w.text()).toContain('No matches')
    await w.findAll('button').find((b) => b.text() === 'Clear search')!.trigger('click')
    expect(w.findAll('tbody tr')).toHaveLength(5)
  })
})

describe('CommandPalette', () => {
  it('filters by label and keywords and selects with Enter', async () => {
    const commands = [
      { id: 'a', label: 'Attendance', group: 'Daily', keywords: 'check in' },
      { id: 'l', label: 'Leave', group: 'Daily', keywords: 'time off' },
      { id: 'f', label: 'Finance', group: 'Administration', keywords: 'payroll' },
    ]
    const w = mount(CommandPalette, { props: { open: false, commands }, attachTo: document.body })
    await w.setProps({ open: true })
    const input = document.querySelector<HTMLInputElement>('input[role="combobox"]')!
    input.value = 'payroll'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(document.querySelectorAll('[role="option"]')).toHaveLength(1)
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(w.emitted('select')![0]![0]).toMatchObject({ id: 'f' })
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })
})

describe('TabBar', () => {
  it('moves selection with arrow keys (roving tabindex)', async () => {
    const tabs = [
      { id: 'a', label: 'A' },
      { id: 'b', label: 'B' },
      { id: 'c', label: 'C' },
    ]
    const w = mount(TabBar, {
      props: { tabs, label: 'Views', idPrefix: 't', modelValue: 'a', 'onUpdate:modelValue': (v: string) => w.setProps({ modelValue: v }) },
    })
    await w.findAll('[role="tab"]')[0]!.trigger('keydown', { key: 'ArrowLeft' })
    expect(w.props('modelValue')).toBe('c')
    expect(w.findAll('[role="tab"]')[2]!.attributes('tabindex')).toBe('0')
    expect(w.findAll('[role="tab"]')[0]!.attributes('tabindex')).toBe('-1')
  })
})

describe('Toasts', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    vi.useRealTimers()
    toasts.splice(0)
  })

  it('announces politely and auto-dismisses', async () => {
    const w = mount(ToastHost)
    toast.success('Saved.')
    await flushPromises()
    expect(w.get('[aria-live="polite"]').text()).toContain('Saved.')
    vi.advanceTimersByTime(4100)
    expect(toasts).toHaveLength(0)
  })
})

describe('AuthForm', () => {
  const makeRouter = (path: string) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/login', name: 'login', component: { template: '<div />' } },
        { path: '/app/:p(.*)*', component: { template: '<div />' } },
      ],
    })
    return router.push(path).then(() => router)
  }
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('validates before calling the API and focuses the first invalid field', async () => {
    const router = await makeRouter('/login')
    const w = mount(AuthForm, { props: { mode: 'login' }, global: { plugins: [router] }, attachTo: document.body })
    await w.get('input[type="email"]').setValue('not-an-email')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).not.toHaveBeenCalled()
    expect(w.text()).toContain("doesn't look like an email")
    expect(w.text()).toContain('Enter your password')
    expect(document.activeElement).toBe(w.get('input[type="email"]').element)
    w.unmount()
  })

  it('maps a 401 to a clear message', async () => {
    const router = await makeRouter('/login')
    vi.mocked(api.post).mockRejectedValue(Object.assign(new Error('401'), { isAxiosError: true, response: { status: 401, data: { detail: 'No active account' } } }))
    const w = mount(AuthForm, { props: { mode: 'login' }, global: { plugins: [router] } })
    await w.get('input[type="email"]').setValue('a@b.co')
    await w.get('input[type="password"]').setValue('secret')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.get('[role="alert"]').text()).toContain("don't match an active account")
  })

  it('toggles password visibility', async () => {
    const router = await makeRouter('/login')
    const w = mount(AuthForm, { props: { mode: 'login' }, global: { plugins: [router] } })
    const toggle = w.get('button[aria-label="Show password"]')
    await toggle.trigger('click')
    expect(w.find('input[autocomplete="current-password"]').attributes('type')).toBe('text')
    expect(w.get('button[aria-label="Hide password"]').attributes('aria-pressed')).toBe('true')
  })

  it('signs in and returns to the requested /app route, ignoring off-site next', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { access: 'a', refresh: 'r' } })
    vi.mocked(api.get).mockResolvedValue({ data: { id: 1, role: 'employee', full_name: 'Sita' } })
    for (const [next, expected] of [
      ['/app/leave?tab=approvals', '/app/leave?tab=approvals'],
      ['//evil.example', '/app'],
    ]) {
      const router = await makeRouter(`/login?next=${encodeURIComponent(next!)}`)
      const w = mount(AuthForm, { props: { mode: 'login' }, global: { plugins: [router] } })
      await w.get('input[type="email"]').setValue('sita@thimitech.com')
      await w.get('input[type="password"]').setValue('secret')
      await w.get('form').trigger('submit')
      await flushPromises()
      expect(router.currentRoute.value.fullPath).toBe(expected)
      w.unmount()
    }
  })

  it('shows field errors returned by registration', async () => {
    const router = await makeRouter('/login')
    vi.mocked(api.post).mockRejectedValue(
      Object.assign(new Error('400'), { isAxiosError: true, response: { status: 400, data: { email: ['user with this email already exists.'] } } }),
    )
    const w = mount(AuthForm, { props: { mode: 'signup' }, global: { plugins: [router] } })
    await w.get('input[autocomplete="name"]').setValue('Sita Rai')
    await w.get('input[type="email"]').setValue('sita@thimitech.com')
    await w.get('input[autocomplete="new-password"]').setValue('longenough')
    await w.findAll('input[autocomplete="new-password"]')[1]!.setValue('longenough')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.text()).toContain('user with this email already exists.')
    expect(w.get('input[type="email"]').attributes('aria-invalid')).toBe('true')
  })
})
