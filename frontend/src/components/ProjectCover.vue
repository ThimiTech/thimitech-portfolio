<script setup lang="ts">
/**
 * Generated cover art for projects without an uploaded image.
 * Four hand-drawn map studies in greyscale — no binary assets required.
 */
import { onMounted, ref } from 'vue'

const props = defineProps<{ variant: number }>()

const PALETTES = [
  { paper: '#ffffff', soft: '#eceef1', deep: '#0a0a0a', mid: '#7c8288', accent: '#0a0a0a' },
  { paper: '#fafbfb', soft: '#e6e9ec', deep: '#141618', mid: '#8d9399', accent: '#2b2f33' },
  { paper: '#ffffff', soft: '#f0f2f4', deep: '#0f1113', mid: '#6f757b', accent: '#0a0a0a' },
  { paper: '#f7f8f9', soft: '#e2e5e8', deep: '#101214', mid: '#878d93', accent: '#1c1f22' },
]

const canvas = ref<HTMLCanvasElement | null>(null)

onMounted(() => {
  const ctx = canvas.value?.getContext('2d')
  if (!ctx) return

  const w = 960
  const h = 720
  const p = PALETTES[props.variant % PALETTES.length] ?? PALETTES[0]!
  const mode = props.variant % 4

  paintPaper(ctx, w, h, p)
  if (mode === 0) paintContourStudy(ctx, p)
  else if (mode === 1) paintNetworkStudy(ctx, p)
  else if (mode === 2) paintLayerStudy(ctx, p)
  else paintGridStudy(ctx, p)
  paintFrame(ctx, w, h, p)
})

function paintPaper(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  p: (typeof PALETTES)[number],
) {
  const wash = ctx.createLinearGradient(0, 0, w, h)
  wash.addColorStop(0, p.paper)
  wash.addColorStop(0.6, p.soft)
  wash.addColorStop(1, p.paper)
  ctx.fillStyle = wash
  ctx.fillRect(0, 0, w, h)

  ctx.strokeStyle = hexAlpha(p.deep, 0.06)
  ctx.lineWidth = 1
  for (let x = 0; x <= w; x += 48) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h)
    ctx.stroke()
  }
  for (let y = 0; y <= h; y += 48) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }
}

function paintContourStudy(ctx: CanvasRenderingContext2D, p: (typeof PALETTES)[number]) {
  for (let level = 0; level < 20; level += 1) {
    ctx.beginPath()
    for (let step = 0; step <= 200; step += 1) {
      const a = (step / 200) * Math.PI * 2
      const radius = 42 + level * 19 + Math.sin(a * 3 + level * 0.11) * (12 + level * 1.4)
      const x = 470 + Math.cos(a) * radius * 1.18
      const y = 350 + Math.sin(a) * radius * 0.68
      if (!step) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
    ctx.strokeStyle = level % 5 === 0 ? hexAlpha(p.deep, 0.8) : hexAlpha(p.mid, 0.45)
    ctx.lineWidth = level % 5 === 0 ? 1.7 : 1
    ctx.stroke()
  }

  ctx.beginPath()
  ctx.moveTo(110, 600)
  ctx.bezierCurveTo(265, 430, 470, 540, 520, 350)
  ctx.bezierCurveTo(548, 228, 752, 312, 820, 158)
  ctx.strokeStyle = p.accent
  ctx.lineWidth = 5
  ctx.lineCap = 'round'
  ctx.stroke()

  for (const [x, y] of [
    [110, 600],
    [520, 350],
    [820, 158],
  ] as const) {
    ctx.beginPath()
    ctx.arc(x, y, 15, 0, Math.PI * 2)
    ctx.fillStyle = hexAlpha(p.accent, 0.16)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(x, y, 8, 0, Math.PI * 2)
    ctx.fillStyle = p.accent
    ctx.fill()
  }
}

function paintNetworkStudy(ctx: CanvasRenderingContext2D, p: (typeof PALETTES)[number]) {
  const hub: [number, number] = [470, 350]
  const spokes: [number, number][] = [
    [215, 168],
    [700, 145],
    [800, 470],
    [250, 545],
    [430, 105],
    [560, 600],
    [118, 330],
  ]

  ctx.strokeStyle = hexAlpha(p.deep, 0.42)
  ctx.lineWidth = 1.6
  spokes.forEach(([x, y]) => {
    ctx.beginPath()
    ctx.moveTo(hub[0], hub[1])
    ctx.quadraticCurveTo((hub[0] + x) / 2, (hub[1] + y) / 2 - 70, x, y)
    ctx.stroke()
  })

  spokes.forEach(([x, y], index) => {
    ctx.beginPath()
    ctx.arc(x, y, 20 + (index % 3) * 10, 0, Math.PI * 2)
    ctx.fillStyle = hexAlpha(p.deep, 0.09)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(x, y, 5, 0, Math.PI * 2)
    ctx.fillStyle = p.deep
    ctx.fill()
  })

  ctx.beginPath()
  ctx.arc(hub[0], hub[1], 96, 0, Math.PI * 2)
  ctx.fillStyle = hexAlpha(p.deep, 0.12)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(hub[0], hub[1], 52, 0, Math.PI * 2)
  ctx.fillStyle = p.deep
  ctx.fill()
  ctx.beginPath()
  ctx.arc(hub[0], hub[1], 70, 0, Math.PI * 2)
  ctx.strokeStyle = hexAlpha(p.deep, 0.55)
  ctx.lineWidth = 2
  ctx.stroke()
}

function paintLayerStudy(ctx: CanvasRenderingContext2D, p: (typeof PALETTES)[number]) {
  const project = (x: number, z: number, y: number): [number, number] => [
    470 + (x - z) * 52,
    250 + (x + z) * 24 + y,
  ]
  const corners: [number, number][] = [
    [-3, -3],
    [3, -3],
    [3, 3],
    [-3, 3],
  ]
  const tones = [hexAlpha(p.mid, 0.55), hexAlpha(p.deep, 0.85), hexAlpha(p.paper, 0.95)]

  for (let layer = 2; layer >= 0; layer -= 1) {
    ctx.beginPath()
    corners.forEach(([x, z], index) => {
      const [px, py] = project(x, z, layer * 96)
      if (!index) ctx.moveTo(px, py)
      else ctx.lineTo(px, py)
    })
    ctx.closePath()
    ctx.fillStyle = tones[layer] ?? p.mid
    ctx.fill()
    ctx.strokeStyle = hexAlpha(p.deep, 0.6)
    ctx.lineWidth = 1.6
    ctx.stroke()

    ctx.strokeStyle = hexAlpha(p.deep, 0.22)
    ctx.lineWidth = 0.9
    for (let line = -2; line <= 2; line += 1) {
      const [ax, ay] = project(line, -3, layer * 96)
      const [bx, by] = project(line, 3, layer * 96)
      ctx.beginPath()
      ctx.moveTo(ax, ay)
      ctx.lineTo(bx, by)
      ctx.stroke()
      const [cx, cy] = project(-3, line, layer * 96)
      const [dx, dy] = project(3, line, layer * 96)
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(dx, dy)
      ctx.stroke()
    }
  }
}

function paintGridStudy(ctx: CanvasRenderingContext2D, p: (typeof PALETTES)[number]) {
  ctx.save()
  ctx.translate(470, 350)
  ctx.rotate(-0.22)
  ctx.translate(-470, -350)

  for (let row = -1; row < 7; row += 1) {
    for (let col = -1; col < 8; col += 1) {
      const x = col * 150
      const y = row * 132
      ctx.fillStyle = hexAlpha(p.deep, (row + col) % 3 === 0 ? 0.12 : 0.05)
      ctx.fillRect(x + 12, y + 12, 122, 104)
      ctx.strokeStyle = hexAlpha(p.deep, 0.2)
      ctx.lineWidth = 1
      ctx.strokeRect(x + 12, y + 12, 122, 104)
      ctx.fillStyle = hexAlpha(p.mid, 0.4)
      ctx.fillRect(x + 30, y + 32, 58, 50)
    }
  }

  ctx.fillStyle = p.deep
  ctx.fillRect(312, 276, 150, 132)
  ctx.fillStyle = p.paper
  ctx.fillRect(342, 306, 78, 68)
  ctx.restore()
}

function paintFrame(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  p: (typeof PALETTES)[number],
) {
  ctx.strokeStyle = hexAlpha(p.deep, 0.18)
  ctx.lineWidth = 2
  ctx.strokeRect(24, 24, w - 48, h - 48)
  ctx.fillStyle = p.deep
  ctx.fillRect(24, 24, 72, 5)
}

function hexAlpha(hex: string, alpha: number): string {
  const value = hex.replace('#', '')
  const r = parseInt(value.slice(0, 2), 16)
  const g = parseInt(value.slice(2, 4), 16)
  const b = parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
</script>

<template>
  <canvas ref="canvas" width="960" height="720" class="project-cover" aria-hidden="true" />
</template>

<style scoped>
.project-cover {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
