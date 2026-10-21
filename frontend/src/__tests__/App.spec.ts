import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../App.vue'
import LandingPage from '../pages/LandingPage.vue'
import NewLandingPage from '../pages/NewLandingPage.vue'
import api from '../api/api'
vi.mock('../api/api', () => ({ default: { get: vi.fn<() => Promise<unknown>>() } }))
beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (url) => ({
    data:
      url === 'services/' ? [{ id: 1, title: 'Web GIS', description: 'Maps people can use.' }] : [],
  }))
})
describe('Public portfolio', () => {
  it.each([
    ['/', 'Turning Geographic Data into Digital Solutions.', 'See our work'],
    ['/new', 'From place to possibility.', 'Explore our work'],
  ])('renders the correct public design at %s', async (path, heading, workLink) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: LandingPage }, { path: '/new', component: NewLandingPage }],
    })
    await router.push(path)
    const wrapper = mount(App, { global: { plugins: [router], stubs: { TerrainScene: true, NepalMap: true } } })
    await flushPromises()
    expect(wrapper.findAll('h1')).toHaveLength(1)
    expect(wrapper.find('h1').text()).toBe(heading)
    expect(wrapper.text()).toContain('Web GIS')
    expect(wrapper.findAll('a[href="#projects"]').some(a => a.text().includes(workLink))).toBe(true)
    wrapper.unmount()
  })
  it('keeps /new links and skip link on the new design', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/new', component: NewLandingPage }] })
    await router.push('/new')
    const wrapper = mount(App, { global: { plugins: [router], stubs: { TerrainScene: true, NepalMap: true } } })
    await flushPromises()
    expect(wrapper.find('a[href="#main-content"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/new#contact"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/#contact"]').exists()).toBe(false)
    wrapper.unmount()
  })
  it('shows a retry when service loading fails', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('offline'))
    const { default: Services } = await import('../components/Services.vue')
    const wrapper = mount(Services)
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('temporarily unavailable')
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Web GIS')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
