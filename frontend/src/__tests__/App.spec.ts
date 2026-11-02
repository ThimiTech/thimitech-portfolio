import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../App.vue'
import LandingPage from '../pages/LandingPage.vue'
import NewLandingPage from '../pages/NewLandingPage.vue'
import api from '../api/api'

vi.mock('../api/api', () => ({ default: { get: vi.fn<() => Promise<unknown>>() } }))

const PROJECT = {
  id: 1,
  name: 'Bagmati Geospatial Data Center',
  subtitle: 'Data management',
  description: 'A centralised spatial data platform.',
  image: null,
  url: '',
}

beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (url) => ({
    data: url === 'projects/' ? [PROJECT] : [],
  }))
})

describe('Public portfolio', () => {
  it.each([
    ['/', 'Turning Geographic Data into Digital Solutions.', 'See our work', '#projects'],
    ['/new', 'From place to possibility.', 'Explore our work', '/new#projects'],
  ])('renders the correct public design at %s', async (path, heading, workLink, workHref) => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: LandingPage }, { path: '/new', component: NewLandingPage }],
    })
    await router.push(path)
    const wrapper = mount(App, {
      global: { plugins: [router], stubs: { GlobeScene: true } },
    })
    await flushPromises()
    expect(wrapper.findAll('h1')).toHaveLength(1)
    expect(wrapper.find('h1').text()).toBe(heading)
    // Services are frontend content — no API call involved.
    expect(wrapper.text()).toContain('WebGIS Development & Geospatial Solutions')
    expect(wrapper.text()).toContain('Data Analytics & Business Intelligence')
    expect(
      wrapper.findAll(`a[href="${workHref}"]`).some((a) => a.text().includes(workLink)),
    ).toBe(true)
    wrapper.unmount()
  })
  it('keeps /new links and skip link on the new design', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/new', component: NewLandingPage }],
    })
    await router.push('/new')
    const wrapper = mount(App, {
      global: { plugins: [router], stubs: { GlobeScene: true } },
    })
    await flushPromises()
    expect(wrapper.find('a[href="#main-content"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/new#contact"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/#contact"]').exists()).toBe(false)
    expect(wrapper.find('a[href="/new#projects"]').exists()).toBe(true)
    wrapper.unmount()
  })
  it('shows a retry when the project list fails to load', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('offline'))
    const { default: Projects } = await import('../components/Projects.vue')
    const wrapper = mount(Projects, {
      // renderStubDefaultSlot keeps the project name (inside RouterLink) in the output
      global: { stubs: { RouterLink: true }, renderStubDefaultSlot: true },
    })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('couldn’t load our projects')
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Bagmati Geospatial Data Center')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
