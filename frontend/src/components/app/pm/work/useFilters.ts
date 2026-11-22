/** Quick filters shared by the board, backlog and list views (search, people, type, epic, "only my issues"),
 *  kept in the URL so a filtered view can be shared or bookmarked. */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Task } from '../pm'
import { ancestors } from './meta'
import { useWorkspace } from './workspace'

export function useFilters() {
  const ws = useWorkspace()
  const route = useRoute()
  const router = useRouter()
  const q = (k: string) => (typeof route.query[k] === 'string' ? (route.query[k] as string) : '')
  const set = (k: string, v: string | null) => {
    const query = { ...route.query }
    if (v) query[k] = v
    else delete query[k]
    router.replace({ query })
  }
  const field = (k: string) => computed({ get: () => q(k), set: (v: string) => set(k, v || null) })

  const search = field('q')
  const type = field('type')
  /** An epic or module id: shows everything beneath it. */
  const within = field('in')
  const people = computed({
    get: () => q('people').split(',').filter(Boolean).map(Number),
    set: (ids: number[]) => set('people', ids.join(',') || null),
  })
  const mine = computed({ get: () => q('mine') === '1', set: (v: boolean) => set('mine', v ? '1' : null) })
  const recent = computed({ get: () => q('recent') === '1', set: (v: boolean) => set('recent', v ? '1' : null) })

  function togglePerson(id: number) {
    people.value = people.value.includes(id) ? people.value.filter((x) => x !== id) : [...people.value, id]
  }
  const active = computed(() => !!(search.value || type.value || within.value || people.value.length || mine.value || recent.value))
  function clear() {
    const query = { ...route.query }
    for (const k of ['q', 'type', 'in', 'people', 'mine', 'recent']) delete query[k]
    router.replace({ query })
  }
  const day = 86_400_000
  function matches(t: Task) {
    const s = search.value.trim().toLowerCase()
    if (s && !`${t.key} ${t.title} ${t.labels.join(' ')} ${t.assignee_name || ''}`.toLowerCase().includes(s)) return false
    if (type.value && t.type !== type.value) return false
    if (people.value.length && !people.value.includes(t.assignee ?? 0)) return false
    if (mine.value && t.assignee !== ws.me) return false
    if (recent.value && (!t.updated_at || Date.now() - Date.parse(t.updated_at) > day)) return false
    if (within.value && !ancestors(t, ws.byId).some((a) => a.id === Number(within.value))) return false
    return true
  }
  return { search, type, within, people, mine, recent, togglePerson, active, clear, matches }
}
