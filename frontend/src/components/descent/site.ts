/**
 * What the landing page reads from the backend: the organization's public profile
 * (`/api/org/public/`) and the published case studies (`/api/pm/public/`).
 * Fetched once per page load and shared by every section. The fallback copy is what
 * shows while loading, offline, or for a field HR has left empty.
 */
import { ref } from 'vue'
import api from '../../api/api'

export interface CaseCard {
  slug: string
  name: string
  key: string
  tagline: string
  cover: string | null
  tech: string[]
  start_date: string | null
  published_at: string | null
}

const FALLBACK = {
  name: 'Thimi Tech',
  tagline: 'Web GIS, software and AI from the Kathmandu valley.',
  email: 'info@thimitech.com',
  phone: '',
  address: 'Madhyapur Thimi, Bhaktapur, Nepal',
  website: '',
  github: '',
  linkedin: '',
  youtube: '',
  founded: '2021-01-01',
  founder_name: 'Ravi Prajapati',
  founder_title: 'Founder & CEO',
  founder_photo: '',
  founder_quote: 'Thimi has shaped clay for a thousand years. We are learning to shape data with the same patience.',
  founder_message:
    'Thimi Tech is still being built, and I would rather say that plainly than pretend we have arrived. Every week we ship something, find out what we got wrong, and fix it before the next one.\n\nWe take on work we can stand behind, we stay with our clients long after launch, and we invest in people from this valley who want to do world-class engineering without leaving it. If we keep doing that, one honest project at a time, the company takes care of itself.',
  stats: null as { people: number; projects: number; open_roles: number } | null,
}

export const site = ref({ ...FALLBACK })
export const cases = ref<CaseCard[]>([])
export const casesState = ref<'loading' | 'ready' | 'failed'>('loading')

export async function loadCases() {
  casesState.value = 'loading'
  try {
    const { data } = await api.get<CaseCard[]>('pm/public/')
    cases.value = Array.isArray(data) ? data : []
    casesState.value = 'ready'
  } catch {
    casesState.value = 'failed'
  }
}

let requested = false
export function useSite() {
  if (!requested) {
    requested = true
    void loadCases()
    api
      .get<Partial<typeof FALLBACK>>('org/public/')
      .then(({ data }) => {
        if (!data || Array.isArray(data)) return
        // an empty field keeps its fallback
        const filled = Object.fromEntries(Object.entries(data).filter(([, v]) => v !== '' && v != null))
        site.value = { ...FALLBACK, ...filled }
      })
      .catch(() => undefined)
  }
  return { site, cases, casesState }
}
