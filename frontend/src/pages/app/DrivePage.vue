<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/api'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import Modal from '@/components/app/ui/Modal.vue'
import EmptyState from '@/components/app/ui/EmptyState.vue'
import { confirmDialog } from '@/components/app/ui/confirm'
import { toast } from '@/components/app/ui/toast'
import DocViewer from '@/components/app/pm/DocViewer.vue'
import { downloadDoc, errorMessage, fileSize, type Doc } from '@/components/app/pm/pm'
import ShareDialog from '@/components/app/drive/ShareDialog.vue'
import MoveDialog from '@/components/app/drive/MoveDialog.vue'
import { asDoc, BADGE_TONE, fileBadge, SPACE_HINT, uploadFile, type Browse, type DriveFile, type FolderRef, type Space, type SpaceId } from '@/components/app/drive/drive'
import { dateLabel, downloadFrom, type Lookup, type Staff } from '@/components/app/finance/finance'

const route = useRoute()
const router = useRouter()
const qs = (k: string) => (typeof route.query[k] === 'string' ? (route.query[k] as string) : '')

const spaces = ref<Space[]>([])
const mine = ref(0)
const canLink = ref(false)
const data = ref<Browse | null>(null)
const selected = ref<DriveFile | null>(null)
const loading = ref(false)
const error = ref('')
const search = ref(qs('q'))
const layout = ref<'grid' | 'list'>((() => { try { return (localStorage.getItem('drive.layout') as 'grid' | 'list') || 'grid' } catch { return 'grid' } })())
watch(layout, (v) => { try { localStorage.setItem('drive.layout', v) } catch { /* not remembered */ } })

const space = computed<SpaceId>(() => (qs('space') as SpaceId) || 'company')
const spaceInfo = computed(() => spaces.value.find((s) => s.id === (data.value?.space || space.value)))
const view = computed(() => qs('view'))
const title = computed(() => (view.value === 'mine' ? 'Linked to me' : view.value === 'recent' ? 'Recent uploads' : qs('q') ? `Search: “${qs('q')}”` : spaceInfo.value?.label || 'Drive'))
const canWrite = computed(() => !!data.value?.can_write && data.value.mode === 'folder')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string> = {}
    for (const k of ['space', 'folder', 'q', 'view', 'employee', 'project', 'fy']) if (qs(k)) params[k] = qs(k)
    if (!params.space && !params.q && !params.view) params.space = 'company'
    data.value = (await api.get<Browse>('drive/browse/', { params })).data
    if (selected.value) selected.value = data.value.files.find((f) => f.id === selected.value!.id) || null
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
async function loadSpaces() {
  const { data: s } = await api.get<{ spaces: Space[]; mine: number; can_link_records: boolean }>('drive/spaces/')
  spaces.value = s.spaces
  mine.value = s.mine
  canLink.value = s.can_link_records
}
onMounted(() => {
  loadSpaces().catch(() => {})
  loadPickers().catch(() => {})
})
watch(() => route.fullPath, () => { selected.value = null; search.value = qs('q'); load() }, { immediate: true })

function nav(query: Record<string, string | undefined>) {
  router.push({ query: Object.fromEntries(Object.entries(query).filter(([, v]) => v)) })
}
const openFolder = (f: FolderRef | { id: number }) => nav({ space: data.value?.space || space.value, folder: String(f.id) })
let typing: number | undefined
watch(search, (v) => {
  clearTimeout(typing)
  typing = window.setTimeout(() => v !== qs('q') && nav(v ? { q: v, space: qs('space') || undefined } : { space: qs('space') || 'company' }), 350)
})

// ---------------------------------------------------------------- upload (files, folder picker, drag & drop)
const progress = reactive({ done: 0, total: 0, pct: 0 })
const dragging = ref(false)
async function upload(items: { file: File; path: string }[]) {
  if (!canWrite.value || !items.length) return
  Object.assign(progress, { done: 0, total: items.length, pct: 0 })
  const failed: string[] = []
  for (const it of items) {
    try {
      await uploadFile(it.file, { space: data.value!.space, folder: data.value!.folder?.id, relative_path: it.path.includes('/') ? it.path : '' }, (p) => (progress.pct = p))
    } catch (e) {
      failed.push(`${it.file.name}: ${errorMessage(e)}`)
    }
    progress.done++
  }
  progress.total = 0
  if (failed.length) toast.error(`${failed.length} failed. ${failed[0]}`)
  else toast.success(`${items.length} file${items.length > 1 ? 's' : ''} uploaded`)
  load()
  loadSpaces().catch(() => {})
}
function picked(e: Event) {
  const input = e.target as HTMLInputElement
  upload(Array.from(input.files || []).map((f) => ({ file: f, path: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name })))
  input.value = ''
}
/** Walk dropped folders (webkitGetAsEntry) so a whole "salary logs" folder keeps its structure. */
async function entries(entry: FileSystemEntry, prefix = ''): Promise<{ file: File; path: string }[]> {
  if (entry.isFile) return [{ file: await new Promise<File>((res, rej) => (entry as FileSystemFileEntry).file(res, rej)), path: prefix + entry.name }]
  const reader = (entry as FileSystemDirectoryEntry).createReader()
  const out: { file: File; path: string }[] = []
  for (;;) {
    const batch = await new Promise<FileSystemEntry[]>((res, rej) => reader.readEntries(res, rej))
    if (!batch.length) break
    for (const child of batch) out.push(...(await entries(child, prefix + entry.name + '/')))
  }
  return out
}
async function drop(e: DragEvent) {
  dragging.value = false
  const roots = Array.from(e.dataTransfer?.items || []).map((i) => i.webkitGetAsEntry()).filter(Boolean) as FileSystemEntry[]
  upload((await Promise.all(roots.map((r) => entries(r)))).flat().filter((x) => !/^(~\$|\.)/.test(x.file.name)))
}

// ---------------------------------------------------------------- folders
const folderDialog = reactive({ open: false, id: null as number | null, name: '', fiscal_year: '', error: '' })
function newFolder() {
  Object.assign(folderDialog, { open: true, id: null, name: '', fiscal_year: '', error: '' })
}
function editFolder(f: FolderRef) {
  Object.assign(folderDialog, { open: true, id: f.id, name: f.name, fiscal_year: f.fiscal_year, error: '' })
}
async function saveFolder() {
  try {
    const body = { name: folderDialog.name, fiscal_year: folderDialog.fiscal_year }
    if (folderDialog.id) await api.patch(`drive/folders/${folderDialog.id}/`, body)
    else await api.post('drive/folders/', { ...body, space: data.value!.space, parent: data.value!.folder?.id ?? null })
    folderDialog.open = false
    load()
  } catch (e) {
    folderDialog.error = errorMessage(e)
  }
}
async function deleteFolder(f: FolderRef) {
  if (!(await confirmDialog({ title: `Delete “${f.name}”?`, body: 'Only empty folders can be deleted.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`drive/folders/${f.id}/`)
    load()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const zip = (f: FolderRef) => downloadFrom(`drive/folders/${f.id}/zip/`, {}, f.name + '.zip').catch(() => toast.error('Download failed.'))

// ---------------------------------------------------------------- files
const viewing = ref<Doc | null>(null)
const details = reactive({ name: '', description: '', fiscal_year: '', employee: null as number | null, project: null as number | null, error: '' })
watch(selected, (f) => f && Object.assign(details, { name: f.name, description: f.description, fiscal_year: f.fiscal_year, employee: f.employee, project: f.project, error: '' }))
async function saveDetails() {
  try {
    const { error: _e, ...body } = details
    void _e
    selected.value = (await api.patch<DriveFile>(`drive/files/${selected.value!.id}/`, body)).data
    toast.success('Saved')
    load()
  } catch (e) {
    details.error = errorMessage(e)
  }
}
async function deleteFile(f: DriveFile) {
  if (!(await confirmDialog({ title: `Delete “${f.name}”?`, body: 'The file is removed for everyone. Audit history keeps a record that it existed.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`drive/files/${f.id}/`)
    selected.value = null
    load()
    loadSpaces().catch(() => {})
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const moving = ref<{ kind: 'file' | 'folder'; id: number } | null>(null)
async function moveTo(folder: number | null) {
  const m = moving.value!
  moving.value = null
  try {
    if (m.kind === 'file') await api.patch(`drive/files/${m.id}/`, { folder })
    else await api.patch(`drive/folders/${m.id}/`, { parent: folder })
    load()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const sharing = ref<{ folder?: number; file?: number; name: string } | null>(null)
const staff = ref<Staff[]>([])
const projects = ref<Lookup[]>([])
async function loadPickers() {
  const [s] = await Promise.all([api.get<Staff[]>('org/people/', { params: { is_active: true } })])
  staff.value = s.data
  const p = await api.get<Lookup[]>('finance/projects/').catch(() => api.get<Lookup[]>('pm/projects/'))
  projects.value = p.data.map((x) => ({ id: x.id, name: x.name }))
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Workspace · Documents" title="Drive" description="Company files in one place: shared templates for everyone, finance and audit records for the books, and staff documents for HR." />
    <div class="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <nav class="grid content-start gap-1" aria-label="Drive spaces">
        <button v-for="s in spaces" :key="s.id" type="button" class="flex items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition"
          :class="data?.space === s.id && data.mode === 'folder' && !data.folder ? 'bg-ink text-paper' : data?.space === s.id && data.mode === 'folder' ? 'bg-panel text-ink' : 'text-ink/75 hover:bg-panel/60'"
          @click="nav({ space: s.id })">
          <span>{{ s.label }}</span><span class="font-mono text-[11px] opacity-60">{{ s.files }}</span>
        </button>
        <hr class="my-2 border-ink/10" />
        <button type="button" class="flex items-center justify-between rounded-lg px-3 py-2 text-left text-sm" :class="view === 'mine' ? 'bg-ink text-paper' : 'text-ink/75 hover:bg-panel/60'" @click="nav({ view: 'mine' })">
          <span>Linked to me</span><span class="font-mono text-[11px] opacity-60">{{ mine }}</span>
        </button>
        <button type="button" class="rounded-lg px-3 py-2 text-left text-sm" :class="view === 'recent' ? 'bg-ink text-paper' : 'text-ink/75 hover:bg-panel/60'" @click="nav({ view: 'recent' })">Recent uploads</button>
        <p v-if="spaceInfo && data?.mode === 'folder'" class="mt-3 px-3 text-xs leading-relaxed text-ink/55">{{ SPACE_HINT[spaceInfo.id] }}</p>
      </nav>

      <section class="relative min-w-0" @dragover.prevent="canWrite && (dragging = true)" @dragleave.self="dragging = false" @drop.prevent="drop">
        <div class="mb-4 flex flex-wrap items-center gap-2">
          <nav class="flex min-w-0 flex-1 flex-wrap items-center gap-1 text-sm" aria-label="Breadcrumb">
            <template v-if="data?.mode === 'folder'">
              <button type="button" class="font-medium hover:underline" @click="nav({ space: data.space! })">{{ spaceInfo?.label }}</button>
              <template v-for="p in data.folder?.path || []" :key="p.id"><span class="text-ink/35">/</span><button type="button" class="hover:underline" @click="openFolder(p)">{{ p.name }}</button></template>
              <span v-if="data.folder?.fiscal_year" class="ml-2 rounded-full bg-contour/15 px-2 py-0.5 font-mono text-[10px] text-contour-ink">FY {{ data.folder.fiscal_year }}</span>
            </template>
            <span v-else class="font-medium">{{ title }}</span>
          </nav>
          <label class="sr-only" for="drive-search">Search the drive</label>
          <input id="drive-search" v-model="search" type="search" class="input w-56" placeholder="Search files and folders…" />
          <div class="flex rounded-lg border border-ink/15 p-0.5" role="group" aria-label="Layout">
            <button v-for="l in (['grid', 'list'] as const)" :key="l" type="button" class="rounded-md px-2.5 py-1 text-xs capitalize" :class="layout === l ? 'bg-ink text-paper' : 'text-ink/60'" :aria-pressed="layout === l" @click="layout = l">{{ l }}</button>
          </div>
        </div>
        <div v-if="canWrite" class="mb-4 flex flex-wrap items-center gap-2">
          <label class="btn-ink cursor-pointer">Upload files<input type="file" multiple class="sr-only" @change="picked" /></label>
          <label class="btn-ghost cursor-pointer">Upload a folder<input type="file" webkitdirectory multiple class="sr-only" @change="picked" /></label>
          <button class="btn-ghost" @click="newFolder">New folder</button>
          <button v-if="data?.folder" class="btn-ghost btn-sm" @click="zip(data.folder)">Download folder (.zip)</button>
          <button v-if="data?.folder && spaceInfo?.can_share" class="btn-ghost btn-sm" @click="sharing = { folder: data.folder.id, name: data.folder.name }">Share folder</button>
          <span class="text-xs text-ink/50">or drag files and folders here</span>
        </div>
        <div v-if="progress.total" class="mb-4 rounded-lg border border-river/30 bg-river/5 px-4 py-2 text-sm" role="status">
          Uploading {{ progress.done + 1 }} of {{ progress.total }} · {{ progress.pct }}%
          <div class="mt-1.5 h-1 rounded-full bg-ink/10"><div class="h-1 rounded-full bg-river transition-all" :style="{ width: ((progress.done + progress.pct / 100) / progress.total) * 100 + '%' }" /></div>
        </div>
        <div v-if="dragging" class="pointer-events-none absolute inset-0 z-10 grid place-items-center rounded-xl border-2 border-dashed border-river bg-sheet/90 text-sm font-medium text-river">Drop to upload into {{ data?.folder?.name || spaceInfo?.label }}</div>

        <p v-if="error" role="alert" class="panel p-4 text-sm text-rust">{{ error }}</p>
        <div v-else class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]" :aria-busy="loading">
          <div class="min-w-0">
            <EmptyState v-if="data && !data.folders.length && !data.files.length" :title="data.mode === 'search' ? 'Nothing found' : 'This folder is empty'"
              :hint="canWrite ? 'Upload files or drag a folder here.' : ''" />
            <template v-if="data?.folders.length">
              <p class="ledger-label mb-2">Folders</p>
              <ul class="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-3 2xl:grid-cols-4">
                <li v-for="f in data.folders" :key="f.id" class="group relative">
                  <button type="button" class="flex w-full items-center gap-3 rounded-lg border border-ink/10 bg-sheet px-3 py-2.5 text-left transition hover:border-ink/25" @click="openFolder(f)">
                    <svg viewBox="0 0 24 24" class="h-5 w-5 shrink-0 fill-contour/30 stroke-contour-ink" stroke-width="1.5" aria-hidden="true"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
                    <span class="min-w-0 flex-1"><span class="block truncate text-sm text-ink">{{ f.name }}</span>
                      <span class="block text-[11px] text-ink/50">{{ f.file_count }} file{{ f.file_count === 1 ? '' : 's' }}{{ f.folder_count ? ` · ${f.folder_count} folder${f.folder_count === 1 ? '' : 's'}` : '' }}{{ f.fiscal_year ? ` · FY ${f.fiscal_year}` : '' }}</span></span>
                  </button>
                  <div v-if="canWrite" class="absolute top-1.5 right-1.5 hidden gap-1 group-focus-within:flex group-hover:flex">
                    <button type="button" class="rounded bg-sheet px-1.5 text-[11px] text-ink/70 shadow hover:text-ink" @click="editFolder(f)">Edit</button>
                    <button type="button" class="rounded bg-sheet px-1.5 text-[11px] text-ink/70 shadow hover:text-ink" @click="moving = { kind: 'folder', id: f.id }">Move</button>
                    <button type="button" class="rounded bg-sheet px-1.5 text-[11px] text-ink/70 shadow hover:text-ink" @click="zip(f)">Zip</button>
                    <button type="button" class="rounded bg-sheet px-1.5 text-[11px] text-rust shadow" @click="deleteFolder(f)">Delete</button>
                  </div>
                </li>
              </ul>
            </template>
            <template v-if="data?.files.length">
              <p class="ledger-label mb-2">Files</p>
              <ul v-if="layout === 'grid'" class="grid grid-cols-2 gap-3 sm:grid-cols-3 2xl:grid-cols-4">
                <li v-for="f in data.files" :key="f.id">
                  <button type="button" class="flex h-full w-full flex-col rounded-lg border bg-sheet p-3 text-left transition"
                    :class="selected?.id === f.id ? 'border-river ring-2 ring-river/20' : 'border-ink/10 hover:border-ink/25'"
                    @click="selected = f" @dblclick="viewing = asDoc(f)">
                    <span class="mb-3 grid h-16 place-items-center rounded-md font-mono text-sm font-medium" :class="BADGE_TONE[fileBadge(f.extension)] || 'bg-ink/[0.06] text-ink/60'">{{ fileBadge(f.extension) }}</span>
                    <span class="line-clamp-2 text-sm break-words text-ink">{{ f.name }}</span>
                    <span class="mt-auto pt-1 text-[11px] text-ink/50">{{ fileSize(f.size) }}{{ f.fiscal_year ? ` · FY ${f.fiscal_year}` : '' }}</span>
                    <span v-if="f.employee_name" class="text-[11px] text-sky">{{ f.employee_name }}</span>
                  </button>
                </li>
              </ul>
              <div v-else class="panel relative overflow-x-auto">
                <table class="ledger-table text-[13px]">
                  <thead><tr><th>Name</th><th v-if="data.mode === 'search'">Folder</th><th>Linked to</th><th>FY</th><th class="text-right">Size</th><th>Added</th></tr></thead>
                  <tbody>
                    <tr v-for="f in data.files" :key="f.id" class="cursor-pointer" :class="selected?.id === f.id && 'bg-river/5'" @click="selected = f" @dblclick="viewing = asDoc(f)">
                      <td><button type="button" class="flex items-center gap-2 text-left" @click.stop="selected = f"><span class="rounded px-1.5 py-0.5 font-mono text-[10px]" :class="BADGE_TONE[fileBadge(f.extension)] || 'bg-ink/[0.06]'">{{ fileBadge(f.extension) }}</span>{{ f.name }}</button></td>
                      <td v-if="data.mode === 'search'" class="text-xs text-ink/60">{{ f.folder_name || '—' }}</td>
                      <td class="text-xs text-ink/60">{{ [f.employee_name, f.project_name].filter(Boolean).join(' · ') || '—' }}</td>
                      <td class="font-mono text-xs">{{ f.fiscal_year }}</td>
                      <td class="readout text-right text-xs">{{ fileSize(f.size) }}</td>
                      <td class="text-xs whitespace-nowrap text-ink/60">{{ dateLabel(f.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>

          <aside v-if="selected" class="panel h-fit p-4 xl:sticky xl:top-4" aria-label="File details">
            <div class="mb-3 flex items-start justify-between gap-2">
              <p class="ledger-label">Details</p>
              <button type="button" class="text-ink/50 hover:text-ink" aria-label="Close details" @click="selected = null">✕</button>
            </div>
            <div class="mb-3 flex flex-wrap gap-2">
              <button class="btn-ink btn-sm" @click="viewing = asDoc(selected)">Open</button>
              <button class="btn-ghost btn-sm" @click="downloadDoc(asDoc(selected))">Download</button>
              <button v-if="spaceInfo?.can_share" class="btn-ghost btn-sm" @click="sharing = { file: selected.id, name: selected.name }">Share</button>
            </div>
            <form class="grid gap-3" @submit.prevent="saveDetails">
              <label class="field"><span class="ledger-label">Name</span><input v-model="details.name" class="input" maxlength="255" /></label>
              <label class="field"><span class="ledger-label">Description</span><textarea v-model="details.description" class="input" rows="2" /></label>
              <label class="field"><span class="ledger-label">Fiscal year</span><input v-model="details.fiscal_year" class="input font-mono" placeholder="2082/83" pattern="\d{4}/\d{2}" /></label>
              <label class="field"><span class="ledger-label">Person</span>
                <select v-model="details.employee" class="input" :disabled="!canLink">
                  <option :value="null">—</option><option v-for="p in staff" :key="p.id" :value="p.id">{{ p.full_name || p.email }}</option></select></label>
              <label class="field"><span class="ledger-label">Project</span>
                <select v-model="details.project" class="input"><option :value="null">—</option><option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option></select></label>
              <p v-if="selected.transaction_label" class="text-xs text-ink/60">Bank line: {{ selected.transaction_label }}</p>
              <p class="text-xs text-ink/50">{{ fileSize(selected.size) }} · added {{ dateLabel(selected.created_at) }}{{ selected.uploaded_by_name ? ' by ' + selected.uploaded_by_name : '' }}</p>
              <p v-if="details.error" role="alert" class="text-sm text-rust">{{ details.error }}</p>
              <div class="flex flex-wrap gap-2">
                <button class="btn-ink btn-sm">Save</button>
                <button type="button" class="btn-ghost btn-sm" @click="moving = { kind: 'file', id: selected.id }">Move</button>
                <button type="button" class="btn-danger btn-sm ml-auto" @click="deleteFile(selected)">Delete</button>
              </div>
            </form>
          </aside>
        </div>
      </section>
    </div>

    <DocViewer :doc="viewing" @close="viewing = null" />
    <ShareDialog :target="sharing" @close="sharing = null" />
    <MoveDialog :open="!!moving" :space="(selected?.space || data?.space || 'company') as SpaceId" :exclude="moving?.kind === 'folder' ? moving.id : undefined" @close="moving = null" @pick="moveTo" />
    <Modal :open="folderDialog.open" :title="folderDialog.id ? 'Edit folder' : 'New folder'" @close="folderDialog.open = false">
      <form class="grid gap-3" @submit.prevent="saveFolder">
        <label class="field"><span class="ledger-label">Name</span><input v-model="folderDialog.name" class="input" required maxlength="120" /></label>
        <label class="field"><span class="ledger-label">Fiscal year (optional, for audit folders)</span><input v-model="folderDialog.fiscal_year" class="input font-mono" placeholder="2081/82" pattern="\d{4}/\d{2}" /></label>
        <p v-if="folderDialog.error" role="alert" class="text-sm text-rust">{{ folderDialog.error }}</p>
        <button class="btn-ink justify-self-end">Save</button>
      </form>
    </Modal>
  </div>
</template>
