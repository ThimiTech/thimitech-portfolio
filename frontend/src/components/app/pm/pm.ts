import { isAxiosError } from 'axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/api'

export interface Person {
  id: number
  name: string
}
export interface Column {
  id: number
  board: number
  name: string
  position: number
  status: string
}
export interface Board {
  id: number
  project: number
  name: string
  columns: Column[]
}
export interface Project {
  id: number
  name: string
  key: string
  description: string
  lead: number
  members: number[]
  people: Person[]
  boards: Board[]
  start_date: string | null
  due_date: string | null
  archived: boolean
  can_manage: boolean
  progress: { total: number; done: number; percent: number }
  health: Health
  visibility: 'private' | 'public'
  slug: string | null
  tagline: string
  cover: string | null
  story: string
  tech: string[]
  public_sections: string[]
  published_at: string | null
}
export type Health = 'on_track' | 'at_risk' | 'off_track'
export const HEALTH: Record<Health, { label: string; pill: string }> = {
  on_track: { label: 'On track', pill: 'done' },
  at_risk: { label: 'At risk', pill: 'review' },
  off_track: { label: 'Off track', pill: 'overdue' },
}
export interface Task {
  id: number
  key: string
  project: number
  board: number
  title: string
  description: string
  column: number
  status: string
  assignee: number | null
  assignee_name: string | null
  priority: string
  estimate: number | null
  labels: string[]
  position: number
  milestone: number | null
  sprint: number | null
  start_date: string | null
  due_date: string | null
  completed_at: string | null
}
export interface Milestone {
  id: number
  project: number
  title: string
  due_date: string
  completed: boolean
}
export interface ProjectLink {
  id: number
  title: string
  kind: string
  url: string
  public: boolean
}
export interface Sprint {
  id: number
  project: number
  name: string
  goal: string
  start_date: string
  end_date: string
  status: 'planned' | 'active' | 'completed'
  completed_at: string | null
}
export interface Doc {
  id: number
  project: number
  title: string
  folder: string
  description: string
  file: string
  url: string
  extension: string
  size: number
  public: boolean
  uploaded_by: number
  uploaded_by_name: string
  can_edit: boolean
  created_at: string
  updated_at: string
}
export interface Note {
  id: number
  project: number
  title: string
  body: string
  pinned: boolean
  author: number
  author_name: string
  updated_by_name: string | null
  created_at: string
  updated_at: string
}
export interface ActionItem {
  text: string
  assignee: number | null
  due: string | null
  task: number | null
  done: boolean
}
export interface Meeting {
  id: number
  project: number
  title: string
  kind: string
  start: string
  end: string
  location: string
  agenda: string
  minutes: string
  action_items: ActionItem[]
  status: 'scheduled' | 'done' | 'cancelled'
  attendees: number[]
  attendees_detail: Person[]
  created_by: number
  created_by_name: string
  updated_at: string
}
export interface WbElement {
  id: string
  type: 'sticky' | 'rect' | 'ellipse' | 'text' | 'pen' | 'arrow'
  x: number
  y: number
  w: number
  h: number
  color: string
  text?: string
  points?: number[]
}
export interface Whiteboard {
  id: number
  project: number
  title: string
  data: { elements?: WbElement[] }
  version: number
  updated_by_name: string | null
  updated_at: string
}

export const MEETING_KINDS: Record<string, string> = {
  standup: 'Stand-up',
  planning: 'Sprint planning',
  review: 'Sprint review',
  retro: 'Retrospective',
  client: 'Client',
  general: 'General',
}

// ───────────── Links ─────────────
export const LINK_KINDS: { id: string; label: string; match?: RegExp }[] = [
  { id: 'github', label: 'GitHub', match: /github\.com/ },
  { id: 'gitlab', label: 'GitLab', match: /gitlab\./ },
  { id: 'youtube', label: 'YouTube', match: /youtube\.com|youtu\.be/ },
  { id: 'figma', label: 'Figma', match: /figma\.com/ },
  { id: 'drive', label: 'Drive', match: /drive\.google|docs\.google|onedrive|dropbox/ },
  { id: 'linkedin', label: 'LinkedIn', match: /linkedin\.com/ },
  { id: 'facebook', label: 'Facebook', match: /facebook\.com|fb\.com/ },
  { id: 'instagram', label: 'Instagram', match: /instagram\.com/ },
  { id: 'x', label: 'X / Twitter', match: /(^|\.)x\.com|twitter\.com/ },
  { id: 'discord', label: 'Discord', match: /discord\.(gg|com)/ },
  { id: 'slack', label: 'Slack', match: /slack\.com/ },
  { id: 'store', label: 'App store', match: /apps\.apple\.com|play\.google\.com/ },
  { id: 'docs', label: 'Documentation', match: /readthedocs|notion\.so|confluence|gitbook/ },
  { id: 'web', label: 'Website' },
  { id: 'other', label: 'Other' },
]
export function detectLinkKind(url: string) {
  try {
    const host = new URL(url).hostname
    return LINK_KINDS.find((k) => k.match?.test(host))?.id || 'web'
  } catch {
    return 'web'
  }
}
export const linkLabel = (kind: string) => LINK_KINDS.find((k) => k.id === kind)?.label || kind

// ───────────── Markdown + [[wikilinks]] ─────────────
const WIKILINK = /\[\[([^\]|\n]+)(?:\|([^\]\n]+))?\]\]/g

/** Targets referenced as [[Target]] or [[Target|alias]] (trimmed, in order, unique). */
export function wikilinks(text: string) {
  return [...new Set([...text.matchAll(WIKILINK)].map((m) => m[1]!.trim()))]
}

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && /^https?:/i.test(node.getAttribute('href') || '')) {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** Sanitized HTML. Wikilinks become <a href="#wiki:Target"> for the caller to intercept. */
export function renderMarkdown(text: string) {
  const linked = text.replace(
    WIKILINK,
    (_, target: string, alias?: string) => `[${(alias || target).trim()}](#wiki:${encodeURIComponent(target.trim())})`,
  )
  return DOMPurify.sanitize(marked.parse(linked, { async: false, gfm: true, breaks: true }))
}

// ───────────── Knowledge graph ─────────────
export type NodeKind = 'note' | 'doc' | 'task' | 'meeting' | 'ghost'
export interface GraphNode {
  id: string
  label: string
  kind: NodeKind
  ref: number | null
}
export interface GraphEdge {
  source: string
  target: string
}

/** Resolve a wikilink target: note title → document title → task key → meeting title (case-insensitive). */
export function resolveLink(target: string, notes: Note[], docs: Doc[], tasks: Task[], meetings: Meeting[]): GraphNode {
  const t = target.toLowerCase()
  const note = notes.find((n) => n.title.toLowerCase() === t)
  if (note) return { id: `note:${note.id}`, label: note.title, kind: 'note', ref: note.id }
  const doc = docs.find((d) => d.title.toLowerCase() === t)
  if (doc) return { id: `doc:${doc.id}`, label: doc.title, kind: 'doc', ref: doc.id }
  const task = tasks.find((x) => x.key.toLowerCase() === t)
  if (task) return { id: `task:${task.id}`, label: `${task.key} ${task.title}`, kind: 'task', ref: task.id }
  const meeting = meetings.find((m) => m.title.toLowerCase() === t)
  if (meeting) return { id: `meeting:${meeting.id}`, label: meeting.title, kind: 'meeting', ref: meeting.id }
  return { id: `ghost:${t}`, label: target, kind: 'ghost', ref: null }
}

/** Every note and document, plus whatever notes/meetings link to (tasks, meetings, unresolved "ghost" notes). */
export function buildGraph(notes: Note[], docs: Doc[], tasks: Task[], meetings: Meeting[]) {
  const nodes = new Map<string, GraphNode>()
  const edges = new Map<string, GraphEdge>()
  for (const n of notes) nodes.set(`note:${n.id}`, { id: `note:${n.id}`, label: n.title, kind: 'note', ref: n.id })
  for (const d of docs) nodes.set(`doc:${d.id}`, { id: `doc:${d.id}`, label: d.title, kind: 'doc', ref: d.id })
  const sources: [GraphNode, string][] = [
    ...notes.map((n) => [nodes.get(`note:${n.id}`)!, n.body] as [GraphNode, string]),
    ...meetings.map(
      (m) =>
        [{ id: `meeting:${m.id}`, label: m.title, kind: 'meeting', ref: m.id }, `${m.agenda}\n${m.minutes}`] as [GraphNode, string],
    ),
  ]
  for (const [from, text] of sources) {
    for (const target of wikilinks(text)) {
      const to = resolveLink(target, notes, docs, tasks, meetings)
      if (to.id === from.id) continue
      nodes.set(from.id, nodes.get(from.id) || from)
      nodes.set(to.id, nodes.get(to.id) || to)
      const key = [from.id, to.id].sort().join('|')
      edges.set(key, { source: from.id, target: to.id })
    }
  }
  return { nodes: [...nodes.values()], edges: [...edges.values()] }
}

// ───────────── Files ─────────────
export const PREVIEW = { image: ['png', 'jpg', 'jpeg', 'gif', 'webp'], pdf: ['pdf'], markdown: ['md'], text: ['txt', 'csv'] }
export function previewKind(ext: string) {
  return (Object.keys(PREVIEW) as (keyof typeof PREVIEW)[]).find((k) => PREVIEW[k].includes(ext)) || null
}
/** Documents need the JWT, so they are fetched as blobs (not linked directly). `url` is the API path from the serializer. */
export async function fetchBlob(url: string, download = false) {
  const path = url.replace(/^\/api\//, '')
  return (await api.get<Blob>(path, { responseType: 'blob', params: download ? { download: 1 } : {} })).data
}
export async function downloadDoc(doc: Doc) {
  const href = URL.createObjectURL(await fetchBlob(doc.url, true))
  const a = Object.assign(document.createElement('a'), { href, download: doc.file })
  a.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

// ───────────── Misc ─────────────
export function fileSize(bytes: number) {
  return bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1048576).toFixed(1)} MB`
}
export function dateTimeLabel(iso: string) {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Kathmandu',
  }).format(new Date(iso))
}
/** ISO → value for <input type="datetime-local"> in the browser's zone. */
export function toLocalInput(iso: string) {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
export const DAY_MS = 86400000
export const dayNum = (ymd: string) => Date.parse(ymd + 'T00:00:00Z') / DAY_MS
export const ymdOf = (day: number) => new Date(day * DAY_MS).toISOString().slice(0, 10)
export interface Comment {
  id: number
  author: number
  author_name: string
  body: string
  created_at: string
}
export interface Summary {
  projects: number
  tasks: number
  done: number
  active: number
  overdue: number
  assigned_to_me: number
}

export function errorMessage(error: unknown) {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data
    if (typeof data === 'object')
      return Object.entries(data)
        .map(
          ([key, value]) =>
            `${key === 'detail' ? '' : key + ': '}${Array.isArray(value) ? value.join(' ') : String(value)}`,
        )
        .join(' ')
  }
  return 'Could not save your changes. Please try again.'
}
export function dateLabel(date: string | null) {
  return date
    ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
        new Date(date + 'T00:00:00Z'),
      )
    : 'No due date'
}
export function todayNPT() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kathmandu' }).format(new Date())
}
export function isOverdue(task: Task) {
  return !!task.due_date && task.due_date < todayNPT() && task.status !== 'done'
}
