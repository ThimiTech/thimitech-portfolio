import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import NavBar from '../components/NavBar.vue'
import Services from '../components/Services.vue'
import Projects from '../components/Projects.vue'
import Team from '../components/Team.vue'
import Hiring from '../components/Hiring.vue'
import { provideSectionVisibility } from '../composables/useSectionVisibility'
import api from '../api/api'

vi.mock('../components/Login.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../api/api', () => ({ default: { get: vi.fn() } }))

const Page = defineComponent({
  components: { NavBar, Services, Projects, Team, Hiring },
  setup() { provideSectionVisibility() },
  template: '<NavBar /><Services /><Projects /><Team /><Hiring />',
})

describe('section navigation', () => {
  it('matches available sections in desktop and mobile navigation', async () => {
    vi.mocked(api.get).mockImplementation(async (endpoint) => {
      if (endpoint === 'services/') return { data: [{ id: 1, title: 'Service', description: 'Description' }] }
      if (endpoint === 'projects/') throw new Error('Offline')
      if (endpoint === 'team/') return { data: [] }
      return { data: { results: [{ id: 1, title: 'Job', description: 'Description' }] } }
    })
    const wrapper = mount(Page, { global: { stubs: { Login: true, RouterLink: true } } })
    expect(wrapper.find('a[href="#services"]').exists()).toBe(false)
    await flushPromises()
    expect(wrapper.find('#services').exists()).toBe(true)
    expect(wrapper.find('#hiring').exists()).toBe(true)
    expect(wrapper.find('#projects').exists()).toBe(false)
    expect(wrapper.find('#team').exists()).toBe(false)
    await wrapper.get('button[aria-label="Menu"]').trigger('click')
    for (const section of ['services', 'hiring']) expect(wrapper.findAll(`a[href="#${section}"]`)).toHaveLength(2)
    for (const section of ['projects', 'team']) expect(wrapper.findAll(`a[href="#${section}"]`)).toHaveLength(0)
    expect(wrapper.findAll('a[href="#about"]')).toHaveLength(2)
    wrapper.unmount()
  })
})
