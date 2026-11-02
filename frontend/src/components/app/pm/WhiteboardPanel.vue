<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { isAxiosError } from 'axios'
import api from '@/api/api'
import { toast } from '../ui/toast'
import { confirmDialog } from '../ui/confirm'
import { errorMessage, type Project, type WbElement, type Whiteboard } from './pm'
const props = defineProps<{ project: Project; boards: Whiteboard[] }>()
const emit = defineEmits<{ changed: [] }>()

type Tool = 'select' | 'hand' | 'sticky' | 'rect' | 'ellipse' | 'text' | 'pen' | 'arrow'
const TOOLS: { id: Tool; key: string; label: string; icon: string }[] = [
  { id: 'select', key: 'v', label: 'Select', icon: 'M5 3l14 8-6 2-2 6z' },
  { id: 'hand', key: 'h', label: 'Pan', icon: 'M8 11V5a1.5 1.5 0 0 1 3 0v5m0-1V4a1.5 1.5 0 0 1 3 0v6m0-3a1.5 1.5 0 0 1 3 0v7a6 6 0 0 1-6 6h-1a6 6 0 0 1-5-3l-2-4a1.5 1.5 0 0 1 2.5-1.5L8 14' },
  { id: 'sticky', key: 's', label: 'Sticky note', icon: 'M4 4h16v11l-5 5H4zM15 20v-5h5' },
  { id: 'rect', key: 'r', label: 'Rectangle', icon: 'M4 6h16v12H4z' },
  { id: 'ellipse', key: 'o', label: 'Ellipse', icon: 'M12 5c5 0 9 3 9 7s-4 7-9 7-9-3-9-7 4-7 9-7z' },
  { id: 'text', key: 't', label: 'Text', icon: 'M5 6V4h14v2M12 4v16M9 20h6' },
  { id: 'arrow', key: 'a', label: 'Arrow', icon: 'M5 19L19 5m0 0h-8m8 0v8' },
  { id: 'pen', key: 'p', label: 'Pen', icon: 'M4 20l4-1L19 8l-3-3L5 16zM14 7l3 3' },
]
const COLORS = ['#f6d36b', '#f2a07b', '#9fd3a8', '#9cc7e0', '#d7b8e8', '#ebe5d9', '#1a1a1a', '#aa4825']

const boardId = ref<number | null>(props.boards[0]?.id ?? null)
const board = computed(() => props.boards.find((b) => b.id === boardId.value) || null)
const els = ref<WbElement[]>([])
const version = ref(1)
const tool = ref<Tool>('select')
const color = ref(COLORS[0]!)
const selected = ref<string | null>(null)
const editingId = ref<string | null>(null)
const view = reactive({ x: 0, y: 0, k: 1 })
const state = ref<'saved' | 'dirty' | 'saving' | 'conflict'>('saved')
const svg = ref<SVGSVGElement | null>(null)

function loadBoard(b: Whiteboard | null) {
  els.value = structuredClone(b?.data.elements || [])
  version.value = b?.version || 1
  history.length = 0
  future.length = 0
  selected.value = editingId.value = null
  state.value = 'saved'
}
watch(board, (b, old) => b?.id !== old?.id && loadBoard(b), { immediate: true })

// ── history + autosave ──
const history: string[] = []
const future: string[] = []
function checkpoint() {
  history.push(JSON.stringify(els.value))
  if (history.length > 60) history.shift()
  future.length = 0
}
function undo() {
  if (!history.length) return
  future.push(JSON.stringify(els.value))
  els.value = JSON.parse(history.pop()!)
  changed()
}
function redo() {
  if (!future.length) return
  history.push(JSON.stringify(els.value))
  els.value = JSON.parse(future.pop()!)
  changed()
}
let timer = 0
function changed() {
  if (state.value === 'conflict') return
  state.value = 'dirty'
  clearTimeout(timer)
  timer = window.setTimeout(save, 1500)
}
async function save() {
  clearTimeout(timer)
  if (!board.value || state.value !== 'dirty') return
  state.value = 'saving'
  try {
    const { data } = await api.patch<Whiteboard>(`pm/whiteboards/${board.value.id}/`, { data: { elements: els.value }, version: version.value })
    version.value = data.version
    state.value = 'saved'
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 409) state.value = 'conflict'
    else {
      state.value = 'dirty'
      toast.error(errorMessage(e))
    }
  }
}
async function reloadLatest() {
  const { data } = await api.get<Whiteboard>(`pm/whiteboards/${board.value!.id}/`)
  loadBoard(data)
}
onBeforeUnmount(save)

// ── geometry ──
const uid = () => Math.random().toString(36).slice(2, 10)
function world(e: PointerEvent | MouseEvent) {
  const r = svg.value!.getBoundingClientRect()
  return { x: (e.clientX - r.left - view.x) / view.k, y: (e.clientY - r.top - view.y) / view.k }
}
const byId = (id: string | null) => els.value.find((e) => e.id === id)
const box = (e: WbElement) => ({ x: Math.min(e.x, e.x + e.w), y: Math.min(e.y, e.y + e.h), w: Math.abs(e.w), h: Math.abs(e.h) })
const penPath = (e: WbElement) => {
  const p = e.points || []
  let d = ''
  for (let i = 0; i < p.length; i += 2) d += `${i ? 'L' : 'M'}${(e.x + p[i]!).toFixed(1)} ${(e.y + p[i + 1]!).toFixed(1)}`
  return d
}
const ink = (c: string) => (['#1a1a1a', '#aa4825'].includes(c) ? '#fbf8f2' : '#1a1a1a')

// ── pointer interactions ──
type Gesture =
  | { kind: 'pan'; sx: number; sy: number; ox: number; oy: number }
  | { kind: 'move'; id: string; sx: number; sy: number; ox: number; oy: number; moved: boolean }
  | { kind: 'resize'; id: string }
  | { kind: 'draw'; id: string }
let gesture: Gesture | null = null
const spaceHeld = ref(false)

function onDown(e: PointerEvent, el?: WbElement) {
  if (editingId.value) commitText()
  svg.value!.setPointerCapture(e.pointerId)
  const p = world(e)
  if (tool.value === 'hand' || spaceHeld.value || e.button === 1) {
    gesture = { kind: 'pan', sx: e.clientX, sy: e.clientY, ox: view.x, oy: view.y }
    return
  }
  if (tool.value === 'select') {
    selected.value = el?.id || null
    if (el) gesture = { kind: 'move', id: el.id, sx: p.x, sy: p.y, ox: el.x, oy: el.y, moved: false }
    return
  }
  checkpoint()
  const base = { id: uid(), x: p.x, y: p.y, color: color.value }
  const t = tool.value
  const created: WbElement =
    t === 'sticky'
      ? { ...base, type: 'sticky', x: p.x - 80, y: p.y - 60, w: 160, h: 120, text: '' }
      : t === 'text'
        ? { ...base, type: 'text', w: 220, h: 40, text: '', color: color.value === COLORS[0] ? '#1a1a1a' : color.value }
        : t === 'pen'
          ? { ...base, type: 'pen', w: 0, h: 0, points: [0, 0] }
          : { ...base, type: t, w: 0, h: 0, text: '' }
  els.value.push(created)
  selected.value = created.id
  if (t === 'sticky' || t === 'text') {
    tool.value = 'select'
    changed()
    nextTick(() => editText(created))
  } else gesture = { kind: 'draw', id: created.id }
}
function onMove(e: PointerEvent) {
  if (!gesture) return
  if (gesture.kind === 'pan') {
    view.x = gesture.ox + e.clientX - gesture.sx
    view.y = gesture.oy + e.clientY - gesture.sy
    return
  }
  const p = world(e)
  const el = byId(gesture.id)
  if (!el) return
  if (gesture.kind === 'move') {
    if (!gesture.moved) {
      checkpoint()
      gesture.moved = true
    }
    el.x = gesture.ox + p.x - gesture.sx
    el.y = gesture.oy + p.y - gesture.sy
  } else if (gesture.kind === 'resize') {
    el.w = Math.max(p.x - el.x, 30)
    el.h = Math.max(p.y - el.y, 24)
  } else if (el.type === 'pen') {
    el.points!.push(+(p.x - el.x).toFixed(1), +(p.y - el.y).toFixed(1))
  } else {
    el.w = p.x - el.x
    el.h = p.y - el.y
  }
}
function onUp() {
  const g = gesture
  gesture = null
  if (!g || g.kind === 'pan') return
  const el = byId(g.id)
  if (g.kind === 'draw' && el) {
    if (el.type === 'pen') {
      const xs = el.points!.filter((_, i) => i % 2 === 0)
      const ys = el.points!.filter((_, i) => i % 2 === 1)
      Object.assign(el, { w: Math.max(...xs), h: Math.max(...ys) })
    } else if (Math.abs(el.w) < 6 && Math.abs(el.h) < 6) {
      // a click without a drag: drop a default-size shape
      Object.assign(el, el.type === 'arrow' ? { w: 140, h: 0 } : { x: el.x - 70, y: el.y - 45, w: 140, h: 90 })
    } else if (el.type !== 'arrow') Object.assign(el, box(el))
  }
  if (g.kind !== 'move' || g.moved) changed()
}
function startResize(e: PointerEvent, el: WbElement) {
  e.stopPropagation()
  svg.value!.setPointerCapture(e.pointerId)
  checkpoint()
  gesture = { kind: 'resize', id: el.id }
}
function onWheel(e: WheelEvent) {
  e.preventDefault()
  const r = svg.value!.getBoundingClientRect()
  const f = e.deltaY < 0 ? 1.1 : 0.9
  const k = Math.min(4, Math.max(0.2, view.k * f))
  const mx = e.clientX - r.left
  const my = e.clientY - r.top
  view.x = mx - ((mx - view.x) * k) / view.k
  view.y = my - ((my - view.y) * k) / view.k
  view.k = k
}
function zoomTo(k: number) {
  view.k = Math.min(4, Math.max(0.2, k))
}
function fit() {
  if (!els.value.length) return Object.assign(view, { x: 0, y: 0, k: 1 })
  const bs = els.value.map(box)
  const minX = Math.min(...bs.map((b) => b.x)) - 40
  const minY = Math.min(...bs.map((b) => b.y)) - 40
  const maxX = Math.max(...bs.map((b) => b.x + b.w)) + 40
  const maxY = Math.max(...bs.map((b) => b.y + b.h)) + 40
  const r = svg.value!.getBoundingClientRect()
  const k = Math.min(r.width / (maxX - minX), r.height / (maxY - minY), 2)
  Object.assign(view, { k, x: -minX * k + (r.width - (maxX - minX) * k) / 2, y: -minY * k + (r.height - (maxY - minY) * k) / 2 })
}

// ── text editing ──
const textDraft = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)
function editText(el: WbElement) {
  if (!['sticky', 'text', 'rect', 'ellipse'].includes(el.type)) return
  editingId.value = el.id
  textDraft.value = el.text || ''
  nextTick(() => textarea.value?.focus())
}
function commitText() {
  const el = byId(editingId.value)
  editingId.value = null
  if (!el || el.text === textDraft.value) return
  checkpoint()
  el.text = textDraft.value
  if (el.type === 'text' && !el.text.trim()) els.value = els.value.filter((x) => x.id !== el.id)
  changed()
}

// ── commands ──
function remove() {
  if (!selected.value) return
  checkpoint()
  els.value = els.value.filter((e) => e.id !== selected.value)
  selected.value = null
  changed()
}
function duplicate() {
  const el = byId(selected.value)
  if (!el) return
  checkpoint()
  const copy = { ...structuredClone(el), id: uid(), x: el.x + 24, y: el.y + 24 }
  els.value.push(copy)
  selected.value = copy.id
  changed()
}
function recolor(c: string) {
  color.value = c
  const el = byId(selected.value)
  if (el) {
    checkpoint()
    el.color = c
    changed()
  }
}
function order(front: boolean) {
  const el = byId(selected.value)
  if (!el) return
  checkpoint()
  els.value = front ? [...els.value.filter((e) => e !== el), el] : [el, ...els.value.filter((e) => e !== el)]
  changed()
}
function onKey(e: KeyboardEvent) {
  const typing = (e.target as HTMLElement).closest?.('input, textarea, select, [contenteditable], [role="dialog"]')
  if (typing || !board.value) return
  const mod = e.ctrlKey || e.metaKey
  if (mod && e.key.toLowerCase() === 'z') return e.preventDefault(), e.shiftKey ? redo() : undo()
  if (mod && e.key.toLowerCase() === 'y') return e.preventDefault(), redo()
  if (mod && e.key.toLowerCase() === 'd') return e.preventDefault(), duplicate()
  if (mod) return
  if (e.key === 'Delete' || e.key === 'Backspace') return e.preventDefault(), remove()
  if (e.key === ' ') return e.preventDefault(), (spaceHeld.value = true)
  if (e.key === 'Escape') return (selected.value = null)
  const t = TOOLS.find((x) => x.key === e.key.toLowerCase())
  if (t) tool.value = t.id
}
const onKeyUp = (e: KeyboardEvent) => e.key === ' ' && (spaceHeld.value = false)
onMounted(() => {
  window.addEventListener('keydown', onKey)
  window.addEventListener('keyup', onKeyUp)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('keyup', onKeyUp)
})

// ── boards ──
async function newBoard() {
  try {
    const { data } = await api.post<Whiteboard>('pm/whiteboards/', { project: props.project.id, title: `Board ${props.boards.length + 1}`, data: { elements: [] } })
    emit('changed')
    boardId.value = data.id
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function rename(e: Event) {
  const title = (e.target as HTMLInputElement).value.trim()
  if (!title || title === board.value?.title) return
  try {
    await api.patch(`pm/whiteboards/${board.value!.id}/`, { title })
    emit('changed')
  } catch (err) {
    toast.error(errorMessage(err))
  }
}
async function removeBoard() {
  if (!(await confirmDialog({ title: `Delete “${board.value!.title}”?`, body: 'Everything on this whiteboard is lost.', confirmLabel: 'Delete board', danger: true }))) return
  try {
    await api.delete(`pm/whiteboards/${board.value!.id}/`)
    boardId.value = props.boards.find((b) => b.id !== boardId.value)?.id ?? null
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
function exportSvg() {
  const clone = svg.value!.cloneNode(true) as SVGSVGElement
  clone.querySelectorAll('[data-ui]').forEach((n) => n.remove())
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const blob = new Blob([clone.outerHTML], { type: 'image/svg+xml' })
  const href = URL.createObjectURL(blob)
  Object.assign(document.createElement('a'), { href, download: `${board.value?.title || 'whiteboard'}.svg` }).click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
const STATE = { saved: 'All changes saved', dirty: 'Unsaved…', saving: 'Saving…', conflict: 'Someone else saved this board' }
const cursor = computed(() => (tool.value === 'hand' || spaceHeld.value ? 'cursor-grab' : tool.value === 'select' ? 'cursor-default' : 'cursor-crosshair'))
const sel = computed(() => byId(selected.value))
</script>
<template>
  <div class="grid gap-3">
    <!-- board bar -->
    <div class="flex flex-wrap items-center gap-2">
      <label class="field"
        ><span class="sr-only">Whiteboard</span>
        <select v-model="boardId" class="input !w-48" @change="save">
          <option v-if="!boards.length" :value="null" disabled>No whiteboards</option>
          <option v-for="b in boards" :key="b.id" :value="b.id">{{ b.title }}</option>
        </select></label
      >
      <label v-if="board" class="field"><span class="sr-only">Rename whiteboard</span><input :value="board.title" maxlength="120" class="input !w-44" @change="rename" /></label>
      <button class="btn-ghost btn-sm" @click="newBoard">New board</button>
      <button v-if="board" class="btn-ghost btn-sm" @click="exportSvg">Export SVG</button>
      <button v-if="board" class="text-xs text-rust" @click="removeBoard">Delete</button>
      <span class="ml-auto text-xs" :class="state === 'conflict' ? 'text-rust' : 'text-ink/50'" role="status">
        {{ STATE[state] }}
        <button v-if="state === 'conflict'" class="ml-2 underline" @click="reloadLatest">Load latest</button>
      </span>
    </div>

    <div v-if="!board" class="panel grid place-items-center p-14 text-center text-sm text-ink/60">
      <div>
        <p class="font-display text-lg text-ink">A blank wall for ideas</p>
        <p class="mt-1">Sketch flows, cluster sticky notes, map architecture — together.</p>
        <button class="btn-primary mt-5" @click="newBoard">Create a whiteboard</button>
      </div>
    </div>
    <div v-else class="relative overflow-hidden rounded-xl border border-ink/10 bg-paper">
      <!-- toolbar -->
      <div class="absolute left-3 top-3 z-10 flex flex-col gap-1 rounded-xl border border-ink/10 bg-sheet p-1 shadow-sm" role="toolbar" aria-label="Whiteboard tools">
        <button
          v-for="t in TOOLS"
          :key="t.id"
          class="grid h-9 w-9 place-items-center rounded-lg"
          :class="tool === t.id ? 'bg-ink text-paper' : 'text-ink/70 hover:bg-panel'"
          :aria-pressed="tool === t.id"
          :title="`${t.label} (${t.key.toUpperCase()})`"
          :aria-label="t.label"
          @click="tool = t.id"
        >
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="t.icon" /></svg>
        </button>
      </div>
      <div class="absolute left-1/2 top-3 z-10 flex -translate-x-1/2 items-center gap-1 rounded-full border border-ink/10 bg-sheet px-2 py-1 shadow-sm">
        <button
          v-for="c in COLORS"
          :key="c"
          class="h-5 w-5 rounded-full border"
          :class="color === c ? 'ring-2 ring-ink ring-offset-1 ring-offset-sheet' : 'border-ink/15'"
          :style="{ background: c }"
          :aria-label="`Colour ${c}`"
          @click="recolor(c)"
        />
        <template v-if="sel">
          <span class="mx-1 h-4 w-px bg-ink/15" />
          <button class="rounded px-1.5 text-xs hover:bg-panel" title="Bring to front" @click="order(true)">Front</button>
          <button class="rounded px-1.5 text-xs hover:bg-panel" title="Send to back" @click="order(false)">Back</button>
          <button class="rounded px-1.5 text-xs hover:bg-panel" title="Duplicate (Ctrl+D)" @click="duplicate">Copy</button>
          <button class="rounded px-1.5 text-xs text-rust hover:bg-panel" title="Delete (Del)" @click="remove">Delete</button>
        </template>
      </div>
      <div class="absolute bottom-3 right-3 z-10 flex items-center gap-1 rounded-full border border-ink/10 bg-sheet px-1.5 py-1 text-xs shadow-sm">
        <button class="rounded px-2 hover:bg-panel" aria-label="Undo" title="Undo (Ctrl+Z)" :disabled="!history.length" @click="undo">↶</button>
        <button class="rounded px-2 hover:bg-panel" aria-label="Redo" title="Redo (Ctrl+Shift+Z)" @click="redo">↷</button>
        <span class="mx-1 h-4 w-px bg-ink/15" />
        <button class="rounded px-2 hover:bg-panel" aria-label="Zoom out" @click="zoomTo(view.k * 0.8)">−</button>
        <span class="readout w-11 text-center">{{ Math.round(view.k * 100) }}%</span>
        <button class="rounded px-2 hover:bg-panel" aria-label="Zoom in" @click="zoomTo(view.k * 1.25)">+</button>
        <button class="rounded px-2 hover:bg-panel" @click="fit">Fit</button>
      </div>

      <svg
        ref="svg"
        class="block h-[72vh] w-full touch-none select-none"
        :class="cursor"
        role="application"
        :aria-label="`Whiteboard ${board.title}, ${els.length} items`"
        @pointerdown="onDown($event)"
        @pointermove="onMove"
        @pointerup="onUp"
        @wheel="onWheel"
      >
        <defs>
          <pattern id="wb-dots" :width="24 * view.k" :height="24 * view.k" patternUnits="userSpaceOnUse" :x="view.x" :y="view.y">
            <circle :cx="1" :cy="1" r="1" fill="var(--color-ink)" fill-opacity=".14" />
          </pattern>
          <marker id="wb-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill="context-stroke" />
          </marker>
        </defs>
        <rect data-ui width="100%" height="100%" fill="url(#wb-dots)" />
        <g :transform="`translate(${view.x} ${view.y}) scale(${view.k})`">
          <g v-for="el in els" :key="el.id" @pointerdown.stop="onDown($event, el)" @dblclick.stop="editText(el)">
            <template v-if="el.type === 'sticky'">
              <rect :x="el.x + 3" :y="el.y + 4" :width="el.w" :height="el.h" rx="4" fill="#000" fill-opacity=".08" />
              <rect :x="el.x" :y="el.y" :width="el.w" :height="el.h" rx="4" :fill="el.color" />
            </template>
            <rect v-else-if="el.type === 'rect'" :x="el.x" :y="el.y" :width="el.w" :height="el.h" rx="8" :fill="el.color" fill-opacity=".25" :stroke="el.color" stroke-width="2" />
            <ellipse v-else-if="el.type === 'ellipse'" :cx="el.x + el.w / 2" :cy="el.y + el.h / 2" :rx="el.w / 2" :ry="el.h / 2" :fill="el.color" fill-opacity=".25" :stroke="el.color" stroke-width="2" />
            <path v-else-if="el.type === 'pen'" :d="penPath(el)" fill="none" :stroke="el.color === COLORS[0] ? '#1a1a1a' : el.color" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
            <g v-else-if="el.type === 'arrow'">
              <line :x1="el.x" :y1="el.y" :x2="el.x + el.w" :y2="el.y + el.h" stroke="transparent" stroke-width="14" />
              <line :x1="el.x" :y1="el.y" :x2="el.x + el.w" :y2="el.y + el.h" :stroke="el.color === COLORS[0] ? '#1a1a1a' : el.color" stroke-width="2.5" marker-end="url(#wb-arrow)" />
            </g>
            <foreignObject
              v-if="['sticky', 'text', 'rect', 'ellipse'].includes(el.type) && el.text && editingId !== el.id"
              :x="el.x"
              :y="el.y"
              :width="Math.max(el.w, 1)"
              :height="Math.max(el.h, 1)"
              class="pointer-events-none"
            >
              <div
                xmlns="http://www.w3.org/1999/xhtml"
                class="flex h-full w-full overflow-hidden whitespace-pre-wrap break-words"
                :class="el.type === 'text' ? 'items-start p-1 text-lg font-medium' : 'items-center justify-center p-3 text-center text-sm'"
                :style="{ color: el.type === 'text' ? el.color : ink(el.color), fontFamily: el.type === 'sticky' ? 'inherit' : undefined }"
              >
                {{ el.text }}
              </div>
            </foreignObject>
          </g>
          <!-- selection chrome -->
          <g v-if="sel && !editingId" data-ui>
            <rect
              :x="box(sel).x - 4"
              :y="box(sel).y - 4"
              :width="box(sel).w + 8"
              :height="box(sel).h + 8"
              fill="none"
              stroke="var(--color-flag)"
              stroke-dasharray="4 3"
              :stroke-width="1.5 / view.k"
              class="pointer-events-none"
            />
            <rect
              v-if="!['pen', 'arrow'].includes(sel.type)"
              :x="sel.x + sel.w - 5 / view.k"
              :y="sel.y + sel.h - 5 / view.k"
              :width="10 / view.k"
              :height="10 / view.k"
              fill="var(--color-flag)"
              class="cursor-nwse-resize"
              @pointerdown="startResize($event, sel)"
            />
          </g>
          <foreignObject v-if="editingId && byId(editingId)" data-ui :x="byId(editingId)!.x" :y="byId(editingId)!.y" :width="byId(editingId)!.w" :height="Math.max(byId(editingId)!.h, 40)">
            <textarea
              ref="textarea"
              v-model="textDraft"
              xmlns="http://www.w3.org/1999/xhtml"
              aria-label="Edit text"
              class="h-full w-full resize-none rounded border-2 border-flag bg-sheet/95 p-2 text-sm text-ink outline-none"
              @pointerdown.stop
              @blur="commitText"
              @keydown.esc="commitText"
              @keydown.enter.ctrl="commitText"
            />
          </foreignObject>
        </g>
      </svg>
      <p class="pointer-events-none absolute bottom-3 left-3 text-[11px] text-ink/45">
        Double-click to write · Space+drag to pan · scroll to zoom · Del to delete
      </p>
    </div>
  </div>
</template>
