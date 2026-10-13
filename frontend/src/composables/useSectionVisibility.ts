import { inject, provide, reactive, type InjectionKey } from 'vue'

export const dataSections = {
  'services/': '#services',
  'projects/': '#projects',
  'team/': '#team',
  'jobs/': '#hiring',
} as const

const visibilityKey: InjectionKey<Record<string, boolean>> = Symbol('sectionVisibility')

export function provideSectionVisibility() {
  const visibility = reactive<Record<string, boolean>>({})
  provide(visibilityKey, visibility)
  return visibility
}

export function useSectionVisibility() {
  return inject(visibilityKey, reactive<Record<string, boolean>>({}))
}
