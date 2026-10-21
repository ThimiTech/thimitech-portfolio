import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'

vi.mock('../api/api', () => ({
  default: {
    get: vi.fn<() => Promise<unknown>>(() => Promise.resolve({ data: {} })),
    post: vi.fn<() => Promise<unknown>>(() => Promise.resolve({ data: {} })),
    patch: vi.fn<() => Promise<unknown>>(() => Promise.resolve({ data: {} })),
  },
}))

// Smoke test: the layout wraps every /app page, so a setup-time crash (e.g. an immediate watcher touching a ref
// declared later) blanks the whole workspace while page-level tests stay green.
describe('AppLayout', () => {
  it('mounts and renders the routed page', async () => {
    const errors: unknown[] = []
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/app/', component: { template: '<p>page body</p>' } }, { path: '/:p(.*)*', component: { template: '<div />' } }],
    })
    await router.push('/app/')
    const w = mount(AppLayout, {
      global: { plugins: [router], config: { errorHandler: (e) => errors.push(e) } },
      attachTo: document.body,
    })
    await flushPromises()
    expect(errors).toEqual([])
    expect(w.text()).toContain('page body')
    w.unmount()
  })
})
