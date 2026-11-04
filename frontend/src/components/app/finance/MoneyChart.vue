<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { amount, saveBlob, shortAmount } from './finance'

/** Grouped bars: money in vs money out per period. Hover a month for exact values; table view and PNG download. */
const props = defineProps<{ title: string; rows: { label: string; in: number; out: number }[]; filename?: string }>()
const box = ref<HTMLElement | null>(null)
const svg = ref<SVGSVGElement | null>(null)
const width = ref(720)
const height = 240
const pad = { top: 12, right: 8, bottom: 26, left: 52 }
const hover = ref<number | null>(null)
const asTable = ref(false)
let ro: ResizeObserver | undefined
onMounted(() => {
  ro = new ResizeObserver(([e]) => (width.value = Math.max(320, Math.round(e!.contentRect.width))))
  if (box.value) ro.observe(box.value)
})
onBeforeUnmount(() => ro?.disconnect())

const empty = computed(() => props.rows.every((r) => !r.in && !r.out))
const max = computed(() => {
  const m = Math.max(1, ...props.rows.flatMap((r) => [r.in, r.out]))
  const step = 10 ** Math.floor(Math.log10(m))
  return Math.ceil(m / step) * step
})
const ticks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((f) => f * max.value))
const plotW = computed(() => width.value - pad.left - pad.right)
const plotH = height - pad.top - pad.bottom
const band = computed(() => plotW.value / Math.max(1, props.rows.length))
const barW = computed(() => Math.max(3, Math.min(18, (band.value - 10) / 2)))
const y = (v: number) => pad.top + plotH - (v / max.value) * plotH
/** Bar with 4px rounded data-end, square on the baseline. */
function bar(x: number, v: number) {
  const top = y(v)
  const h = pad.top + plotH - top
  if (h <= 0) return ''
  const r = Math.min(4, barW.value / 2, h)
  const w = barW.value
  return `M${x},${top + h}V${top + r}Q${x},${top} ${x + r},${top}H${x + w - r}Q${x + w},${top} ${x + w},${top + r}V${top + h}Z`
}
const groups = computed(() =>
  props.rows.map((r, i) => {
    const cx = pad.left + band.value * i + band.value / 2
    return { ...r, i, cx, xIn: cx - barW.value - 1, xOut: cx + 1, short: r.label.split(' ')[0]!.slice(0, 3) }
  }),
)
const tip = computed(() => (hover.value === null ? null : groups.value[hover.value]))

/** PNG export: copy computed colours/fonts onto a clone so CSS variables survive serialisation. */
async function downloadPng() {
  const src = svg.value
  if (!src) return
  const clone = src.cloneNode(true) as SVGSVGElement
  const a = src.querySelectorAll('*')
  const b = clone.querySelectorAll('*')
  a.forEach((el, i) => {
    const cs = getComputedStyle(el)
    const t = b[i] as SVGElement
    t.setAttribute('fill', cs.fill)
    t.setAttribute('stroke', cs.stroke)
    if (el.tagName === 'text') t.setAttribute('style', `font: ${cs.fontSize} ${cs.fontFamily}`)
  })
  const bg = getComputedStyle(box.value!).backgroundColor
  clone.insertAdjacentHTML('afterbegin', `<rect width="100%" height="100%" fill="${bg}"/>`)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const img = new Image()
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(clone))
  await img.decode()
  const canvas = Object.assign(document.createElement('canvas'), { width: width.value * 2, height: height * 2 })
  const ctx = canvas.getContext('2d')!
  ctx.scale(2, 2)
  ctx.drawImage(img, 0, 0)
  canvas.toBlob((blob) => blob && saveBlob(blob, (props.filename || 'chart') + '.png'))
}
</script>

<template>
  <figure class="panel p-5">
    <figcaption class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <h3 class="font-medium text-ink">{{ title }}</h3>
      <div class="flex flex-wrap items-center gap-4 text-xs text-ink/70">
        <span class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-chart-in" aria-hidden="true" />Money in</span>
        <span class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-chart-out" aria-hidden="true" />Money out</span>
        <button type="button" class="btn-ghost btn-sm" :aria-pressed="asTable" @click="asTable = !asTable">{{ asTable ? 'Chart' : 'Table' }}</button>
        <button v-if="!asTable && !empty" type="button" class="btn-ghost btn-sm" @click="downloadPng">PNG</button>
      </div>
    </figcaption>
    <p v-if="empty" class="py-10 text-center text-sm text-ink/55">No bank activity recorded in this period yet.</p>
    <div v-show="!asTable && !empty" ref="box" class="relative bg-sheet" @mouseleave="hover = null">
      <svg ref="svg" :width="width" :height="height" role="img" :aria-label="`${title}. Use the table view for exact values.`" class="block">
        <g class="text-ink/45" font-size="10" font-family="IBM Plex Mono, monospace">
          <template v-for="t in ticks" :key="t">
            <line :x1="pad.left" :x2="width - pad.right" :y1="y(t)" :y2="y(t)" class="stroke-ink/10" :stroke-dasharray="t ? '2 3' : ''" />
            <text :x="pad.left - 6" :y="y(t) + 3" text-anchor="end" class="fill-ink/50">{{ shortAmount(t) }}</text>
          </template>
        </g>
        <g v-for="g in groups" :key="g.i">
          <rect v-if="hover === g.i" :x="g.cx - band / 2" :y="pad.top" :width="band" :height="plotH" class="fill-ink/[0.04]" />
          <path :d="bar(g.xIn, g.in)" class="fill-chart-in" />
          <path :d="bar(g.xOut, g.out)" class="fill-chart-out" />
          <text :x="g.cx" :y="height - 8" text-anchor="middle" font-size="10" class="fill-ink/55">{{ g.short }}</text>
          <rect :x="g.cx - band / 2" :y="0" :width="band" :height="height" fill="transparent" @mouseenter="hover = g.i" @focus="hover = g.i"
            @blur="hover = null" tabindex="0" :aria-label="`${g.label}: in ${amount(g.in, 0)}, out ${amount(g.out, 0)}`" />
        </g>
      </svg>
      <div v-if="tip" class="pointer-events-none absolute top-2 z-10 min-w-44 rounded-lg border border-ink/15 bg-sheet px-3 py-2 text-xs shadow-lg"
        :style="{ left: Math.min(tip.cx + 12, width - 190) + 'px' }">
        <p class="font-medium text-ink">{{ tip.label }}</p>
        <p class="mt-1 flex justify-between gap-4"><span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-sm bg-chart-in" />In</span><span class="readout">{{ amount(tip.in) }}</span></p>
        <p class="flex justify-between gap-4"><span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-sm bg-chart-out" />Out</span><span class="readout">{{ amount(tip.out) }}</span></p>
        <p class="mt-1 flex justify-between gap-4 border-t border-ink/10 pt-1 text-ink/70"><span>Net</span><span class="readout">{{ amount(tip.in - tip.out) }}</span></p>
      </div>
    </div>
    <div v-if="asTable" class="overflow-x-auto">
      <table class="ledger-table">
        <thead><tr><th>Month</th><th class="text-right">Money in</th><th class="text-right">Money out</th><th class="text-right">Net</th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.label">
            <td>{{ r.label }}</td>
            <td class="readout text-right">{{ amount(r.in) }}</td>
            <td class="readout text-right">{{ amount(r.out) }}</td>
            <td class="readout text-right">{{ amount(r.in - r.out) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </figure>
</template>
