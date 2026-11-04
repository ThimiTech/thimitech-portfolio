import api from '@/api/api'
import type { Doc } from '../pm/pm'
import type { Level } from '@/stores/auth'

export type SpaceId = 'company' | 'finance' | 'people'
export interface Space {
  id: SpaceId
  label: string
  files: number
  size: number
  can_write: boolean
  can_share: boolean
}
export interface FolderRef {
  id: number
  space: SpaceId
  parent: number | null
  name: string
  fiscal_year: string
  classification: Level
  path: { id: number; name: string }[]
  file_count?: number
  folder_count?: number
}
export interface DriveFile {
  id: number
  space: SpaceId
  folder: number | null
  folder_name: string
  name: string
  title: string
  extension: string
  size: number
  description: string
  fiscal_year: string
  classification: Level
  employee: number | null
  employee_name: string
  project: number | null
  project_name: string
  transaction: number | null
  transaction_label: string
  expense: number | null
  invoice: number | null
  statement: number | null
  uploaded_by_name: string
  created_at: string
  updated_at: string
  url: string
}
export interface Browse {
  mode: 'folder' | 'search'
  space: SpaceId | null
  folder: FolderRef | null
  folders: FolderRef[]
  files: DriveFile[]
  can_write: boolean
}
export interface ShareLink {
  id: number
  token: string
  folder: number | null
  file: number | null
  label: string
  expires_at: string
  revoked_at: string | null
  created_by_name: string
  created_at: string
  target_name: string
  active: boolean
}

export const SPACE_HINT: Record<SpaceId, string> = {
  company: 'Shared with everyone: letterheads, logos, email signatures, templates, policies.',
  finance: 'Finance team and CA only: bank statements, salary slips, SSF, tax, audit files.',
  people: 'HR only: offer letters, experience letters, contracts. Each person can see files linked to them.',
}

/** Shape pm's DocViewer expects. */
export function asDoc(f: { id: number; name: string; extension: string; size: number; url: string; description?: string; folder_name?: string; uploaded_by_name?: string }): Doc {
  return { ...f, title: f.name, file: f.name, folder: f.folder_name || '', uploaded_by_name: f.uploaded_by_name || '', public: false, description: f.description || '' } as unknown as Doc
}

/** Upload one file; extra fields become links (employee, transaction, fiscal_year, relative_path…). */
export async function uploadFile(file: File, fields: Record<string, string | number | null | undefined>, onProgress?: (pct: number) => void) {
  const form = new FormData()
  form.append('file', file)
  for (const [k, v] of Object.entries(fields)) if (v !== null && v !== undefined && v !== '') form.append(k, String(v))
  return (await api.post<DriveFile>('drive/files/', form, { onUploadProgress: (e) => onProgress?.(Math.round(((e.loaded || 0) / (e.total || 1)) * 100)) })).data
}

const ICON: Record<string, string> = { pdf: 'PDF', doc: 'DOC', docx: 'DOC', xls: 'XLS', xlsx: 'XLS', csv: 'CSV', png: 'IMG', jpg: 'IMG', jpeg: 'IMG', gif: 'IMG', webp: 'IMG', zip: 'ZIP', ppt: 'PPT', pptx: 'PPT', txt: 'TXT', md: 'TXT' }
export const fileBadge = (ext: string) => ICON[ext] || (ext || 'file').slice(0, 4).toUpperCase()
export const BADGE_TONE: Record<string, string> = { PDF: 'bg-rust/12 text-rust', DOC: 'bg-sky/12 text-sky', XLS: 'bg-moss/12 text-moss', CSV: 'bg-moss/12 text-moss', IMG: 'bg-contour/15 text-contour-ink' }
