<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import { confirmDialog } from '../ui/confirm'
import Modal from '../ui/Modal.vue'
import EmptyState from '../ui/EmptyState.vue'
import DocViewer from './DocViewer.vue'
import { downloadDoc, errorMessage, fileSize, type Doc, type Project } from './pm'
const props = defineProps<{ project: Project; docs: Doc[]; openId?: number | null }>()
const emit = defineEmits<{ changed: []; wikilink: [target: string] }>()

const ACCEPT = '.pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv,.docx,.xlsx,.pptx,.zip'
const MAX = 25 * 1024 * 1024
const folder = ref<string | null>(null)
const search = ref('')
const layout = ref<'grid' | 'list'>('grid')
const viewing = ref<Doc | null>(null)
const uploading = ref<{ name: string; done: boolean; error?: string }[]>([])
const dragOver = ref(false)
const uploadFolder = ref('')
const editing = ref<Doc | null>(null)
const form = reactive({ title: '', folder: '', description: '', public: false })

const folders = computed(() => [...new Set(props.docs.map((d) => d.folder).filter(Boolean))].sort())
const shown = computed(() =>
  props.docs.filter(
    (d) =>
      (folder.value === null || d.folder === folder.value) &&
      `${d.title} ${d.file} ${d.description}`.toLowerCase().includes(search.value.toLowerCase()),
  ),
)
watch(
  () => props.openId,
  (id) => {
    if (id) viewing.value = props.docs.find((d) => d.id === id) || null
  },
  { immediate: true },
)

const ICON: Record<string, string> = { pdf: 'PDF', docx: 'DOC', xlsx: 'XLS', pptx: 'PPT', zip: 'ZIP', md: 'MD', txt: 'TXT', csv: 'CSV' }
const TONE: Record<string, string> = { pdf: 'bg-rust/12 text-rust', docx: 'bg-sky/12 text-sky', xlsx: 'bg-moss/12 text-moss', pptx: 'bg-flag/12 text-flag', md: 'bg-river/12 text-river' }
const isImage = (d: Doc) => ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(d.extension)

async function upload(files: FileList | File[] | null) {
  if (!files?.length) return
  const list = [...files]
  uploading.value = list.map((f) => ({ name: f.name, done: false }))
  await Promise.all(
    list.map(async (f, i) => {
      const row = uploading.value[i]!
      if (f.size > MAX) return (row.error = 'Larger than 25 MB')
      const data = new FormData()
      data.append('project', String(props.project.id))
      data.append('title', f.name.replace(/\.[^.]+$/, '').slice(0, 200))
      data.append('folder', uploadFolder.value.trim())
      data.append('file', f)
      try {
        await api.post('pm/documents/', data)
        row.done = true
      } catch (e) {
        row.error = errorMessage(e)
      }
    }),
  )
  const ok = uploading.value.filter((u) => u.done).length
  if (ok) toast.success(`${ok} document${ok === 1 ? '' : 's'} uploaded.`)
  if (uploading.value.every((u) => u.done)) uploading.value = []
  emit('changed')
}
function onDrop(e: DragEvent) {
  dragOver.value = false
  upload(e.dataTransfer?.files || null)
}
function edit(d: Doc) {
  editing.value = d
  Object.assign(form, { title: d.title, folder: d.folder, description: d.description, public: d.public })
}
async function saveEdit() {
  try {
    await api.patch(`pm/documents/${editing.value!.id}/`, form)
    editing.value = null
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function remove(d: Doc) {
  if (!(await confirmDialog({ title: `Delete “${d.title}”?`, body: 'The file is removed permanently.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`pm/documents/${d.id}/`)
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
</script>
<template>
  <div class="grid gap-5 lg:grid-cols-[200px_1fr]">
    <aside class="grid content-start gap-1">
      <p class="ledger-label mb-2 px-2">Folders</p>
      <button
        v-for="f in [null, ...folders, ...(docs.some((d) => !d.folder) && folders.length ? [''] : [])]"
        :key="String(f)"
        class="flex items-center justify-between rounded-md px-2.5 py-1.5 text-left text-sm"
        :class="folder === f ? 'bg-panel font-medium' : 'text-ink/70 hover:bg-panel/60'"
        @click="folder = f"
      >
        <span class="truncate">{{ f === null ? 'All documents' : f || 'Unfiled' }}</span>
        <span class="readout text-[11px] text-ink/50">{{ f === null ? docs.length : docs.filter((d) => d.folder === f).length }}</span>
      </button>
    </aside>
    <div class="min-w-0">
      <label
        class="mb-5 flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition-colors"
        :class="dragOver ? 'border-flag bg-flag/5' : 'border-ink/15 hover:border-ink/30'"
        @dragover.prevent="dragOver = true"
        @dragleave.self="dragOver = false"
        @drop.prevent="onDrop"
      >
        <svg viewBox="0 0 24 24" class="h-6 w-6 text-ink/50" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
        <span class="text-sm"><strong class="font-medium">Drop files</strong> or click to upload</span>
        <span class="text-xs text-ink/50">PDF, images, Markdown, text, CSV, Office files, ZIP · up to 25 MB each</span>
        <input type="file" multiple :accept="ACCEPT" class="sr-only" @change="upload(($event.target as HTMLInputElement).files)" />
      </label>
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <label class="field min-w-0 flex-1 sm:max-w-xs"><span class="sr-only">Search documents</span><input v-model="search" type="search" class="input" placeholder="Search documents…" /></label>
        <label class="flex items-center gap-2 text-xs text-ink/60"
          >Upload to
          <input v-model="uploadFolder" list="doc-folders" class="input !w-36 !py-1 text-xs" placeholder="Folder (optional)" maxlength="80" />
          <datalist id="doc-folders"><option v-for="f in folders" :key="f" :value="f" /></datalist>
        </label>
        <div class="ml-auto flex rounded-full border border-ink/15 p-0.5" role="group" aria-label="Layout">
          <button v-for="l in ['grid', 'list'] as const" :key="l" class="rounded-full px-3 py-1 text-xs capitalize" :class="layout === l ? 'bg-ink text-paper' : 'text-ink/60'" :aria-pressed="layout === l" @click="layout = l">{{ l }}</button>
        </div>
      </div>
      <ul v-if="uploading.length" class="mb-4 grid gap-1 rounded-lg bg-panel/50 p-3 text-xs" aria-live="polite">
        <li v-for="u in uploading" :key="u.name" class="flex justify-between gap-3">
          <span class="truncate">{{ u.name }}</span>
          <span :class="u.error ? 'text-rust' : u.done ? 'text-moss' : 'text-ink/50'">{{ u.error || (u.done ? 'Uploaded' : 'Uploading…') }}</span>
        </li>
      </ul>
      <div v-if="!shown.length" class="panel">
        <EmptyState :title="search ? 'No matching documents' : 'No documents yet'" hint="Specs, contracts, designs and reports live here — previewable right in the browser." />
      </div>
      <div v-else-if="layout === 'grid'" class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <article v-for="d in shown" :key="d.id" class="group panel flex flex-col overflow-hidden">
          <button class="grid aspect-[4/3] place-items-center bg-panel/50 transition-colors hover:bg-panel" :aria-label="`Open ${d.title}`" @click="viewing = d">
            <span class="rounded-md px-2.5 py-1.5 font-mono text-sm font-medium" :class="isImage(d) ? 'bg-contour/15 text-contour-ink' : TONE[d.extension] || 'bg-ink/8 text-ink/60'">
              {{ isImage(d) ? 'IMG' : ICON[d.extension] || d.extension.toUpperCase() }}
            </span>
          </button>
          <div class="flex flex-1 flex-col p-3">
            <p class="line-clamp-2 text-sm font-medium">{{ d.title }}</p>
            <p class="mt-1 font-mono text-[10px] text-ink/50">{{ d.extension }} · {{ fileSize(d.size) }}<span v-if="d.public" class="text-moss"> · public</span></p>
            <div class="mt-auto flex gap-2 pt-3 text-xs opacity-80 group-hover:opacity-100">
              <button class="hover:text-river" @click="downloadDoc(d)">Download</button>
              <button v-if="d.can_edit" class="hover:text-river" @click="edit(d)">Edit</button>
              <button v-if="d.can_edit" class="ml-auto text-rust" @click="remove(d)">Delete</button>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="panel overflow-x-auto">
        <table class="ledger-table">
          <thead><tr><th>Title</th><th>Folder</th><th>Type</th><th>Size</th><th>Uploaded</th><th><span class="sr-only">Actions</span></th></tr></thead>
          <tbody>
            <tr v-for="d in shown" :key="d.id">
              <td><button class="text-left font-medium hover:text-river" @click="viewing = d">{{ d.title }}</button><span v-if="d.public" class="ml-2 text-[10px] text-moss">public</span></td>
              <td class="text-ink/60">{{ d.folder || '—' }}</td>
              <td class="font-mono text-xs uppercase">{{ d.extension }}</td>
              <td class="readout text-xs">{{ fileSize(d.size) }}</td>
              <td class="text-xs text-ink/60">{{ d.uploaded_by_name }} · {{ new Date(d.created_at).toLocaleDateString('en-GB') }}</td>
              <td class="whitespace-nowrap text-right text-xs">
                <button class="mr-3 hover:text-river" @click="downloadDoc(d)">Download</button>
                <button v-if="d.can_edit" class="mr-3 hover:text-river" @click="edit(d)">Edit</button>
                <button v-if="d.can_edit" class="text-rust" @click="remove(d)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <DocViewer :doc="viewing" @close="viewing = null" @wikilink="emit('wikilink', $event)" />
    <Modal :open="!!editing" title="Edit document" @close="editing = null">
      <form class="grid gap-4" @submit.prevent="saveEdit">
        <label class="field"><span class="ledger-label">Title</span><input v-model="form.title" required maxlength="200" class="input" /></label>
        <label class="field"><span class="ledger-label">Folder</span><input v-model="form.folder" list="doc-folders" maxlength="80" class="input" /></label>
        <label class="field"><span class="ledger-label">Description</span><textarea v-model="form.description" rows="3" class="input" /></label>
        <label v-if="project.can_manage" class="flex items-start gap-2 text-sm">
          <input v-model="form.public" type="checkbox" class="mt-1 accent-ink" />
          <span>Show on the public project page<span class="block text-xs text-ink/55">Images appear in the gallery, other files in downloads — when those sections are published.</span></span>
        </label>
        <button class="btn-ink justify-self-end">Save</button>
      </form>
    </Modal>
  </div>
</template>
