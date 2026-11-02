<script setup lang="ts">
/**
 * The hero globe: a 3D sphere wrapped in an OpenLayers-rendered world map,
 * with the animated delivery network and a field of twinkling sparkles over it.
 *
 * Deliberately chrome-free — no frame, no coordinate read-outs, no panels.
 * The surface data comes from `globeTexture.ts` (OpenLayers); this component
 * only spins the sphere and animates what sits on it.
 */
defineOptions({ name: 'GlobeScene' })

import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import {
  BoxGeometry,
  CanvasTexture,
  ConeGeometry,
  CylinderGeometry,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshPhongMaterial,
  MeshStandardMaterial,
  OctahedronGeometry,
  SRGBColorSpace,
  SphereGeometry,
  TOUCH,
} from 'three'
import type { GlobeInstance } from 'globe.gl'
import { HQ, NETWORK_NODES, type NetworkNode } from '../data/network'
import { buildGlobeSurface, surfaceToDataUrl, type GlobeSurface } from './globeTexture'

const props = withDefaults(
  defineProps<{
    hq?: NetworkNode
    nodes?: NetworkNode[]
    height?: string
    interactive?: boolean
  }>(),
  {
    hq: () => HQ,
    nodes: () => NETWORK_NODES,
    height: '100%',
    interactive: true,
  },
)

interface ArcDatum {
  id: string
  kind: 'branch' | 'partner'
  startLat: number
  startLng: number
  endLat: number
  endLng: number
  color: string[]
  duration: number
}

interface RingDatum {
  id: string
  lat: number
  lng: number
  maxRadius: number
  speed: number
  period: number
}

interface SatelliteDatum {
  type: 'satellite'
  id: string
  speed: number
  phase: number
  inclination: number
  startLng: number
  altitude: number
  scale: number
}

interface SparkleDatum {
  type: 'sparkle'
  id: string
  lat: number
  lng: number
  altitude: number
  phase: number
  speed: number
  size: number
}

type LayerDatum = SatelliteDatum | SparkleDatum

const INITIAL_POV = { lat: 20, lng: 78, altitude: 1.78 }
const ARC_BRANCH: string[] = [
  'rgba(255, 255, 255, 0)',
  'rgba(255, 255, 255, 0.96)',
  'rgba(255, 255, 255, 0)',
]
const ARC_PARTNER: string[] = [
  'rgba(206, 210, 214, 0)',
  'rgba(226, 229, 232, 0.9)',
  'rgba(206, 210, 214, 0)',
]

const SATELLITES: SatelliteDatum[] = [
  { type: 'satellite', id: 'tt-orbit-1', speed: 0.22, phase: 0.4, inclination: 42, startLng: 62, altitude: 0.16, scale: 1.05 },
  { type: 'satellite', id: 'tt-orbit-2', speed: 0.15, phase: 2.7, inclination: 28, startLng: -24, altitude: 0.21, scale: 0.92 },
  { type: 'satellite', id: 'tt-orbit-3', speed: 0.105, phase: 4.6, inclination: 58, startLng: 138, altitude: 0.25, scale: 0.82 },
]

/** Deterministic PRNG so the sparkle field is identical on every load. */
function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Even coverage: `asin` spreads the latitudes so the poles are not crowded. */
const SPARKLES: SparkleDatum[] = (() => {
  const random = mulberry32(20260111)
  return Array.from({ length: 76 }, (_, index) => ({
    type: 'sparkle' as const,
    id: `sparkle-${index}`,
    lat: (Math.asin(random() * 2 - 1) * 180) / Math.PI,
    lng: random() * 360 - 180,
    altitude: 0.002 + random() * 0.016,
    phase: random() * Math.PI * 2,
    speed: 0.7 + random() * 1.9,
    size: 0.55 + random() * 1.15,
  }))
})()

const LAYER_DATA: LayerDatum[] = [...SATELLITES, ...SPARKLES]

const host = ref<HTMLDivElement | null>(null)
const failed = ref(false)
const ready = ref(false)
const flatSurface = shallowRef('')
/** Which renderer produced the globe surface — surfaced for debugging and e2e checks. */
const surfaceState = ref<'pending' | 'openlayers' | 'flat' | 'none'>('pending')

let globe: GlobeInstance | null = null
let material: MeshPhongMaterial | null = null
let texture: CanvasTexture | null = null
let resizeObserver: ResizeObserver | null = null
let rafId = 0
let disposed = false
let reducedMotion = false
let motionQuery: MediaQueryList | null = null
let motionListener: ((event: MediaQueryListEvent) => void) | null = null
let contextCanvas: HTMLCanvasElement | null = null
let contextLostListener: ((event: Event) => void) | null = null
let orbitElapsed = 0
let lastFrameTime = 0

const layerObjects = new Map<string, Mesh | Group>()
const layerData = new Map<string, LayerDatum>()

const allNodes = computed<NetworkNode[]>(() => {
  const seen = new Set<string>()
  const list: NetworkNode[] = [props.hq]
  seen.add(props.hq.id)
  for (const node of props.nodes) {
    if (seen.has(node.id) || node.kind === 'hq') continue
    seen.add(node.id)
    list.push(node)
  }
  return list
})

const remoteNodes = computed(() => allNodes.value.filter((node) => node.kind !== 'hq'))

const accessibleSummary = computed(() => {
  const locations = allNodes.value.map((node) => `${node.city}, ${node.country}`).join('; ')
  return `Thimi Tech headquarters: ${props.hq.city}, ${props.hq.country}. Delivery network: ${locations}. Drag to rotate, scroll to zoom.`
})

onMounted(() => {
  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion = motionQuery.matches
  motionListener = (event) => {
    reducedMotion = event.matches
    if (reducedMotion && rafId) {
      cancelAnimationFrame(rafId)
      rafId = 0
    } else {
      startAnimation()
    }
  }
  motionQuery.addEventListener('change', motionListener)
  void start()
})

onBeforeUnmount(() => {
  disposed = true
  if (motionQuery && motionListener) motionQuery.removeEventListener('change', motionListener)
  motionQuery = null
  motionListener = null
  teardown()
})

watch(
  () => props.interactive,
  (enabled) => setInteraction(enabled),
)

watch(
  [() => props.hq, () => props.nodes],
  () => {
    if (globe) applyNetwork(globe)
  },
  { deep: true },
)

async function start() {
  const surfacePromise = buildGlobeSurface(allNodes.value).catch(() => null)

  try {
    await initGlobe()
  } catch (error) {
    if (disposed) return
    console.warn('[GlobeScene] Unable to start the WebGL globe.', error)
    failed.value = true
  }

  const surface = await surfacePromise
  if (disposed) return
  if (!surface) {
    surfaceState.value = 'none'
    return
  }
  if (failed.value) {
    flatSurface.value = surfaceToDataUrl(surface)
    surfaceState.value = 'flat'
    return
  }
  applySurface(surface)
  surfaceState.value = 'openlayers'
}

async function initGlobe() {
  const element = host.value
  if (!element) return

  const { default: Globe } = await import('globe.gl')
  if (disposed) return

  const instance = new Globe(element, { animateIn: !reducedMotion })
  globe = instance
  configure(instance, element)
  applyNetwork(instance)
  startAnimation()
  observeResize(element)
  watchContextLoss(instance)
  instance.onGlobeReady(() => {
    ready.value = true
  })
}

function configure(instance: GlobeInstance, container: HTMLElement) {
  const bounds = container.getBoundingClientRect()
  const width = Math.max(320, Math.round(bounds.width))
  const height = Math.max(320, Math.round(bounds.height))

  material = createGlobeMaterial()

  instance
    .width(width)
    .height(height)
    .backgroundColor('rgba(0,0,0,0)')
    .showAtmosphere(true)
    .atmosphereColor('#a9c8e0')
    .atmosphereAltitude(0.16)
    .showGraticules(false)
    .globeMaterial(material)
    .pointsTransitionDuration(0)
    .arcsTransitionDuration(0)
    .labelsTransitionDuration(0)
    .customThreeObject((datum) => {
      const layer = datum as LayerDatum
      const object = layer.type === 'satellite' ? buildSatellite(layer) : buildSparkle()
      layerObjects.set(layer.id, object)
      layerData.set(layer.id, layer)
      return object
    })
    .customThreeObjectUpdate((object, datum) => {
      const layer = datum as LayerDatum
      const mesh = object as Mesh | Group
      layerObjects.set(layer.id, mesh)
      layerData.set(layer.id, layer)
      updateLayerObject(mesh, layer, orbitElapsed)
    })
    .customLayerData(LAYER_DATA)
    .pointOfView(INITIAL_POV, 0)

  const controls = instance.controls()
  controls.enableDamping = true
  controls.dampingFactor = 0.075
  controls.rotateSpeed = 0.55
  controls.zoomSpeed = 0.85
  controls.enablePan = false
  controls.autoRotate = false
  controls.minDistance = 130
  controls.maxDistance = 460
  controls.touches.ONE = TOUCH.ROTATE
  controls.touches.TWO = TOUCH.DOLLY_ROTATE

  setInteraction(props.interactive)
}

function createGlobeMaterial(): MeshPhongMaterial {
  return new MeshPhongMaterial({
    color: 0x0f3a5c,
    emissive: 0x071c30,
    emissiveIntensity: 0.7,
    specular: 0x9dc4de,
    shininess: 10,
  })
}

/** Wraps the OpenLayers canvas around the sphere. */
function applySurface(surface: GlobeSurface) {
  if (!globe || !material) return

  texture?.dispose()
  texture = new CanvasTexture(surface.canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = Math.min(4, globe.renderer().capabilities.getMaxAnisotropy())

  material.map = texture
  material.color.set(0xffffff)
  material.emissiveIntensity = 0.3
  material.needsUpdate = true
}

function applyNetwork(instance: GlobeInstance) {
  const hq = props.hq
  const nodes = allNodes.value

  const arcs: ArcDatum[] = remoteNodes.value.map((node, index) => ({
    id: node.id,
    kind: node.kind === 'partner' ? 'partner' : 'branch',
    startLat: hq.lat,
    startLng: hq.lng,
    endLat: node.lat,
    endLng: node.lng,
    color: node.kind === 'branch' ? ARC_BRANCH : ARC_PARTNER,
    duration: 3200 + index * 180,
  }))

  const rings: RingDatum[] = [
    { id: 'hq-inner', lat: hq.lat, lng: hq.lng, maxRadius: 3.4, speed: 1.45, period: 1700 },
    { id: 'hq-outer', lat: hq.lat, lng: hq.lng, maxRadius: 5.4, speed: 1.0, period: 2800 },
  ]

  instance
    .pointLat((node) => (node as NetworkNode).lat)
    .pointLng((node) => (node as NetworkNode).lng)
    .pointColor((node) => nodeColor((node as NetworkNode).kind))
    .pointAltitude((node) => ((node as NetworkNode).kind === 'hq' ? 0.035 : 0.018))
    .pointRadius((node) => ((node as NetworkNode).kind === 'hq' ? 0.46 : 0.28))
    .pointsMerge(false)
    .pointsData(nodes)
    .arcStartLat((arc) => (arc as ArcDatum).startLat)
    .arcStartLng((arc) => (arc as ArcDatum).startLng)
    .arcEndLat((arc) => (arc as ArcDatum).endLat)
    .arcEndLng((arc) => (arc as ArcDatum).endLng)
    .arcColor((arc: object) => (arc as ArcDatum).color)
    .arcDashLength(0.36)
    .arcDashGap(0.3)
    .arcDashAnimateTime((arc) => (arc as ArcDatum).duration)
    .arcStroke((arc) => ((arc as ArcDatum).kind === 'branch' ? 0.42 : 0.32))
    .arcAltitudeAutoScale(0.4)
    .arcsData(arcs)
    .ringLat((ring) => (ring as RingDatum).lat)
    .ringLng((ring) => (ring as RingDatum).lng)
    .ringAltitude(0.018)
    .ringColor(() => (t: number) => `rgba(255, 255, 255, ${(Math.max(0, 1 - t) * 0.75).toFixed(3)})`)
    .ringMaxRadius((ring) => (ring as RingDatum).maxRadius)
    .ringPropagationSpeed((ring) => (ring as RingDatum).speed)
    .ringRepeatPeriod((ring) => (ring as RingDatum).period)
    .ringResolution(64)
    .ringsData(rings)
    .labelLat((node) => (node as NetworkNode).lat)
    .labelLng((node) => (node as NetworkNode).lng)
    .labelText((node) => labelTextFor(node as NetworkNode))
    .labelColor((node) => labelColorFor(node as NetworkNode))
    .labelAltitude((node) => ((node as NetworkNode).kind === 'hq' ? 0.045 : 0.024))
    .labelSize((node) => ((node as NetworkNode).kind === 'hq' ? 0.72 : 0.5))
    .labelIncludeDot(false)
    .labelsData(nodes)
}

function setInteraction(enabled: boolean) {
  if (!globe) return
  globe.enablePointerInteraction(enabled)
  const controls = globe.controls()
  controls.enabled = enabled
  controls.enableRotate = enabled
  controls.enableZoom = enabled
  controls.enablePan = false
}

function observeResize(container: HTMLElement) {
  resizeObserver = new ResizeObserver(() => {
    if (!globe) return
    const width = Math.round(container.clientWidth)
    const height = Math.round(container.clientHeight)
    if (width > 0 && height > 0) globe.width(width).height(height)
  })
  resizeObserver.observe(container)
}

function watchContextLoss(instance: GlobeInstance) {
  contextCanvas = instance.renderer().domElement
  contextLostListener = (event: Event) => {
    event.preventDefault()
    if (disposed) return
    failed.value = true
    teardown()
  }
  contextCanvas.addEventListener('webglcontextlost', contextLostListener)
}

function startAnimation() {
  if (disposed || reducedMotion || rafId || !globe) return
  lastFrameTime = 0
  rafId = requestAnimationFrame(animate)
}

function animate(now: number) {
  rafId = 0
  if (disposed || !globe) return
  if (lastFrameTime === 0) lastFrameTime = now
  const delta = Math.min((now - lastFrameTime) / 1000, 0.1)
  lastFrameTime = now
  orbitElapsed += delta

  for (const [id, object] of layerObjects) {
    const datum = layerData.get(id)
    if (datum) updateLayerObject(object, datum, orbitElapsed)
  }

  rafId = requestAnimationFrame(animate)
}

function updateLayerObject(object: Mesh | Group, datum: LayerDatum, elapsed: number) {
  if (datum.type === 'satellite') {
    positionSatellite(object as Group, datum, elapsed)
    return
  }
  twinkleSparkle(object as Mesh, datum, elapsed)
}

function positionSatellite(group: Group, satellite: SatelliteDatum, elapsed: number) {
  if (!globe) return
  const angle = elapsed * satellite.speed + satellite.phase
  const lat = satellite.inclination * Math.sin(angle)
  const lng = wrapLongitude(satellite.startLng + angle * (180 / Math.PI))
  const coords = globe.getCoords(lat, lng, satellite.altitude)
  group.position.set(coords.x, coords.y, coords.z)
  group.lookAt(0, 0, 0)
}

/** Sparkles ride just above the surface and pulse, which reads as glitter on the map. */
function twinkleSparkle(mesh: Mesh, sparkle: SparkleDatum, elapsed: number) {
  if (!globe) return
  const coords = globe.getCoords(sparkle.lat, sparkle.lng, sparkle.altitude)
  mesh.position.set(coords.x, coords.y, coords.z)

  const pulse = Math.pow(Math.abs(Math.sin(elapsed * sparkle.speed + sparkle.phase)), 1.6)
  const twinkle = 0.2 + 0.8 * pulse
  const sparkleMaterial = mesh.material as MeshBasicMaterial
  sparkleMaterial.opacity = twinkle
  mesh.scale.setScalar(sparkle.size * (0.65 + 0.7 * twinkle))
}

function buildSparkle(): Mesh {
  return new Mesh(
    new OctahedronGeometry(0.85, 0),
    new MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 }),
  )
}

function buildSatellite(satellite: SatelliteDatum): Group {
  const group = new Group()
  group.scale.setScalar(satellite.scale)

  const bodyMaterial = new MeshStandardMaterial({
    color: 0xe8eaec,
    metalness: 0.7,
    roughness: 0.3,
    emissive: 0x2a2e33,
    emissiveIntensity: 0.5,
  })
  const panelMaterial = new MeshStandardMaterial({
    color: 0x9aa1a8,
    metalness: 0.55,
    roughness: 0.35,
    emissive: 0x3a3f45,
    emissiveIntensity: 0.6,
  })

  group.add(new Mesh(new BoxGeometry(1.05, 0.55, 0.55), bodyMaterial))

  for (const side of [-1, 1]) {
    const panel = new Mesh(new BoxGeometry(1.45, 0.045, 0.62), panelMaterial)
    panel.position.x = side * 1.32
    group.add(panel)

    const strut = new Mesh(new BoxGeometry(0.32, 0.05, 0.05), bodyMaterial)
    strut.position.x = side * 0.68
    group.add(strut)
  }

  const mast = new Mesh(new CylinderGeometry(0.03, 0.03, 0.5, 8), bodyMaterial)
  mast.rotation.x = Math.PI / 2
  mast.position.z = -0.48
  group.add(mast)

  const dish = new Mesh(new ConeGeometry(0.2, 0.28, 14), panelMaterial)
  dish.rotation.x = -Math.PI / 2
  dish.position.z = -0.82
  group.add(dish)

  const beacon = new Mesh(new SphereGeometry(0.075, 10, 10), new MeshBasicMaterial({ color: 0xffffff }))
  beacon.position.set(0, 0.34, 0)
  group.add(beacon)

  return group
}

function teardown() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (contextCanvas && contextLostListener) {
    contextCanvas.removeEventListener('webglcontextlost', contextLostListener)
  }
  contextCanvas = null
  contextLostListener = null

  for (const object of layerObjects.values()) disposeObject(object)
  layerObjects.clear()
  layerData.clear()

  texture?.dispose()
  texture = null
  material?.dispose()
  material = null

  const current = globe
  globe = null
  if (current) {
    try {
      current._destructor()
    } catch (error) {
      console.warn('[GlobeScene] Globe teardown reported an issue.', error)
    }
  }

  host.value?.replaceChildren()
}

function disposeObject(root: Mesh | Group) {
  const disposables = new Set<{ dispose(): void }>()
  root.traverse((object) => {
    const mesh = object as Mesh
    if (mesh.geometry) disposables.add(mesh.geometry)
    const meshMaterial = mesh.material
    if (Array.isArray(meshMaterial)) {
      for (const item of meshMaterial) disposables.add(item)
    } else if (meshMaterial) {
      disposables.add(meshMaterial)
    }
  })
  for (const item of disposables) item.dispose()
}

function nodeColor(kind: NetworkNode['kind']): string {
  if (kind === 'hq') return '#ffffff'
  return kind === 'branch' ? '#eef0f2' : '#cfd3d7'
}

function labelTextFor(node: NetworkNode): string {
  return node.kind === 'hq' ? 'Kathmandu · HQ' : node.city
}

function labelColorFor(node: NetworkNode): string {
  if (node.kind === 'hq') return '#ffffff'
  return node.kind === 'branch' ? '#f2f4f5' : '#dcdfe2'
}

function wrapLongitude(value: number): number {
  return ((((value + 180) % 360) + 360) % 360) - 180
}
</script>

<template>
  <div
    class="globe-scene"
    :class="{ 'is-static': !interactive }"
    :style="{ height }"
    :data-globe-surface="surfaceState"
    role="region"
    aria-label="Interactive 3D globe of the Thimi Tech delivery network"
  >
    <div v-if="!failed" ref="host" class="globe-host" aria-hidden="true"></div>

    <figure v-else-if="flatSurface" class="globe-flat">
      <img :src="flatSurface" alt="World map of the Thimi Tech delivery network" />
    </figure>

    <div v-else class="globe-plain" aria-hidden="true"></div>

    <div v-if="!ready && !failed" class="globe-loading" aria-hidden="true">
      <span></span>
    </div>

    <p class="sr-only">{{ accessibleSummary }}</p>
  </div>
</template>

<style scoped>
.globe-scene {
  position: relative;
  width: 100%;
  min-height: 320px;
  overflow: hidden;
}

.globe-scene::before {
  content: '';
  position: absolute;
  inset: -10% -8%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle at 50% 48%, rgb(18 69 111 / 0.16), rgb(255 255 255 / 0) 62%);
}

.globe-host,
.globe-flat,
.globe-plain {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.globe-host :deep(canvas) {
  display: block;
}

.globe-flat {
  display: grid;
  place-items: center;
  margin: 0;
}

.globe-flat img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.globe-plain {
  inset: 12%;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 32%, #2f6f9e, #123f66 58%, #061a2e);
  box-shadow: 0 30px 80px rgb(18 69 111 / 0.28);
}

.globe-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  pointer-events: none;
}

.globe-loading span {
  width: 28px;
  height: 28px;
  border: 1px solid rgb(10 10 10 / 0.16);
  border-top-color: #0a0a0a;
  border-radius: 50%;
  animation: globe-spin 900ms linear infinite;
}

@keyframes globe-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .globe-loading span {
    animation: none;
  }
}
</style>
