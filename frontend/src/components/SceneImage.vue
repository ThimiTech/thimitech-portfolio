<script setup lang="ts">
/**
 * Generated scene imagery for the Services and Mission cards.
 *
 * Every panel is painted at runtime from deterministic noise: shaded relief terrain,
 * satellite land cover, street basemaps, earth-from-orbit and product screenshots.
 * Original artwork, no binary assets, identical on every load, and rendered at 2×
 * so it stays crisp on high-density screens.
 */
defineOptions({ name: 'SceneImage' })

import { onMounted, ref, watch } from 'vue'
import { fbm, makeValueNoise, mulberry32, ridged } from '../data/noise'

export type SceneKind =
  | 'terrain'
  | 'satellite'
  | 'city'
  | 'orbit'
  | 'dashboard'
  | 'field'
  | 'analytics'

const props = defineProps<{ scene: SceneKind; seed?: number }>()

const canvas = ref<HTMLCanvasElement | null>(null)

const W = 800
const H = 500
const NAVY = '#12456f'
const NAVY_DEEP = '#0b2b4a'
const INK = '#0a0a0a'

type Painter = (ctx: CanvasRenderingContext2D, seed: number) => void

onMounted(paint)
watch(
  () => [props.scene, props.seed],
  () => paint(),
)

function paint() {
  const element = canvas.value
  if (!element) return
  const ctx = element.getContext('2d')
  if (!ctx) return

  const ratio = Math.min(2, Math.max(1, Math.round(window.devicePixelRatio || 1)))
  element.width = W * ratio
  element.height = H * ratio
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  ctx.clearRect(0, 0, W, H)

  const painter = PAINTERS[props.scene] ?? PAINTERS.terrain
  painter(ctx, (props.seed ?? 1) * 7919 + 13)
}

/* ── Shared helpers ───────────────────────────────────────────────────────── */

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const radius = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + w - radius, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius)
  ctx.lineTo(x + w, y + h - radius)
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h)
  ctx.lineTo(x + radius, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
  ctx.closePath()
}

function softShadow(ctx: CanvasRenderingContext2D, blur: number, alpha = 0.18) {
  ctx.shadowColor = `rgba(9, 22, 36, ${alpha})`
  ctx.shadowBlur = blur
  ctx.shadowOffsetY = blur * 0.35
}

function clearShadow(ctx: CanvasRenderingContext2D) {
  ctx.shadowColor = 'transparent'
  ctx.shadowBlur = 0
  ctx.shadowOffsetY = 0
}

function grain(ctx: CanvasRenderingContext2D, seed: number, alpha: number) {
  const random = mulberry32(seed * 977 + 5)
  for (let i = 0; i < 2200; i += 1) {
    const x = random() * W
    const y = random() * H
    ctx.fillStyle =
      random() > 0.5 ? `rgba(255, 255, 255, ${alpha})` : `rgba(8, 18, 30, ${alpha})`
    ctx.fillRect(x, y, 1, 1)
  }
}

function vignette(ctx: CanvasRenderingContext2D, alpha = 0.3) {
  const gradient = ctx.createRadialGradient(W * 0.5, H * 0.48, H * 0.32, W * 0.5, H * 0.5, H * 0.92)
  gradient.addColorStop(0, 'rgba(6, 17, 29, 0)')
  gradient.addColorStop(1, `rgba(6, 17, 29, ${alpha})`)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, W, H)
}

/** Terrain height grid (ridged multifractal, edges pulled down into valleys). */
function heightGrid(seed: number, gw: number, gh: number) {
  const noise = makeValueNoise(seed)
  const heights = new Float32Array(gw * gh)
  let min = Infinity
  let max = -Infinity

  for (let y = 0; y < gh; y += 1) {
    for (let x = 0; x < gw; x += 1) {
      const h = ridged(noise, (x / gw) * 5.5, (y / gh) * 5.5, 6)
      const edge = Math.min(1, Math.min(x, gw - 1 - x) / 24, Math.min(y, gh - 1 - y) / 24)
      const value = h * (0.5 + 0.5 * edge)
      heights[y * gw + x] = value
      if (value < min) min = value
      if (value > max) max = value
    }
  }

  const span = Math.max(1e-6, max - min)
  for (let i = 0; i < heights.length; i += 1) {
    // Gamma pushes the mass of the terrain down, so valleys stay grey and only
    // the summits reach the snow stops of the ramp.
    heights[i] = Math.pow((heights[i]! - min) / span, 1.35)
  }
  return heights
}

function mix(a: number[], b: number[], t: number): [number, number, number] {
  const a0 = a[0] ?? 0
  const a1 = a[1] ?? 0
  const a2 = a[2] ?? 0
  const b0 = b[0] ?? a0
  const b1 = b[1] ?? a1
  const b2 = b[2] ?? a2
  return [
    Math.round(a0 + (b0 - a0) * t),
    Math.round(a1 + (b1 - a1) * t),
    Math.round(a2 + (b2 - a2) * t),
  ]
}

const RAMP: number[][] = [
  [9, 30, 52],
  [22, 58, 92],
  [52, 88, 118],
  [96, 116, 132],
  [140, 156, 168],
  [186, 198, 208],
  [226, 234, 240],
  [255, 255, 255],
]

function rampColor(t: number): [number, number, number] {
  const clamped = Math.min(0.999, Math.max(0, t)) * (RAMP.length - 1)
  const index = Math.floor(clamped)
  const lower = RAMP[index] ?? [10, 34, 58]
  const upper = RAMP[index + 1] ?? lower
  return mix(lower, upper, clamped - index)
}

/** Paints hill-shaded relief, optionally with contour lines, rivers and roads. */
function paintRelief(
  ctx: CanvasRenderingContext2D,
  seed: number,
  options: { detail?: boolean; contours?: boolean; contoursOnly?: boolean } = {},
) {
  const { detail = true, contours = true } = options
  const GW = 200
  const GH = 125
  const heights = heightGrid(seed, GW, GH)

  const small = document.createElement('canvas')
  small.width = GW
  small.height = GH
  const smallCtx = small.getContext('2d')
  if (!smallCtx) return
  const image = smallCtx.createImageData(GW, GH)

  const azimuth = (315 * Math.PI) / 180
  const altitude = (42 * Math.PI) / 180
  const lx = Math.cos(altitude) * Math.sin(azimuth)
  const ly = Math.cos(altitude) * Math.cos(azimuth)
  const lz = Math.sin(altitude)

  for (let y = 0; y < GH; y += 1) {
    for (let x = 0; x < GW; x += 1) {
      const index = y * GW + x
      const h = heights[index]!
      const hx =
        heights[y * GW + Math.min(GW - 1, x + 1)]! - heights[y * GW + Math.max(0, x - 1)]!
      const hy =
        heights[Math.min(GH - 1, y + 1) * GW + x]! - heights[Math.max(0, y - 1) * GW + x]!
      const nx = -hx * 5.5
      const ny = -hy * 5.5
      const length = Math.hypot(nx, ny, 1)
      const shade = Math.max(0, (nx * lx + ny * ly + lz) / length)
      const [r, g, b] = rampColor(h)
      const k = 0.34 + 0.92 * shade
      const out = index * 4
      image.data[out] = Math.min(255, r * k)
      image.data[out + 1] = Math.min(255, g * k)
      image.data[out + 2] = Math.min(255, b * k)
      image.data[out + 3] = 255
    }
  }

  smallCtx.putImageData(image, 0, 0)
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(small, 0, 0, W, H)

  if (contours) {
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'
    ctx.lineWidth = 1
    const sx = W / GW
    const sy = H / GH
    for (let level = 0.08; level < 0.98; level += 0.075) {
      ctx.beginPath()
      for (let y = 0; y < GH - 1; y += 1) {
        for (let x = 0; x < GW - 1; x += 1) {
          const a = heights[y * GW + x]!
          const b = heights[y * GW + x + 1]!
          const c = heights[(y + 1) * GW + x + 1]!
          const d = heights[(y + 1) * GW + x]!
          const points: [number, number][] = []
          if ((a - level) * (b - level) < 0) {
            points.push([(x + (level - a) / (b - a)) * sx, y * sy])
          }
          if ((b - level) * (c - level) < 0) {
            points.push([(x + 1) * sx, (y + (level - b) / (c - b)) * sy])
          }
          if ((c - level) * (d - level) < 0) {
            points.push([((x + 1) + (level - c) / (d - c)) * sx, (y + 1) * sy])
          }
          if ((d - level) * (a - level) < 0) {
            points.push([x * sx, ((y + 1) + (level - d) / (a - d)) * sy])
          }
          if (points.length === 2) {
            ctx.moveTo(points[0]![0], points[0]![1])
            ctx.lineTo(points[1]![0], points[1]![1])
          } else if (points.length === 4) {
            ctx.moveTo(points[0]![0], points[0]![1])
            ctx.lineTo(points[1]![0], points[1]![1])
            ctx.moveTo(points[2]![0], points[2]![1])
            ctx.lineTo(points[3]![0], points[3]![1])
          }
        }
      }
      ctx.stroke()
    }
  }

  if (!detail) return

  // Rivers follow the low ground.
  const random = mulberry32(seed + 31)
  ctx.lineCap = 'round'
  for (let i = 0; i < 2; i += 1) {
    const startY = H * (0.5 + random() * 0.42)
    ctx.beginPath()
    ctx.moveTo(-30, startY)
    let y = startY
    for (let x = -30; x <= W + 30; x += 46) {
      y += (random() - 0.5) * 54
      ctx.quadraticCurveTo(x + 23, y + (random() - 0.5) * 26, x + 46, y)
    }
    ctx.strokeStyle = 'rgba(10, 34, 58, 0.5)'
    ctx.lineWidth = 3.4 - i
    ctx.stroke()
    ctx.strokeStyle = 'rgba(214, 234, 250, 0.4)'
    ctx.lineWidth = 1.1
    ctx.stroke()
  }

  // A road crossing the valley.
  ctx.beginPath()
  ctx.moveTo(-20, H * 0.82)
  ctx.bezierCurveTo(W * 0.3, H * 0.66, W * 0.6, H * 0.9, W + 20, H * 0.7)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)'
  ctx.lineWidth = 3.4
  ctx.stroke()
  ctx.strokeStyle = 'rgba(12, 28, 46, 0.5)'
  ctx.lineWidth = 1
  ctx.setLineDash([7, 7])
  ctx.stroke()
  ctx.setLineDash([])

  grain(ctx, seed, 0.05)
  vignette(ctx, 0.32)
}

/* ── Painters ─────────────────────────────────────────────────────────────── */

const PAINTERS: Record<SceneKind, Painter> = {
  terrain(ctx, seed) {
    paintRelief(ctx, seed)
  },

  satellite(ctx, seed) {
    const noise = makeValueNoise(seed)
    const GW = 160
    const GH = 100
    const small = document.createElement('canvas')
    small.width = GW
    small.height = GH
    const smallCtx = small.getContext('2d')
    if (!smallCtx) return
    const image = smallCtx.createImageData(GW, GH)

    for (let y = 0; y < GH; y += 1) {
      for (let x = 0; x < GW; x += 1) {
        const n = fbm(noise, (x / GW) * 4.5, (y / GH) * 4.5, 4)
        const band = Math.round(n * 6) / 6
        const value = 70 + band * 130
        const out = (y * GW + x) * 4
        image.data[out] = value * 1.02
        image.data[out + 1] = value
        image.data[out + 2] = value * 0.96
        image.data[out + 3] = 255
      }
    }
    smallCtx.putImageData(image, 0, 0)
    ctx.imageSmoothingEnabled = true
    ctx.drawImage(small, 0, 0, W, H)

    // Agricultural parcels.
    const random = mulberry32(seed + 17)
    for (let row = 0; row < 10; row += 1) {
      for (let col = 0; col < 15; col += 1) {
        const w = 30 + random() * 24
        const h = 24 + random() * 18
        const x = col * 56 + random() * 18 - 10
        const y = row * 52 + random() * 14 - 8
        const shade = 120 + random() * 110
        ctx.fillStyle = `rgba(${shade}, ${shade + 4}, ${shade - 4}, 0.45)`
        ctx.fillRect(x, y, w, h)
        ctx.strokeStyle = 'rgba(24, 38, 52, 0.18)'
        ctx.lineWidth = 1
        ctx.strokeRect(x, y, w, h)
      }
    }

    // River and lake.
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(-20, H * 0.3)
    let y = H * 0.3
    for (let x = -20; x <= W + 20; x += 54) {
      y += (random() - 0.45) * 46
      ctx.quadraticCurveTo(x + 27, y + (random() - 0.5) * 22, x + 54, y)
    }
    ctx.strokeStyle = 'rgba(18, 69, 111, 0.92)'
    ctx.lineWidth = 7
    ctx.stroke()

    ctx.beginPath()
    ctx.ellipse(W * 0.74, H * 0.7, 54, 30, -0.3, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(18, 69, 111, 0.85)'
    ctx.fill()

    // Roads.
    for (const offset of [0, 1]) {
      ctx.beginPath()
      ctx.moveTo(-10, H * (0.62 + offset * 0.16))
      ctx.lineTo(W + 10, H * (0.5 + offset * 0.16))
      ctx.strokeStyle = 'rgba(250, 250, 250, 0.55)'
      ctx.lineWidth = 2.6 - offset
      ctx.stroke()
    }

    // Settlement cluster.
    for (let i = 0; i < 70; i += 1) {
      const x = W * 0.5 + (random() - 0.5) * 190
      const y = H * 0.42 + (random() - 0.5) * 130
      ctx.fillStyle = `rgba(248, 248, 248, ${0.35 + random() * 0.4})`
      ctx.fillRect(x, y, 4 + random() * 6, 4 + random() * 5)
    }

    grain(ctx, seed, 0.045)
    vignette(ctx, 0.26)
  },

  city(ctx, seed) {
    const random = mulberry32(seed + 3)
    ctx.fillStyle = '#eef0f2'
    ctx.fillRect(0, 0, W, H)

    // River across one corner.
    ctx.beginPath()
    ctx.moveTo(-20, H * 0.72)
    ctx.bezierCurveTo(W * 0.24, H * 0.6, W * 0.38, H * 1.02, W * 0.74, H * 0.86)
    ctx.bezierCurveTo(W * 0.86, H * 0.8, W * 0.94, H * 0.98, W + 20, H * 0.94)
    ctx.lineTo(W + 20, H + 20)
    ctx.lineTo(-20, H + 20)
    ctx.closePath()
    const water = ctx.createLinearGradient(0, H * 0.65, W, H)
    water.addColorStop(0, '#12456f')
    water.addColorStop(1, '#0b2b4a')
    ctx.fillStyle = water
    ctx.fill()

    // Parks.
    for (const [x, y, w, h] of [
      [70, 78, 132, 96],
      [452, 62, 108, 118],
      [268, 268, 148, 86],
    ] as const) {
      roundRect(ctx, x, y, w, h, 16)
      ctx.fillStyle = '#d3dde2'
      ctx.fill()
    }

    // Street grid with casings.
    const drawGrid = (casing: string, fill: string, casingWidth: number, width: number) => {
      ctx.strokeStyle = casing
      ctx.lineWidth = casingWidth
      for (let x = 34; x < W; x += 64) {
        ctx.beginPath()
        ctx.moveTo(x, -10)
        ctx.lineTo(x, H + 10)
        ctx.stroke()
      }
      for (let y = 30; y < H; y += 54) {
        ctx.beginPath()
        ctx.moveTo(-10, y)
        ctx.lineTo(W + 10, y)
        ctx.stroke()
      }
      ctx.strokeStyle = fill
      ctx.lineWidth = width
      for (let x = 34; x < W; x += 64) {
        ctx.beginPath()
        ctx.moveTo(x, -10)
        ctx.lineTo(x, H + 10)
        ctx.stroke()
      }
      for (let y = 30; y < H; y += 54) {
        ctx.beginPath()
        ctx.moveTo(-10, y)
        ctx.lineTo(W + 10, y)
        ctx.stroke()
      }
    }
    drawGrid('#d6dadd', '#ffffff', 9, 6)

    // Avenues and a ring road.
    ctx.strokeStyle = '#dfe3e6'
    ctx.lineWidth = 15
    ctx.beginPath()
    ctx.moveTo(-20, 40)
    ctx.lineTo(W + 20, H * 0.62)
    ctx.stroke()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 11
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(W * 0.52, H * 0.42, 168, -0.4, 2.7)
    ctx.strokeStyle = '#dfe3e6'
    ctx.lineWidth = 13
    ctx.stroke()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 9
    ctx.stroke()

    // Blocks.
    for (let i = 0; i < 260; i += 1) {
      const x = random() * W
      const y = random() * H * 0.86
      const w = 14 + random() * 26
      const h = 12 + random() * 22
      ctx.fillStyle = `rgba(122, 134, 146, ${0.1 + random() * 0.16})`
      ctx.fillRect(x, y, w, h)
    }

    // Landmarks.
    for (const [x, y] of [
      [318, 168],
      [560, 300],
      [166, 344],
    ] as const) {
      ctx.beginPath()
      ctx.arc(x, y, 9, 0, Math.PI * 2)
      ctx.fillStyle = NAVY
      ctx.fill()
      ctx.beginPath()
      ctx.arc(x, y, 15, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(18, 69, 111, 0.35)'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    vignette(ctx, 0.16)
  },

  orbit(ctx, seed) {
    const random = mulberry32(seed + 11)
    const sky = ctx.createLinearGradient(0, 0, 0, H)
    sky.addColorStop(0, '#04070b')
    sky.addColorStop(1, '#081420')
    ctx.fillStyle = sky
    ctx.fillRect(0, 0, W, H)

    for (let i = 0; i < 520; i += 1) {
      const x = random() * W
      const y = random() * H * 0.62
      const r = random() * 1.5
      ctx.fillStyle = `rgba(255, 255, 255, ${0.18 + random() * 0.7})`
      ctx.beginPath()
      ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fill()
    }

    // Earth limb.
    const cx = W * 0.5
    const cy = H * 2.4
    const radius = H * 1.96
    const planet = ctx.createRadialGradient(cx, cy - radius * 0.9, radius * 0.7, cx, cy, radius)
    planet.addColorStop(0, '#8ec2e4')
    planet.addColorStop(0.28, '#2b6f9f')
    planet.addColorStop(0.62, '#12456f')
    planet.addColorStop(1, '#061726')
    ctx.beginPath()
    ctx.arc(cx, cy, radius, 0, Math.PI * 2)
    ctx.fillStyle = planet
    ctx.fill()

    ctx.save()
    ctx.beginPath()
    ctx.arc(cx, cy, radius, 0, Math.PI * 2)
    ctx.clip()
    // Cloud systems.
    for (let i = 0; i < 46; i += 1) {
      const bx = cx + (random() - 0.5) * radius * 1.5
      const by = cy - radius * (0.82 + random() * 0.12)
      const br = 40 + random() * 130
      const cloud = ctx.createRadialGradient(bx, by, 0, bx, by, br)
      cloud.addColorStop(0, `rgba(255, 255, 255, ${0.1 + random() * 0.22})`)
      cloud.addColorStop(1, 'rgba(255, 255, 255, 0)')
      ctx.fillStyle = cloud
      ctx.fillRect(bx - br, by - br, br * 2, br * 2)
    }
    // Landmass hints.
    for (let i = 0; i < 16; i += 1) {
      const bx = cx + (random() - 0.5) * radius * 1.35
      const by = cy - radius * (0.8 + random() * 0.14)
      const br = 50 + random() * 120
      const land = ctx.createRadialGradient(bx, by, 0, bx, by, br)
      land.addColorStop(0, 'rgba(90, 122, 96, 0.32)')
      land.addColorStop(1, 'rgba(90, 122, 96, 0)')
      ctx.fillStyle = land
      ctx.fillRect(bx - br, by - br, br * 2, br * 2)
    }
    ctx.restore()

    // Atmosphere.
    ctx.save()
    ctx.globalAlpha = 0.55
    ctx.shadowColor = '#9ad3f7'
    ctx.shadowBlur = 30
    ctx.strokeStyle = 'rgba(186, 226, 250, 0.95)'
    ctx.lineWidth = 5
    ctx.beginPath()
    ctx.arc(cx, cy, radius, Math.PI * 1.02, Math.PI * 1.98)
    ctx.stroke()
    ctx.restore()

    // Satellite with an orbit trail.
    ctx.strokeStyle = 'rgba(180, 214, 240, 0.5)'
    ctx.lineWidth = 1.4
    ctx.setLineDash([9, 8])
    ctx.beginPath()
    ctx.moveTo(-30, H * 0.42)
    ctx.bezierCurveTo(W * 0.3, H * 0.14, W * 0.7, H * 0.34, W + 30, H * 0.08)
    ctx.stroke()
    ctx.setLineDash([])

    const sx = W * 0.66
    const sy = H * 0.24
    ctx.save()
    softShadow(ctx, 18, 0.5)
    ctx.fillStyle = '#e8ecf0'
    roundRect(ctx, sx - 13, sy - 9, 26, 18, 4)
    ctx.fill()
    ctx.fillStyle = '#9fb6c8'
    roundRect(ctx, sx - 46, sy - 7, 30, 14, 3)
    ctx.fill()
    roundRect(ctx, sx + 16, sy - 7, 30, 14, 3)
    ctx.fill()
    clearShadow(ctx)
    ctx.restore()
    ctx.beginPath()
    ctx.arc(sx, sy + 20, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#7fd8ff'
    ctx.fill()

    vignette(ctx, 0.3)
  },

  dashboard(ctx, seed) {
    const random = mulberry32(seed + 23)
    ctx.fillStyle = '#e9ecef'
    ctx.fillRect(0, 0, W, H)

    ctx.save()
    softShadow(ctx, 26, 0.22)
    roundRect(ctx, 36, 26, 728, 448, 16)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.restore()

    // Browser chrome.
    ctx.fillStyle = '#f3f5f6'
    roundRect(ctx, 36, 26, 728, 42, 16)
    ctx.fill()
    ctx.fillRect(36, 52, 728, 16)
    for (let i = 0; i < 3; i += 1) {
      ctx.beginPath()
      ctx.arc(60 + i * 16, 47, 4.4, 0, Math.PI * 2)
      ctx.fillStyle = i === 0 ? NAVY : '#c9ced3'
      ctx.fill()
    }
    roundRect(ctx, 118, 38, 470, 18, 9)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.fillStyle = '#8e959b'
    ctx.font = '500 11px "IBM Plex Mono", monospace'
    ctx.fillText('app.thimitech.com/portal', 132, 51)

    // Sidebar.
    ctx.fillStyle = NAVY_DEEP
    ctx.beginPath()
    ctx.moveTo(36, 68)
    ctx.lineTo(186, 68)
    ctx.lineTo(186, 474)
    ctx.lineTo(52, 474)
    ctx.quadraticCurveTo(36, 474, 36, 458)
    ctx.closePath()
    ctx.fill()
    ctx.fillStyle = 'rgba(255, 255, 255, 0.92)'
    ctx.font = '600 13px "Outfit Variable", sans-serif'
    ctx.fillText('Thimi Tech OS', 58, 98)
    const rows = [128, 158, 188, 218, 248, 278]
    rows.forEach((y, index) => {
      roundRect(ctx, 52, y, 118, 20, 6)
      ctx.fillStyle = index === 1 ? 'rgba(255, 255, 255, 0.22)' : 'rgba(255, 255, 255, 0.08)'
      ctx.fill()
      ctx.fillStyle = 'rgba(255, 255, 255, 0.62)'
      ctx.fillRect(62, y + 8, 52 + (index % 3) * 16, 4)
    })

    // Header.
    ctx.fillStyle = INK
    ctx.font = '600 19px "Outfit Variable", sans-serif'
    ctx.fillText('District overview', 210, 104)
    ctx.fillStyle = '#8e959b'
    ctx.font = '400 12px "IBM Plex Mono", monospace'
    ctx.fillText('Bagmati Province · 77 districts', 210, 124)

    // KPI tiles.
    const kpis = [
      { label: 'Districts mapped', value: '77', trend: [8, 14, 11, 18, 16, 24] },
      { label: 'Datasets live', value: '312', trend: [12, 10, 16, 14, 20, 26] },
      { label: 'Field records', value: '48.2k', trend: [6, 12, 18, 15, 22, 28] },
    ]
    kpis.forEach((kpi, index) => {
      const x = 210 + index * 176
      roundRect(ctx, x, 140, 160, 78, 10)
      ctx.fillStyle = '#f5f6f7'
      ctx.fill()
      ctx.fillStyle = '#8e959b'
      ctx.font = '500 10px "IBM Plex Mono", monospace'
      ctx.fillText(kpi.label.toUpperCase(), x + 14, 160)
      ctx.fillStyle = INK
      ctx.font = '600 24px "Outfit Variable", sans-serif'
      ctx.fillText(kpi.value, x + 14, 188)
      ctx.beginPath()
      kpi.trend.forEach((value, i) => {
        const px = x + 92 + i * 10
        const py = 200 - value * 1.6
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      })
      ctx.strokeStyle = NAVY
      ctx.lineWidth = 2
      ctx.stroke()
    })

    // Chart card.
    roundRect(ctx, 210, 236, 336, 216, 10)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.strokeStyle = '#e3e7ea'
    ctx.lineWidth = 1
    ctx.stroke()
    ctx.fillStyle = '#8e959b'
    ctx.font = '500 10px "IBM Plex Mono", monospace'
    ctx.fillText('RECORDS BY MONTH', 226, 258)
    for (let i = 0; i < 4; i += 1) {
      ctx.beginPath()
      ctx.moveTo(226, 286 + i * 38)
      ctx.lineTo(530, 286 + i * 38)
      ctx.strokeStyle = '#eef1f3'
      ctx.stroke()
    }
    const bars = [42, 68, 54, 82, 63, 95, 74, 110]
    bars.forEach((height, index) => {
      const x = 234 + index * 38
      roundRect(ctx, x, 434 - height, 20, height, 4)
      ctx.fillStyle = index === 7 ? NAVY : '#dbe0e4'
      ctx.fill()
    })

    // Map inset.
    roundRect(ctx, 562, 236, 186, 216, 10)
    ctx.fillStyle = '#eef1f3'
    ctx.fill()
    ctx.save()
    roundRect(ctx, 562, 236, 186, 216, 10)
    ctx.clip()
    ctx.fillStyle = '#dfe5e9'
    ctx.beginPath()
    ctx.moveTo(552, 300)
    ctx.bezierCurveTo(610, 268, 660, 330, 760, 292)
    ctx.lineTo(760, 460)
    ctx.lineTo(552, 460)
    ctx.closePath()
    ctx.fill()
    for (let i = 0; i < 5; i += 1) {
      const px = 590 + random() * 130
      const py = 270 + random() * 150
      ctx.beginPath()
      ctx.arc(px, py, 5, 0, Math.PI * 2)
      ctx.fillStyle = NAVY
      ctx.fill()
      ctx.beginPath()
      ctx.arc(px, py, 11, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(18, 69, 111, 0.3)'
      ctx.lineWidth = 1.6
      ctx.stroke()
    }
    ctx.restore()
    ctx.fillStyle = '#8e959b'
    ctx.font = '500 10px "IBM Plex Mono", monospace'
    ctx.fillText('LIVE MAP', 578, 258)

    vignette(ctx, 0.14)
  },

  field(ctx, seed) {
    ctx.save()
    ctx.filter = 'blur(7px)'
    paintRelief(ctx, seed + 5, { contours: true, detail: false })
    ctx.restore()
    ctx.fillStyle = 'rgba(6, 17, 29, 0.34)'
    ctx.fillRect(0, 0, W, H)

    // Phone.
    ctx.save()
    softShadow(ctx, 30, 0.4)
    roundRect(ctx, 276, 22, 248, 456, 30)
    ctx.fillStyle = '#0f1216'
    ctx.fill()
    ctx.restore()
    roundRect(ctx, 288, 38, 224, 424, 20)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
    ctx.fillStyle = '#0f1216'
    roundRect(ctx, 366, 46, 68, 8, 4)
    ctx.fill()

    // Mini map inside the app.
    ctx.save()
    roundRect(ctx, 298, 66, 204, 168, 12)
    ctx.clip()
    ctx.save()
    ctx.filter = 'blur(1.6px)'
    ctx.translate(298, 66)
    ctx.scale(0.255, 0.336)
    paintRelief(ctx, seed + 9, { contours: false, detail: false })
    ctx.restore()
    ctx.fillStyle = 'rgba(18, 69, 111, 0.22)'
    ctx.beginPath()
    ctx.moveTo(322, 200)
    ctx.lineTo(376, 132)
    ctx.lineTo(452, 146)
    ctx.lineTo(478, 210)
    ctx.closePath()
    ctx.fill()
    ctx.strokeStyle = NAVY
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(400, 158, 22, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(18, 69, 111, 0.18)'
    ctx.fill()
    ctx.beginPath()
    ctx.arc(400, 158, 6.5, 0, Math.PI * 2)
    ctx.fillStyle = NAVY
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.restore()
    roundRect(ctx, 298, 66, 204, 168, 12)
    ctx.strokeStyle = '#e3e7ea'
    ctx.lineWidth = 1
    ctx.stroke()

    // Form rows.
    const rows = [
      { label: 'PARCEL ID', value: 'BGT-04-1187' },
      { label: 'LAND USE', value: 'Irrigated agriculture' },
      { label: 'OWNER', value: 'Recorded at ward office' },
      { label: 'AREA', value: '0.62 ha' },
    ]
    rows.forEach((row, index) => {
      const y = 254 + index * 44
      ctx.fillStyle = '#8e959b'
      ctx.font = '500 9px "IBM Plex Mono", monospace'
      ctx.fillText(row.label, 302, y)
      roundRect(ctx, 298, y + 8, 204, 26, 6)
      ctx.fillStyle = '#f5f6f7'
      ctx.fill()
      ctx.fillStyle = INK
      ctx.font = '400 12px "Outfit Variable", sans-serif'
      ctx.fillText(row.value, 308, y + 25)
    })

    roundRect(ctx, 298, 434, 204, 20, 10)
    ctx.fillStyle = '#e9ecef'
    ctx.fill()
    ctx.fillStyle = NAVY
    roundRect(ctx, 298, 434, 128, 20, 10)
    ctx.fill()
    ctx.fillStyle = '#ffffff'
    ctx.font = '500 10px "IBM Plex Mono", monospace'
    ctx.fillText('SYNCED · 12 RECORDS', 312, 448)

    // Floating status chips.
    ctx.save()
    softShadow(ctx, 16, 0.3)
    roundRect(ctx, 578, 70, 168, 44, 12)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.96)'
    ctx.fill()
    clearShadow(ctx)
    ctx.restore()
    ctx.fillStyle = NAVY
    ctx.font = '600 15px "Outfit Variable", sans-serif'
    ctx.fillText('± 3 m', 596, 98)
    ctx.fillStyle = '#8e959b'
    ctx.font = '500 10px "IBM Plex Mono", monospace'
    ctx.fillText('GPS ACCURACY', 656, 97)

    ctx.save()
    softShadow(ctx, 16, 0.3)
    roundRect(ctx, 578, 128, 168, 44, 12)
    ctx.fillStyle = 'rgba(18, 69, 111, 0.94)'
    ctx.fill()
    clearShadow(ctx)
    ctx.restore()
    ctx.fillStyle = '#ffffff'
    ctx.font = '600 14px "Outfit Variable", sans-serif'
    ctx.fillText('Works offline', 596, 156)

    ctx.fillStyle = 'rgba(255, 255, 255, 0.82)'
    ctx.font = '500 11px "IBM Plex Mono", monospace'
    ctx.fillText('SURVEY · WARD 04', 578, 210)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)'
    ctx.fillText('Captured 11:42 · 14 photos', 578, 230)

    vignette(ctx, 0.34)
  },

  analytics(ctx, seed) {
    const random = mulberry32(seed + 41)
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, W, H)

    ctx.strokeStyle = '#eef1f3'
    ctx.lineWidth = 1
    for (let x = 60; x < W - 40; x += 56) {
      ctx.beginPath()
      ctx.moveTo(x, 60)
      ctx.lineTo(x, 330)
      ctx.stroke()
    }
    for (let y = 60; y <= 330; y += 54) {
      ctx.beginPath()
      ctx.moveTo(48, y)
      ctx.lineTo(W - 40, y)
      ctx.stroke()
    }

    // Area chart.
    const points: [number, number][] = []
    for (let i = 0; i <= 12; i += 1) {
      const x = 60 + i * 56
      const y = 300 - (40 + Math.sin(i * 0.85) * 34 + i * 14 + (random() - 0.5) * 16)
      points.push([x, y])
    }
    ctx.beginPath()
    points.forEach(([x, y], index) => (index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)))
    ctx.lineTo(points[points.length - 1]![0], 330)
    ctx.lineTo(points[0]![0], 330)
    ctx.closePath()
    const area = ctx.createLinearGradient(0, 120, 0, 330)
    area.addColorStop(0, 'rgba(18, 69, 111, 0.34)')
    area.addColorStop(1, 'rgba(18, 69, 111, 0.02)')
    ctx.fillStyle = area
    ctx.fill()

    ctx.beginPath()
    points.forEach(([x, y], index) => (index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)))
    ctx.strokeStyle = NAVY
    ctx.lineWidth = 2.6
    ctx.stroke()

    points.forEach(([x, y], index) => {
      if (index % 2 !== 0) return
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      ctx.fillStyle = '#ffffff'
      ctx.fill()
      ctx.strokeStyle = NAVY
      ctx.lineWidth = 2
      ctx.stroke()
    })

    ctx.fillStyle = INK
    ctx.font = '600 17px "Outfit Variable", sans-serif'
    ctx.fillText('Land-use change, 2019 – 2026', 48, 40)
    ctx.fillStyle = '#8e959b'
    ctx.font = '400 11px "IBM Plex Mono", monospace'
    ctx.fillText('HECTARES CLASSIFIED · 12 QUARTERS', 48, 56)

    // KPI tiles.
    const tiles = [
      { label: 'Parcels', value: '48,210' },
      { label: 'Accuracy', value: '96.4%' },
      { label: 'Reports', value: '132' },
    ]
    tiles.forEach((tile, index) => {
      const x = 48 + index * 178
      roundRect(ctx, x, 356, 160, 74, 10)
      ctx.fillStyle = '#f5f6f7'
      ctx.fill()
      ctx.fillStyle = '#8e959b'
      ctx.font = '500 9px "IBM Plex Mono", monospace'
      ctx.fillText(tile.label.toUpperCase(), x + 14, 376)
      ctx.fillStyle = INK
      ctx.font = '600 22px "Outfit Variable", sans-serif'
      ctx.fillText(tile.value, x + 14, 404)
    })

    // Donut + legend.
    const cx = 636
    const cy = 396
    ctx.beginPath()
    ctx.arc(cx, cy, 34, 0, Math.PI * 2)
    ctx.strokeStyle = '#e3e7ea'
    ctx.lineWidth = 14
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(cx, cy, 34, -Math.PI / 2, Math.PI * 0.35)
    ctx.strokeStyle = NAVY
    ctx.lineWidth = 14
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(cx, cy, 34, Math.PI * 0.35, Math.PI * 0.9)
    ctx.strokeStyle = '#8e959b'
    ctx.lineWidth = 14
    ctx.stroke()
    ctx.fillStyle = INK
    ctx.font = '600 13px "Outfit Variable", sans-serif'
    ctx.fillText('Land cover', cx + 58, cy - 12)
    ctx.fillStyle = '#8e959b'
    ctx.font = '400 11px "IBM Plex Mono", monospace'
    ctx.fillText('Forest 42%', cx + 58, cy + 6)
    ctx.fillText('Cropland 31%', cx + 58, cy + 24)
    ctx.fillText('Built-up 12%', cx + 58, cy + 42)

    vignette(ctx, 0.12)
  },
}
</script>

<template>
  <canvas ref="canvas" class="scene-image" width="800" height="500" aria-hidden="true" />
</template>

<style scoped>
.scene-image {
  display: block;
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 10;
  border-bottom: 1px solid rgb(10 10 10 / 0.1);
  background: #eef0f2;
}
</style>
