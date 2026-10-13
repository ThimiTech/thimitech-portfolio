import { computed, onMounted, shallowRef } from 'vue'
import api from '../api/api'
import { dataSections, useSectionVisibility } from './useSectionVisibility'

/** Publish a section only after its collection has loaded successfully. */
export function useApiCollection<T>(endpoint: string) {
  const visibility = useSectionVisibility()
  const section = dataSections[endpoint as keyof typeof dataSections]
  const items = shallowRef<T[]>([])
  const visible = computed(() => items.value.length > 0)

  onMounted(async () => {
    try {
      const { data } = await api.get<T[] | { results: T[] }>(endpoint)
      const collection = Array.isArray(data) ? data : data?.results
      items.value = Array.isArray(collection) ? collection : []
    } catch {
      items.value = []
    } finally {
      if (section) visibility[section] = visible.value
    }
  })

  return { items, visible }
}
