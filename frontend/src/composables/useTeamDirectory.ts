/**
 * Shared team directory.
 *
 * The About section needs the team size and the Team section needs the people, so the
 * list is fetched once per page load and shared instead of requested twice.
 */
import { ref } from 'vue'
import api from '../api/api'

export interface TeamSocial {
  id: number
  platform: string
  url: string
}

export interface TeamMember {
  id: number
  name: string
  role: string
  initials?: string
  image?: string | null
  email?: string
  social_media?: TeamSocial[]
}

const members = ref<TeamMember[]>([])
const loading = ref(true)
const error = ref(false)
let requested = false

async function load(force = false) {
  if (requested && !force) return
  requested = true
  loading.value = true
  error.value = false
  try {
    const { data } = await api.get<TeamMember[]>('team/')
    members.value = Array.isArray(data) ? data : []
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

export function useTeamDirectory() {
  void load()
  return { members, loading, error, reload: () => load(true) }
}
