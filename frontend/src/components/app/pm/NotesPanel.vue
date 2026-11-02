<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import { confirmDialog } from '../ui/confirm'
import MarkdownView from './MarkdownView.vue'
import NoteGraph from './NoteGraph.vue'
import {
  buildGraph,
  errorMessage,
  resolveLink,
  wikilinks,
  type Doc,
  type GraphNode,
  type Meeting,
  type Note,
  type Project,
  type Task,
} from './pm'
const props = defineProps<{ project: Project; notes: Note[]; docs: Doc[]; tasks: Task[]; meetings: Meeting[]; openId?: number | null }>()
const emit = defineEmits<{
  upsert: [note: Note]
  removed: [id: number]
  openDoc: [id: number]
  openTask: [task: Task]
  openMeeting: [id: number]
}>()

const mode = ref<'note' | 'graph'>(props.notes.length || props.openId ? 'note' : 'graph')
const selectedId = ref<number | null>(props.openId ?? props.notes[0]?.id ?? null)
watch(
  () => props.openId,
  (id) => {
    if (id) {
      selectedId.value = id
      mode.value = 'note'
    }
  },
)
const view = ref<'split' | 'edit' | 'preview'>('preview')
const search = ref('')
const title = ref('')
const body = ref('')
const status = ref<'saved' | 'dirty' | 'saving' | 'error'>('saved')
const selected = computed(() => props.notes.find((n) => n.id === selectedId.value) || null)
const list = computed(() => {
  const q = search.value.toLowerCase()
  return props.notes.filter((n) => `${n.title} ${n.body}`.toLowerCase().includes(q))
})

watch(
  selected,
  (n, old) => {
    if (n?.id === old?.id) return
    title.value = n?.title || ''
    body.value = n?.body || ''
    status.value = 'saved'
  },
  { immediate: true },
)

// autosave 1.2s after the last keystroke; ponytail: last write wins, add a version check if co-editing gets common
let timer = 0
watch([title, body], () => {
  if (!selected.value || (title.value === selected.value.title && body.value === selected.value.body)) return
  status.value = 'dirty'
  clearTimeout(timer)
  timer = window.setTimeout(save, 1200)
})
async function save() {
  clearTimeout(timer)
  const note = selected.value
  if (!note || status.value !== 'dirty') return
  if (!title.value.trim()) {
    status.value = 'error'
    return
  }
  status.value = 'saving'
  try {
    const { data } = await api.patch<Note>(`pm/notes/${note.id}/`, { title: title.value.trim(), body: body.value })
    emit('upsert', data)
    status.value = 'saved'
  } catch (e) {
    status.value = 'error'
    toast.error(errorMessage(e))
  }
}
onBeforeUnmount(save)

async function create(name?: string) {
  await save()
  let base = name || 'Untitled'
  const taken = new Set(props.notes.map((n) => n.title.toLowerCase()))
  for (let i = 2; taken.has(base.toLowerCase()); i++) base = `${name || 'Untitled'} ${i}`
  try {
    const { data } = await api.post<Note>('pm/notes/', {
      project: props.project.id,
      title: base,
      body: name ? '' : '# ' + base + '\n\n',
    })
    emit('upsert', data)
    selectedId.value = data.id
    mode.value = 'note'
    view.value = 'split'
    await nextTick()
    editor.value?.focus()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function remove() {
  const note = selected.value
  if (!note) return
  if (!(await confirmDialog({ title: `Delete “${note.title}”?`, body: 'Links to it will show as unwritten notes.', confirmLabel: 'Delete note', danger: true })))
    return
  try {
    await api.delete(`pm/notes/${note.id}/`)
    emit('removed', note.id)
    selectedId.value = props.notes.find((n) => n.id !== note.id)?.id ?? null
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function togglePin() {
  if (!selected.value) return
  try {
    emit('upsert', (await api.patch<Note>(`pm/notes/${selected.value.id}/`, { pinned: !selected.value.pinned })).data)
  } catch (e) {
    toast.error(errorMessage(e))
  }
}

function open(node: GraphNode) {
  if (node.kind === 'note') {
    selectedId.value = node.ref
    mode.value = 'note'
  } else if (node.kind === 'doc') emit('openDoc', node.ref!)
  else if (node.kind === 'meeting') emit('openMeeting', node.ref!)
  else if (node.kind === 'task') emit('openTask', props.tasks.find((t) => t.id === node.ref)!)
  else create(node.label)
}
const follow = (target: string) => open(resolveLink(target, props.notes, props.docs, props.tasks, props.meetings))

const graph = computed(() => buildGraph(props.notes, props.docs, props.tasks, props.meetings))
const backlinks = computed(() => {
  const n = selected.value
  if (!n) return []
  const t = n.title.toLowerCase()
  return [
    ...props.notes.filter((o) => o.id !== n.id && wikilinks(o.body).some((l) => l.toLowerCase() === t)).map((o) => ({ id: `note:${o.id}`, label: o.title, kind: 'note' as const, ref: o.id })),
    ...props.meetings.filter((m) => wikilinks(`${m.agenda}\n${m.minutes}`).some((l) => l.toLowerCase() === t)).map((m) => ({ id: `meeting:${m.id}`, label: m.title, kind: 'meeting' as const, ref: m.id })),
  ]
})
const outgoing = computed(() => wikilinks(body.value).map((l) => resolveLink(l, props.notes, props.docs, props.tasks, props.meetings)))
const tags = computed(() => [...new Set([...body.value.matchAll(/(?:^|\s)#([\p{L}\d_-]{2,30})/gu)].map((m) => m[1]))])

// ── [[ autocomplete ──
const editor = ref<HTMLTextAreaElement | null>(null)
const suggest = ref<{ query: string; index: number } | null>(null)
const candidates = computed(() => {
  if (!suggest.value) return []
  const q = suggest.value.query.toLowerCase()
  return [
    ...props.notes.filter((n) => n.id !== selectedId.value).map((n) => ({ label: n.title, hint: 'note' })),
    ...props.docs.map((d) => ({ label: d.title, hint: d.extension })),
    ...props.meetings.map((m) => ({ label: m.title, hint: 'meeting' })),
    ...props.tasks.map((t) => ({ label: t.key, hint: t.title })),
  ]
    .filter((c) => `${c.label} ${c.hint}`.toLowerCase().includes(q))
    .slice(0, 8)
})
function onInput() {
  const el = editor.value!
  const m = el.value.slice(0, el.selectionStart).match(/\[\[([^\]\n]{0,60})$/)
  suggest.value = m ? { query: m[1]!, index: 0 } : null
}
function pick(label: string) {
  const el = editor.value!
  const caret = el.selectionStart
  const before = el.value.slice(0, caret).replace(/\[\[([^\]\n]*)$/, `[[${label}]]`)
  const after = el.value.slice(caret).replace(/^[^\]\n]*\]\]/, '')
  body.value = before + after
  suggest.value = null
  nextTick(() => {
    el.focus()
    el.setSelectionRange(before.length, before.length)
  })
}
function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save()
    return
  }
  const s = suggest.value
  if (!s || !candidates.value.length) return
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    s.index = (s.index + (e.key === 'ArrowDown' ? 1 : -1) + candidates.value.length) % candidates.value.length
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault()
    pick(candidates.value[s.index]!.label)
  } else if (e.key === 'Escape') suggest.value = null
}
const STATUS = { saved: 'Saved', dirty: 'Unsaved changes', saving: 'Saving…', error: 'Not saved — needs a title' }
</script>
<template>
  <div class="grid gap-4 lg:grid-cols-[240px_1fr]">
    <!-- sidebar -->
    <aside class="panel flex max-h-[75vh] flex-col overflow-hidden">
      <div class="grid gap-2 border-b border-dashed border-ink/15 p-3">
        <div class="flex gap-2">
          <button class="btn-primary btn-sm flex-1" @click="create()">New note</button>
          <button class="btn-ghost btn-sm" :aria-pressed="mode === 'graph'" @click="mode = mode === 'graph' ? 'note' : 'graph'">
            <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="5" cy="6" r="2.5" /><circle cx="19" cy="7" r="2.5" /><circle cx="12" cy="18" r="2.5" /><path d="M7 7l10 0M6.5 8l4.5 8M17.5 9l-4 7" /></svg>
            Graph
          </button>
        </div>
        <label class="field"><span class="sr-only">Search notes</span><input v-model="search" type="search" class="input !py-1.5 text-xs" placeholder="Search notes…" /></label>
      </div>
      <nav class="flex-1 overflow-y-auto p-1.5" aria-label="Notes">
        <p v-if="!list.length" class="p-3 text-xs text-ink/55">{{ search ? 'No matching notes.' : 'No notes yet.' }}</p>
        <button
          v-for="n in list"
          :key="n.id"
          class="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm"
          :class="n.id === selectedId && mode === 'note' ? 'bg-panel font-medium text-ink' : 'text-ink/70 hover:bg-panel/60'"
          @click="(save(), (selectedId = n.id), (mode = 'note'))"
        >
          <span v-if="n.pinned" class="text-flag" aria-label="Pinned">●</span>
          <span class="truncate">{{ n.title }}</span>
        </button>
      </nav>
      <p class="border-t border-dashed border-ink/15 px-3 py-2 text-[11px] text-ink/50">
        Link with <code class="font-mono">[[Title]]</code> · tag with <code class="font-mono">#tag</code>
      </p>
    </aside>

    <!-- main -->
    <NoteGraph v-if="mode === 'graph'" :nodes="graph.nodes" :edges="graph.edges" :active="selected ? `note:${selected.id}` : null" :height="620" @open="open" />
    <div v-else-if="!selected" class="panel grid place-items-center p-12 text-center text-sm text-ink/60">
      <div>
        <p class="font-display text-lg text-ink">A second brain for this project</p>
        <p class="mt-1">Capture decisions, research and specs. Connect them with [[links]] and watch the graph grow.</p>
        <button class="btn-primary mt-5" @click="create()">Write the first note</button>
      </div>
    </div>
    <div v-else class="grid gap-4 xl:grid-cols-[1fr_240px]">
      <article class="panel min-w-0">
        <div class="panel-head flex-wrap">
          <label class="field min-w-0 flex-1"
            ><span class="sr-only">Note title</span
            ><input v-model="title" maxlength="200" class="w-full bg-transparent font-display text-xl font-medium outline-none" @blur="save"
          /></label>
          <div class="flex items-center gap-2">
            <span class="text-[11px]" :class="status === 'error' ? 'text-rust' : 'text-ink/50'" role="status">{{ STATUS[status] }}</span>
            <div class="flex rounded-full border border-ink/15 p-0.5" role="group" aria-label="Editor layout">
              <button
                v-for="v in ['edit', 'split', 'preview'] as const"
                :key="v"
                class="rounded-full px-2.5 py-0.5 text-xs capitalize"
                :class="view === v ? 'bg-ink text-paper' : 'text-ink/60'"
                :aria-pressed="view === v"
                @click="view = v"
              >
                {{ v }}
              </button>
            </div>
            <button class="btn-ghost btn-sm" :aria-pressed="selected.pinned" @click="togglePin">{{ selected.pinned ? 'Unpin' : 'Pin' }}</button>
            <button class="btn-danger btn-sm" @click="remove">Delete</button>
          </div>
        </div>
        <div class="grid min-h-[420px]" :class="view === 'split' ? 'md:grid-cols-2' : ''">
          <div v-if="view !== 'preview'" class="relative border-ink/10" :class="view === 'split' ? 'md:border-r' : ''">
            <label class="sr-only" for="note-editor">Note body (Markdown)</label>
            <textarea
              id="note-editor"
              ref="editor"
              v-model="body"
              class="h-full min-h-[420px] w-full resize-none bg-transparent p-5 font-mono text-[13px] leading-6 outline-none"
              placeholder="Write in Markdown. Type [[ to link a note, document, meeting or task."
              spellcheck="true"
              @input="onInput"
              @keydown="onKey"
              @blur="(suggest = null), save()"
            />
            <ul
              v-if="suggest && candidates.length"
              class="absolute left-5 right-5 top-12 z-20 max-h-64 overflow-y-auto rounded-lg border border-ink/15 bg-sheet py-1 shadow-xl"
              role="listbox"
              aria-label="Link suggestions"
            >
              <li
                v-for="(c, i) in candidates"
                :key="c.label + c.hint"
                role="option"
                :aria-selected="i === suggest.index"
                class="flex cursor-pointer justify-between gap-3 px-3 py-1.5 text-sm"
                :class="i === suggest.index ? 'bg-panel' : ''"
                @mousedown.prevent="pick(c.label)"
              >
                <span class="truncate">{{ c.label }}</span><span class="shrink-0 truncate font-mono text-[10px] text-ink/50">{{ c.hint }}</span>
              </li>
            </ul>
          </div>
          <div v-if="view !== 'edit'" class="min-w-0 p-5">
            <MarkdownView :source="body" empty="Start writing — the preview appears here." @wikilink="follow" />
          </div>
        </div>
        <p class="border-t border-dashed border-ink/15 px-5 py-2 text-[11px] text-ink/50">
          Created by {{ selected.author_name }}<template v-if="selected.updated_by_name"> · last edited by {{ selected.updated_by_name }}</template>
          · {{ new Date(selected.updated_at).toLocaleString('en-GB', { timeZone: 'Asia/Kathmandu' }) }}
        </p>
      </article>
      <aside class="grid content-start gap-4">
        <section class="panel">
          <h3 class="panel-head ledger-label">Backlinks · {{ backlinks.length }}</h3>
          <div class="panel-body grid gap-1.5 !py-3">
            <p v-if="!backlinks.length" class="text-xs text-ink/55">Nothing links here yet.</p>
            <button v-for="b in backlinks" :key="b.id" class="truncate text-left text-sm text-river hover:underline" @click="open(b)">
              {{ b.kind === 'meeting' ? '◷ ' : '' }}{{ b.label }}
            </button>
          </div>
        </section>
        <section class="panel">
          <h3 class="panel-head ledger-label">Links out · {{ outgoing.length }}</h3>
          <div class="panel-body grid gap-1.5 !py-3">
            <p v-if="!outgoing.length" class="text-xs text-ink/55">Type [[ to link something.</p>
            <button
              v-for="o in outgoing"
              :key="o.id"
              class="flex items-center gap-2 truncate text-left text-sm hover:underline"
              :class="o.kind === 'ghost' ? 'text-ink/50' : 'text-river'"
              :title="o.kind === 'ghost' ? 'Not written yet — click to create' : o.kind"
              @click="open(o)"
            >
              <span class="font-mono text-[9px] uppercase text-ink/45">{{ o.kind === 'ghost' ? 'new' : o.kind }}</span>
              <span class="truncate">{{ o.label }}</span>
            </button>
          </div>
        </section>
        <section v-if="tags.length" class="panel">
          <h3 class="panel-head ledger-label">Tags</h3>
          <div class="panel-body flex flex-wrap gap-1.5 !py-3">
            <button v-for="t in tags" :key="t" class="rounded-full border border-ink/15 px-2 py-0.5 text-xs hover:bg-panel" @click="search = '#' + t">#{{ t }}</button>
          </div>
        </section>
        <NoteGraph
          v-if="outgoing.length || backlinks.length"
          :nodes="graph.nodes.filter((n) => n.id === `note:${selected!.id}` || graph.edges.some((e) => (e.source === n.id || e.target === n.id) && (e.source === `note:${selected!.id}` || e.target === `note:${selected!.id}`)))"
          :edges="graph.edges.filter((e) => e.source === `note:${selected!.id}` || e.target === `note:${selected!.id}`)"
          :active="`note:${selected.id}`"
          :height="220"
          compact
          @open="open"
        />
      </aside>
    </div>
  </div>
</template>
