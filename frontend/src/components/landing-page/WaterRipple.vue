<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'

interface WaterRippleProps {
  deepColor?: string
  midColor?: string
  crestColor?: string
  glowColor?: string
  quality?: 'auto' | 'high' | 'low'
}

interface Ripple {
  x: number
  y: number
  birth: number
  strength: number
  expand: number
  fade: number
  life: number
}

interface Tier {
  maxRipples: number
  dprCap: number
  octaves: number
  rings: number
  mediump: boolean
  caustics: boolean
  grain: boolean
  targetFps: number
  idleFps: number
  maxDimension: number
}

const HIGH_TIER: Tier = {
  maxRipples: 12,
  dprCap: 1.5,
  octaves: 4,
  rings: 3,
  mediump: false,
  caustics: true,
  grain: true,
  targetFps: 60,
  idleFps: 24,
  maxDimension: 1800,
}

const LOW_TIER: Tier = {
  maxRipples: 8,
  dprCap: 1.1,
  octaves: 3,
  rings: 2,
  mediump: true,
  caustics: false,
  grain: false,
  targetFps: 30,
  idleFps: 18,
  maxDimension: 1280,
}

const props = withDefaults(defineProps<WaterRippleProps>(), {
  deepColor: '#f3f6f5',
  midColor: '#12726f',
  crestColor: '#e7ede9',
  glowColor: '#c98a3d',
  quality: 'auto',
})

const canvasEl = ref<HTMLCanvasElement | null>(null)
const webglSupported = ref(true)

const FOLLOWER_LERP = 0.08
const MIN_SPAWN_DIST = 0.01
const MIN_SPAWN_INTERVAL = 0.075
const MOVE_SPEED_EPSILON = 0.05
const SETTLE_DELAY = 0.22
const TRAIL_EXPAND = 0.18
const TRAIL_FADE = 0.6
const TRAIL_LIFE = 3
const SETTLE_EXPAND = 0.1
const SETTLE_FADE = 0.42
const SETTLE_LIFE = 4.4
const CLICK_EXPAND = 0.24
const CLICK_FADE = 0.5
const CLICK_LIFE = 3.4
const MIN_RENDER_SCALE = 0.4
const RENDER_SCALE_STEP = 0.8
const DEGRADE_COOLDOWN = 1.5
const MAX_DELTA = 0.05
const IDLE_AFTER = 2.5

const tier: Tier = { ...HIGH_TIER }

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.OrthographicCamera | null = null
let material: THREE.ShaderMaterial | null = null
let uniforms: RippleUniforms | null = null
let geometry: THREE.PlaneGeometry | null = null
let timer: THREE.Timer | null = null

let ripples: Ripple[] = []
let rippleHead = 0
let rippleData: THREE.Vector4[] = []
let rippleShape: THREE.Vector3[] = []
let aliveRipples = 0

let resizeObserver: ResizeObserver | null = null
let intersectionObserver: IntersectionObserver | null = null

let rafId = 0
let running = false
let inViewport = true
let reducedMotion = false
let scrollPending = false
let resizePending = false
let accumulator = 0

let renderScale = 1
let frameEmaMs = 16.7
let lastRenderAt = 0
let lastDegradeAt = 0

let elapsed = 0
let lastActivityAt = 0

let rectLeft = 0
let rectTop = 0
let rectWidth = 1
let rectHeight = 1

let pointerActive = false
let pointerX = 0.5
let pointerY = 0.5
let followerX = 0.5
let followerY = 0.5
let previousX = 0.5
let previousY = 0.5
let lastSpawnX = 0.5
let lastSpawnY = 0.5
let lastSpawnTime = 0
let lastMoveTime = 0
let moving = false
let settleRequested = false

const fallbackStyle = computed(() => ({
  backgroundColor: props.deepColor,
  backgroundImage: [
    `radial-gradient(95% 70% at 50% -8%, ${props.crestColor} 0%, rgba(0, 0, 0, 0) 62%)`,
    `radial-gradient(130% 95% at 50% 0%, ${props.midColor} 0%, ${props.deepColor} 68%)`,
  ].join(', '),
}))

interface RippleUniforms {
  u_time: { value: number }
  u_resolution: { value: THREE.Vector2 }
  u_ripple: { value: THREE.Vector4[] }
  u_shape: { value: THREE.Vector3[] }
  u_deep: { value: THREE.Color }
  u_mid: { value: THREE.Color }
  u_crest: { value: THREE.Color }
  u_glow: { value: THREE.Color }
}

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`

function buildFragmentShader(): string {
  const precision = tier.mediump ? 'mediump' : 'highp'
  const rings = tier.rings
  const toneMap = tier.mediump
    ? 'color = mix(color, sqrt(max(color, vec3(0.0))), 0.72);'
    : 'color = pow(max(color, vec3(0.0)), vec3(0.86));'
  const caustics = tier.caustics
    ? `
      float caus = sin(h * 9.0 + t * 1.2) * cos(h * 7.0 - t * 0.9);
      float caus2 = caus * caus;
      color += caus2 * caus2 * abs(caus) * u_glow * 0.05;
    `
    : ''
  const grain = tier.grain ? 'color += (hash(uv * u_resolution.xy * 0.5 + u_time) - 0.5) * 0.012;' : ''

  return `
    precision ${precision} float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec4 u_ripple[${tier.maxRipples}];
    uniform vec3 u_shape[${tier.maxRipples}];
    uniform vec3 u_deep;
    uniform vec3 u_mid;
    uniform vec3 u_crest;
    uniform vec3 u_glow;
    varying vec2 vUv;

    float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      f = f * f * (3.0 - 2.0 * f);
      float a = hash(i), b = hash(i + vec2(1.0, 0.0)), c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
      return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
    }

    float fbm(vec2 p) {
      float v = 0.0, a = 0.5;
      for (int i = 0; i < ${tier.octaves}; i++) {
        v += a * noise(p);
        p *= 2.02;
        a *= 0.5;
      }
      return v;
    }

    float surface(vec2 p, float t) {
      float h = 0.0;
      h += sin(dot(p, normalize(vec2( 0.85,  0.55))) * 1.6 + t * 0.70) * 0.34;
      h += sin(dot(p, normalize(vec2(-0.65,  0.85))) * 2.2 + t * 0.85) * 0.18;
      h += sin(dot(p, normalize(vec2( 0.75, -0.70))) * 3.6 + t * 1.10) * 0.10;
      h += sin(dot(p, normalize(vec2(-0.95, -0.40))) * 5.0 + t * 1.35) * 0.05;
      vec2 q = vec2(fbm(p * 1.15 + t * 0.08), fbm(p * 1.15 + vec2(5.2, 1.3) - t * 0.06));
      h += (fbm(p * 1.9 + q) - 0.5) * 0.22;
      return h;
    }

    void main() {
      vec2 uv = vUv;
      float aspect = u_resolution.x / max(u_resolution.y, 1.0);
      vec2 p = (uv - 0.5) * vec2(aspect, 1.0);

      float t = u_time * 0.3;
      float h = surface(p, t);

      float rippleHeight = 0.0;
      float rippleGlow = 0.0;

      for (int i = 0; i < ${tier.maxRipples}; i++) {
        vec4 r = u_ripple[i];
        if (r.w <= 0.0) continue;

        vec3 shape = u_shape[i];
        float age = u_time - r.z;
        if (age < 0.0 || age > shape.z) continue;

        vec2 rp = (r.xy - 0.5) * vec2(aspect, 1.0);
        float d = length(p - rp);
        float str = r.w;

        for (int k = 0; k < ${rings}; k++) {
          float ringAge = age - float(k) * 0.1;
          if (ringAge < 0.0) continue;

          float radius = ringAge * shape.x;
          float width = 0.016 + ringAge * 0.007;
          float x = (d - radius) / width;
          float ring = exp(-x * x);
          float ageFade = exp(-ringAge * shape.y);
          float distFade = 1.0 / (1.0 + ringAge * 0.75);
          float ringFade = 1.0 - float(k) * 0.32;

          rippleHeight += ring * ageFade * distFade * ringFade * str * 0.2;
        }

        rippleHeight -= exp(-(d * 20.0 + age * 4.0)) * str * 0.16;
        rippleGlow += exp(-(d * 15.0 + age * 2.2)) * str * 0.3;
      }

      h += rippleHeight;

      vec3 base = mix(u_deep, u_mid, 0.4);
      vec3 light = mix(u_mid, u_crest, 0.55);
      vec3 foam = mix(u_crest, vec3(1.0), 0.5);
      vec3 bright = mix(u_crest, vec3(1.0), 0.85);

      vec3 color = u_deep;
      color = mix(color, base, smoothstep(-0.42, 0.02, h));
      color = mix(color, u_mid, smoothstep(-0.05, 0.26, h));
      color = mix(color, light, smoothstep(0.14, 0.5, h));
      color = mix(color, foam, smoothstep(0.4, 0.74, h));
      color = mix(color, bright, smoothstep(0.68, 0.95, h) * 0.7);

      float spec = pow(max(0.0, h - 0.12), 3.0);
      color += spec * mix(u_glow, vec3(1.0), 0.45) * 0.4;

      color += rippleGlow * u_glow;

      ${caustics}

      float depth = smoothstep(-0.6, 0.6, p.y);
      color *= mix(0.94, 1.06, depth);

      ${toneMap}

      float centerFade = smoothstep(0.0, 1.35, length(p) * 0.5);
      color = mix(color * 0.72, color, centerFade);

      float vignette = 1.0 - smoothstep(0.8, 1.9, length(p)) * 0.26;
      color *= vignette;

      ${grain}

      gl_FragColor = vec4(color, 1.0);
    }
  `
}

function detectWebGL2(): boolean {
  try {
    const probe = document.createElement('canvas')
    const context = probe.getContext('webgl2')
    return context !== null
  } catch {
    return false
  }
}

function resolveTier(): void {
  const coarse = window.matchMedia('(pointer: coarse)').matches
  const cores = navigator.hardwareConcurrency ?? 8
  const smallViewport = Math.min(window.innerWidth, window.innerHeight) < 640
  const low = props.quality === 'low' || (props.quality !== 'high' && (coarse || cores <= 4 || smallViewport))
  Object.assign(tier, low ? LOW_TIER : HIGH_TIER)

  ripples = Array.from({ length: tier.maxRipples }, () => ({
    x: 0.5,
    y: 0.5,
    birth: -1000,
    strength: 0,
    expand: TRAIL_EXPAND,
    fade: TRAIL_FADE,
    life: TRAIL_LIFE,
  }))
  rippleData = Array.from({ length: tier.maxRipples }, () => new THREE.Vector4(0.5, 0.5, -1000, 0))
  rippleShape = Array.from({ length: tier.maxRipples }, () => new THREE.Vector3(TRAIL_EXPAND, TRAIL_FADE, TRAIL_LIFE))
}

function updateRect(): void {
  const canvas = canvasEl.value
  if (!canvas) return
  const box = canvas.getBoundingClientRect()
  rectLeft = box.left
  rectTop = box.top
  rectWidth = box.width || 1
  rectHeight = box.height || 1
}

function resizeRenderer(): void {
  const canvas = canvasEl.value
  if (!canvas || !renderer || !uniforms) return
  updateRect()

  const dpr = Math.min(window.devicePixelRatio || 1, tier.dprCap) * renderScale
  const dimension = Math.max(rectWidth, rectHeight) * dpr
  const cap = dimension > tier.maxDimension ? tier.maxDimension / dimension : 1
  const ratio = Math.max(0.35, dpr * cap)

  renderer.setPixelRatio(ratio)
  renderer.setSize(rectWidth, rectHeight, false)
  uniforms.u_resolution.value.set(rectWidth, rectHeight)
}

function scheduleResize(): void {
  if (resizePending) return
  resizePending = true
  requestAnimationFrame(() => {
    resizePending = false
    resizeRenderer()
    if (!running) renderStaticFrame()
  })
}

function spawnRipple(x: number, y: number, strength: number, expand: number, fade: number, life: number): void {
  const slot = ripples[rippleHead]
  if (!slot) return
  slot.x = x
  slot.y = y
  slot.birth = elapsed
  slot.strength = strength
  slot.expand = expand
  slot.fade = fade
  slot.life = life
  rippleHead = (rippleHead + 1) % tier.maxRipples
}

function syncRippleUniforms(): void {
  const now = elapsed
  let alive = 0
  for (let i = 0; i < tier.maxRipples; i++) {
    const slot = ripples[i]
    const data = rippleData[i]
    const shape = rippleShape[i]
    if (!slot || !data || !shape) continue
    const age = now - slot.birth
    if (slot.strength <= 0 || age < 0 || age > slot.life) {
      if (data.w !== 0) {
        data.set(0.5, 0.5, -1000, 0)
        shape.set(TRAIL_EXPAND, TRAIL_FADE, TRAIL_LIFE)
      }
      continue
    }
    alive += 1
    data.set(slot.x, slot.y, slot.birth, slot.strength)
    shape.set(slot.expand, slot.fade, slot.life)
  }
  aliveRipples = alive
}

function stepRipples(now: number, dt: number): void {
  const dx = followerX - previousX
  const dy = followerY - previousY
  const speed = dt > 0 ? Math.sqrt(dx * dx + dy * dy) / dt : 0
  previousX = followerX
  previousY = followerY

  if (!pointerActive) {
    if (moving && now - lastMoveTime > SETTLE_DELAY) {
      spawnRipple(followerX, followerY, 0.42, SETTLE_EXPAND, SETTLE_FADE, SETTLE_LIFE)
      moving = false
    }
    return
  }

  if (speed > MOVE_SPEED_EPSILON) {
    lastMoveTime = now
    moving = true
  }

  if (settleRequested) {
    settleRequested = false
    if (moving) {
      spawnRipple(followerX, followerY, 0.42, SETTLE_EXPAND, SETTLE_FADE, SETTLE_LIFE)
      moving = false
      lastMoveTime = now
    }
  }

  if (!moving) return

  const trailX = followerX - lastSpawnX
  const trailY = followerY - lastSpawnY
  const distance = Math.sqrt(trailX * trailX + trailY * trailY)
  if (distance < MIN_SPAWN_DIST || now - lastSpawnTime < MIN_SPAWN_INTERVAL) return

  const strength = Math.min(0.55, 0.16 + speed * 0.05)
  spawnRipple(followerX, followerY, strength, TRAIL_EXPAND, TRAIL_FADE, TRAIL_LIFE)
  lastSpawnX = followerX
  lastSpawnY = followerY
  lastSpawnTime = now
}

function adaptQuality(now: number): void {
  if (lastRenderAt > 0) {
    const intervalMs = (now - lastRenderAt) * 1000
    frameEmaMs = frameEmaMs * 0.9 + intervalMs * 0.1
  }
  lastRenderAt = now

  const slowThreshold = tier.targetFps >= 60 ? 30 : 48
  if (frameEmaMs > slowThreshold && renderScale > MIN_RENDER_SCALE && now - lastDegradeAt > DEGRADE_COOLDOWN) {
    renderScale = Math.max(MIN_RENDER_SCALE, renderScale * RENDER_SCALE_STEP)
    lastDegradeAt = now
    resizeRenderer()
  }
}

function isIdle(now: number): boolean {
  return aliveRipples === 0 && now - lastActivityAt > IDLE_AFTER
}

function animate(): void {
  if (!running) return
  rafId = requestAnimationFrame(animate)
  if (!timer || !renderer || !scene || !camera || !material || !uniforms) return

  timer.update()
  const dt = Math.min(timer.getDelta(), MAX_DELTA)
  elapsed += dt
  accumulator += dt

  const idle = isIdle(elapsed)
  if (accumulator < 1 / ((idle ? tier.idleFps : tier.targetFps) + 1)) return
  accumulator = 0

  if (!idle) adaptQuality(elapsed)

  const follow = Math.min(1, FOLLOWER_LERP * dt * 60)
  followerX += (pointerX - followerX) * follow
  followerY += (pointerY - followerY) * follow

  uniforms.u_time.value = elapsed
  stepRipples(elapsed, dt)
  syncRippleUniforms()
  renderer.render(scene, camera)
}

function startLoop(): void {
  if (running || reducedMotion || !inViewport || document.hidden || !webglSupported.value) return
  running = true
  lastSpawnTime = elapsed
  lastMoveTime = elapsed
  lastRenderAt = 0
  accumulator = 1
  rafId = requestAnimationFrame(animate)
}

function stopLoop(): void {
  running = false
  if (rafId !== 0) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
}

function syncActive(): void {
  if (inViewport && !document.hidden && !reducedMotion && webglSupported.value) startLoop()
  else stopLoop()
}

function handlePointer(clientX: number, clientY: number): void {
  const localX = clientX - rectLeft
  const localY = clientY - rectTop
  const inside = localX >= 0 && localX <= rectWidth && localY >= 0 && localY <= rectHeight
  if (!inside) {
    pointerActive = false
    return
  }
  pointerActive = true
  pointerX = localX / rectWidth
  pointerY = 1 - localY / rectHeight
}

function markActivity(): void {
  lastActivityAt = elapsed
  startLoop()
}

function updatePointer(clientX: number, clientY: number): void {
  handlePointer(clientX, clientY)
  markActivity()
}

function onPointerMove(event: PointerEvent): void {
  updatePointer(event.clientX, event.clientY)
}

function onPointerEnter(event: PointerEvent): void {
  updatePointer(event.clientX, event.clientY)
}

function spawnClickRipple(clientX: number, clientY: number): void {
  const localX = clientX - rectLeft
  const localY = clientY - rectTop
  if (localX < 0 || localX > rectWidth || localY < 0 || localY > rectHeight) return

  const x = localX / rectWidth
  const y = 1 - localY / rectHeight

  pointerX = x
  pointerY = y
  followerX = x
  followerY = y
  previousX = x
  previousY = y
  lastSpawnX = x
  lastSpawnY = y
  lastSpawnTime = elapsed
  moving = false

  spawnRipple(x, y, 1, CLICK_EXPAND, CLICK_FADE, CLICK_LIFE)
  spawnRipple(x, y, 0.5, CLICK_EXPAND * 0.6, CLICK_FADE * 0.6, CLICK_LIFE + 1.2)
}

function onPointerDown(event: PointerEvent): void {
  if (event.pointerType === 'touch') return
  spawnClickRipple(event.clientX, event.clientY)
  markActivity()
}

function onTouchStart(event: TouchEvent): void {
  const touch = event.touches[0]
  if (touch) {
    handlePointer(touch.clientX, touch.clientY)
    spawnClickRipple(touch.clientX, touch.clientY)
  }
  markActivity()
}

function onTouchMove(event: TouchEvent): void {
  const touch = event.touches[0]
  if (touch) handlePointer(touch.clientX, touch.clientY)
  markActivity()
}

function onTouchEnd(): void {
  settleRequested = true
  markActivity()
}

function onScroll(): void {
  markActivity()
  if (scrollPending) return
  scrollPending = true
  requestAnimationFrame(() => {
    scrollPending = false
    updateRect()
  })
}

function onVisibilityChange(): void {
  markActivity()
  syncActive()
}

function onContextLost(event: Event): void {
  event.preventDefault()
  stopLoop()
}

function onContextRestored(): void {
  resizeRenderer()
  syncActive()
  if (!running) renderStaticFrame()
}

function renderStaticFrame(): void {
  if (!renderer || !scene || !camera || !material) return
  syncRippleUniforms()
  renderer.render(scene, camera)
}

function teardown(): void {
  stopLoop()
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerenter', onPointerEnter, true)
  window.removeEventListener('pointerdown', onPointerDown)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchmove', onTouchMove)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', markActivity)
  window.removeEventListener('keydown', markActivity)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  resizeObserver?.disconnect()
  resizeObserver = null
  intersectionObserver?.disconnect()
  intersectionObserver = null

  const canvas = canvasEl.value
  canvas?.removeEventListener('webglcontextlost', onContextLost)
  canvas?.removeEventListener('webglcontextrestored', onContextRestored)

  geometry?.dispose()
  material?.dispose()
  renderer?.dispose()
  renderer?.forceContextLoss()

  renderer = null
  scene = null
  camera = null
  material = null
  geometry = null
  timer = null
  ripples = []
  rippleData = []
  rippleShape = []
}

onMounted(() => {
  const canvas = canvasEl.value
  if (!canvas) return

  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  webglSupported.value = detectWebGL2()
  if (!webglSupported.value) return

  resolveTier()

  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: false,
      antialias: false,
      stencil: false,
      depth: false,
      preserveDrawingBuffer: false,
      precision: tier.mediump ? 'mediump' : 'highp',
      powerPreference: window.matchMedia('(pointer: coarse)').matches ? 'low-power' : 'high-performance',
      failIfMajorPerformanceCaveat: false,
    })
  } catch {
    webglSupported.value = false
    renderer = null
    return
  }

  scene = new THREE.Scene()
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
  timer = new THREE.Timer()

  uniforms = {
    u_time: { value: 0 },
    u_resolution: { value: new THREE.Vector2(1, 1) },
    u_ripple: { value: rippleData },
    u_shape: { value: rippleShape },
    u_deep: { value: new THREE.Color(props.deepColor) },
    u_mid: { value: new THREE.Color(props.midColor) },
    u_crest: { value: new THREE.Color(props.crestColor) },
    u_glow: { value: new THREE.Color(props.glowColor) },
  }

  material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader: buildFragmentShader(),
    uniforms: uniforms as unknown as { [uniform: string]: THREE.IUniform },
  })

  geometry = new THREE.PlaneGeometry(2, 2)
  scene.add(new THREE.Mesh(geometry, material))

  resizeRenderer()
  followerX = pointerX
  followerY = pointerY
  previousX = followerX
  previousY = followerY
  lastSpawnX = followerX
  lastSpawnY = followerY

  window.addEventListener('pointermove', onPointerMove, { passive: true })
  window.addEventListener('pointerenter', onPointerEnter, { passive: true, capture: true })
  window.addEventListener('pointerdown', onPointerDown, { passive: true })
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchmove', onTouchMove, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: true })
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', markActivity, { passive: true })
  window.addEventListener('keydown', markActivity)
  document.addEventListener('visibilitychange', onVisibilityChange)
  canvas.addEventListener('webglcontextlost', onContextLost, false)
  canvas.addEventListener('webglcontextrestored', onContextRestored, false)

  resizeObserver = new ResizeObserver(scheduleResize)
  resizeObserver.observe(canvas)

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      inViewport = entry ? entry.isIntersecting : true
      if (inViewport) lastActivityAt = elapsed
      syncActive()
    },
    { threshold: 0 },
  )
  intersectionObserver.observe(canvas)

  if (reducedMotion) {
    renderStaticFrame()
  } else {
    syncActive()
  }
})

onBeforeUnmount(teardown)
</script>

<template>
  <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
    <div class="absolute inset-0" :style="fallbackStyle"></div>
    <canvas v-show="webglSupported" ref="canvasEl" class="absolute inset-0 h-full w-full"></canvas>
  </div>
</template>
