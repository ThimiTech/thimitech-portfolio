<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { GraphEdge, GraphNode, NodeKind } from './pm'
const props = withDefaults(
  defineProps<{ nodes: GraphNode[]; edges: GraphEdge[]; active?: string | null; height?: number; compact?: boolean }>(),
  { active: null, height: 560, compact: false },
)
const emit = defineEmits<{ open: [node: GraphNode] }>()

const TONE: Record<NodeKind, string> = {
  note: 'var(--color-river)',
  doc: 'var(--color-sky)',
  task: 'var(--color-moss)',
  meeting: 'var(--color-flag)',
  ghost: 'transparent',
}
const LABEL: Record<NodeKind, string> = { note: 'Notes', doc: 'Documents', task: 'Tasks', meeting: 'Meetings', ghost: 'Unwritten' }
const show = reactive<Record<NodeKind, boolean>>({ note: true, doc: true, task: true, meeting: true, ghost: true })
const orphans = ref(true)
const query = ref('')

const degree = computed(() => {
  const d = new Map<string, number>()
  for (const e of props.edges) {
    d.set(e.source, (d.get(e.source) || 0) + 1)
    d.set(e.target, (d.get(e.target) || 0) + 1)
  }
  return d
})
const visible = computed(() => props.nodes.filter((n) => show[n.kind] && (orphans.value || degree.value.get(n.id))))
const visibleIds = computed(() => new Set(visible.value.map((n) => n.id)))
const links = computed(() => props.edges.filter((e) => visibleIds.value.has(e.source) && visibleIds.value.has(e.target)))

// ── simulation ── ponytail: O(n²) repulsion, fine to ~800 nodes; switch to a quadtree (d3-force) beyond that
const pos = reactive(new Map<string, { x: number; y: number; vx: number; vy: number; fixed?: boolean }>())
let alpha = 1
let frame = 0
function seed(id: string) {
  let h = 0
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) | 0
  const a = (h % 360) * (Math.PI / 180)
  const r = 80 + (Math.abs(h) % 160)
  return { x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0 }
}
function tick() {
  const ns = visible.value.map((n) => pos.get(n.id)!)
  for (let i = 0; i < ns.length; i++)
    for (let j = i + 1; j < ns.length; j++) {
      const a = ns[i]!, b = ns[j]!
      let dx = a.x - b.x, dy = a.y - b.y
      const d2 = Math.max(dx * dx + dy * dy, 25)
      const f = (1600 / d2) * alpha
      const d = Math.sqrt(d2)
      dx /= d
      dy /= d
      a.vx += dx * f; a.vy += dy * f
      b.vx -= dx * f; b.vy -= dy * f
    }
  for (const e of links.value) {
    const a = pos.get(e.source)!, b = pos.get(e.target)!
    const dx = b.x - a.x, dy = b.y - a.y
    const d = Math.sqrt(dx * dx + dy * dy) || 1
    const f = ((d - 80) / d) * 0.05 * alpha
    a.vx += dx * f; a.vy += dy * f
    b.vx -= dx * f; b.vy -= dy * f
  }
  for (const p of ns) {
    p.vx -= p.x * 0.012 * alpha
    p.vy -= p.y * 0.012 * alpha
    if (!p.fixed) {
      p.x += p.vx
      p.y += p.vy
    }
    p.vx *= 0.6
    p.vy *= 0.6
  }
  alpha *= 0.985
  frame = alpha > 0.02 ? requestAnimationFrame(tick) : 0
}
function reheat(a = 0.8) {
  alpha = Math.max(alpha, a)
  if (!frame) frame = requestAnimationFrame(tick)
}
watch(
  visible,
  (ns) => {
    for (const n of ns) if (!pos.has(n.id)) pos.set(n.id, seed(n.id))
    reheat(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 0.3 : 1)
  },
  { immediate: true },
)
onMounted(() => {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 250 && alpha > 0.02; i++) tick() // settle synchronously, then show a still graph
    cancelAnimationFrame(frame)
    frame = 0
  }
})
onBeforeUnmount(() => cancelAnimationFrame(frame))

// ── view: pan / zoom / drag ──
const svg = ref<SVGSVGElement | null>(null)
const view = reactive({ x: 0, y: 0, k: 1 })
const hover = ref<string | null>(null)
let gesture: { kind: 'pan' | 'node'; id?: string; sx: number; sy: number; ox: number; oy: number; moved: boolean } | null = null
function toGraph(e: PointerEvent) {
  const r = svg.value!.getBoundingClientRect()
  return { x: (e.clientX - r.left - r.width / 2 - view.x) / view.k, y: (e.clientY - r.top - r.height / 2 - view.y) / view.k }
}
function down(e: PointerEvent, id?: string) {
  ;(e.currentTarget as Element).setPointerCapture(e.pointerId)
  gesture = { kind: id ? 'node' : 'pan', id, sx: e.clientX, sy: e.clientY, ox: view.x, oy: view.y, moved: false }
  e.stopPropagation()
}
function move(e: PointerEvent) {
  if (!gesture) return
  if (Math.abs(e.clientX - gesture.sx) + Math.abs(e.clientY - gesture.sy) > 3) gesture.moved = true
  if (gesture.kind === 'pan') {
    view.x = gesture.ox + e.clientX - gesture.sx
    view.y = gesture.oy + e.clientY - gesture.sy
  } else if (gesture.moved) {
    const p = pos.get(gesture.id!)!
    Object.assign(p, toGraph(e), { fixed: true, vx: 0, vy: 0 })
    reheat(0.3)
  }
}
function up(node?: GraphNode) {
  if (gesture?.kind === 'node') {
    const p = pos.get(gesture.id!)
    if (p) p.fixed = false
    if (!gesture.moved && node) emit('open', node)
  }
  gesture = null
}
function wheel(e: WheelEvent) {
  e.preventDefault()
  view.k = Math.min(3, Math.max(0.25, view.k * (e.deltaY < 0 ? 1.1 : 0.9)))
}
function zoomBy(f: number) {
  view.k = Math.min(3, Math.max(0.25, view.k * f))
}
function reset() {
  Object.assign(view, { x: 0, y: 0, k: 1 })
  reheat()
}

const focus = computed(() => hover.value || props.active)
const neighbours = computed(() => {
  const s = new Set<string>()
  if (!focus.value) return s
  s.add(focus.value)
  for (const e of links.value) {
    if (e.source === focus.value) s.add(e.target)
    if (e.target === focus.value) s.add(e.source)
  }
  return s
})
const matches = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? new Set(visible.value.filter((n) => n.label.toLowerCase().includes(q)).map((n) => n.id)) : null
})
const dim = (id: string) => (matches.value ? !matches.value.has(id) : focus.value ? !neighbours.value.has(id) : false)
const radius = (id: string) => 5 + Math.min(degree.value.get(id) || 0, 10) * 1.2
const P = (id: string) => pos.get(id) || { x: 0, y: 0 }
</script>
<template>
  <div class="relative overflow-hidden rounded-xl border border-ink/10 bg-paper" :style="{ height: `${height}px` }">
    <div v-if="!compact" class="absolute left-3 top-3 z-10 flex flex-wrap items-center gap-2">
      <label class="field w-44"><span class="sr-only">Highlight nodes</span><input v-model="query" type="search" class="input !py-1 text-xs" placeholder="Highlight…" /></label>
      <label
        v-for="k in (Object.keys(LABEL) as NodeKind[])"
        :key="k"
        class="flex cursor-pointer items-center gap-1.5 rounded-full border border-ink/10 bg-sheet/90 px-2 py-0.5 text-[11px]"
        ><input v-model="show[k]" type="checkbox" class="sr-only" />
        <span class="h-2 w-2 rounded-full border" :style="{ background: show[k] ? TONE[k] : 'transparent', borderColor: k === 'ghost' ? 'currentColor' : TONE[k] }" />
        <span :class="show[k] ? '' : 'text-ink/40 line-through'">{{ LABEL[k] }}</span></label
      >
      <label class="flex items-center gap-1.5 text-[11px] text-ink/60"><input v-model="orphans" type="checkbox" class="accent-ink" /> Orphans</label>
    </div>
    <div v-if="!compact" class="absolute bottom-3 right-3 z-10 flex gap-1">
      <button class="btn-ghost btn-sm !bg-sheet" aria-label="Zoom in" @click="zoomBy(1.2)">+</button>
      <button class="btn-ghost btn-sm !bg-sheet" aria-label="Zoom out" @click="zoomBy(0.8)">−</button>
      <button class="btn-ghost btn-sm !bg-sheet" @click="reset">Re-center</button>
    </div>
    <p v-if="!visible.length" class="absolute inset-0 grid place-items-center text-sm text-ink/55">
      Write notes and link them with [[double brackets]] to grow the graph.
    </p>
    <svg
      ref="svg"
      class="h-full w-full cursor-grab touch-none select-none active:cursor-grabbing"
      role="img"
      :aria-label="`Knowledge graph: ${visible.length} items, ${links.length} links`"
      @pointerdown="down($event)"
      @pointermove="move"
      @pointerup="up()"
      @wheel="wheel"
    >
      <g :transform="`translate(${(svg?.clientWidth || 0) / 2 + view.x} ${height / 2 + view.y}) scale(${view.k})`">
        <line
          v-for="e in links"
          :key="`${e.source}|${e.target}`"
          :x1="P(e.source).x"
          :y1="P(e.source).y"
          :x2="P(e.target).x"
          :y2="P(e.target).y"
          stroke="var(--color-ink)"
          :stroke-opacity="focus && neighbours.has(e.source) && neighbours.has(e.target) ? 0.55 : dim(e.source) || dim(e.target) ? 0.05 : 0.18"
          :stroke-width="1 / view.k + 0.4"
        />
        <g
          v-for="n in visible"
          :key="n.id"
          :transform="`translate(${P(n.id).x} ${P(n.id).y})`"
          class="cursor-pointer"
          :opacity="dim(n.id) ? 0.18 : 1"
          @pointerdown="down($event, n.id)"
          @pointerup.stop="up(n)"
          @pointerenter="hover = n.id"
          @pointerleave="hover = null"
        >
          <circle
            :r="radius(n.id)"
            :fill="TONE[n.kind]"
            :stroke="n.kind === 'ghost' ? 'var(--color-ink)' : n.id === active ? 'var(--color-ink)' : 'var(--color-paper)'"
            :stroke-dasharray="n.kind === 'ghost' ? '2 2' : undefined"
            :stroke-opacity="n.kind === 'ghost' ? 0.5 : 1"
            :stroke-width="n.id === active ? 2.5 : 1.5"
          />
          <text
            v-if="view.k > 0.7 || neighbours.has(n.id) || (degree.get(n.id) || 0) > 3"
            :y="radius(n.id) + 12"
            text-anchor="middle"
            class="pointer-events-none fill-ink"
            :font-size="11 / Math.max(view.k, 0.8)"
            :font-weight="n.id === focus ? 600 : 400"
            :fill-opacity="n.kind === 'ghost' ? 0.5 : 0.85"
          >
            {{ n.label.length > 28 ? n.label.slice(0, 27) + '…' : n.label }}
          </text>
        </g>
      </g>
    </svg>
  </div>
</template>
