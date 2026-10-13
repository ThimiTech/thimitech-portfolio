import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Services from '../components/Services.vue'
import Projects from '../components/Projects.vue'
import Team from '../components/Team.vue'
import Hiring from '../components/Hiring.vue'
import api from '../api/api'

vi.mock('../api/api', () => ({ default: { get: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const item = { id: 1, name: 'Existing name', title: 'Existing title', description: 'Existing description', role: 'Engineer' }

describe.each([
  ['services', Services],
  ['projects', Projects],
  ['team', Team],
  ['hiring', Hiring],
] as const)('%s section', (id, component) => {
  const render = () => mount(component, { global: { stubs: { RouterLink: true } } })

  it('stays hidden while loading and after a backend failure', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('Offline'))
    const wrapper = render()
    expect(wrapper.find('section').exists()).toBe(false)
    await flushPromises()
    expect(wrapper.find('section').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([[], { results: [] }, null, { detail: 'Invalid response' }])('hides an empty or malformed response %j', async (data) => {
    vi.mocked(api.get).mockResolvedValueOnce({ data })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.find('section').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([[item], { results: [item] }])('shows existing content from a successful response %j', async (data) => {
    vi.mocked(api.get).mockResolvedValueOnce({ data })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.find(`#${id}`).exists()).toBe(true)
    expect(wrapper.text()).toContain(id === 'team' || id === 'projects' ? item.name : item.title)
    wrapper.unmount()
  })
})
