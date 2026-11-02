/**
 * OpenLayers builds the geographic surface of the hero globe.
 *
 * The hero keeps a real, draggable 3D globe, but every piece of *map data* on it —
 * ocean, country polygons, graticule, coast glow and city markers — is projected,
 * styled and rasterised here by OpenLayers into an equirectangular 2:1 canvas
 * (EPSG:4326). That canvas is wrapped around the three.js sphere, which only spins
 * it and adds the animated network routes and sparkles on top.
 *
 * The palette is strictly monochrome: a graphite ocean, silver countries and bright
 * white boundaries, so the globe stays the one dramatic element on a white page.
 */
import Feature from 'ol/Feature.js'
import GeoJSON from 'ol/format/GeoJSON.js'
import OlMap from 'ol/Map.js'
import View from 'ol/View.js'
import LineString from 'ol/geom/LineString.js'
import Point from 'ol/geom/Point.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import CircleStyle from 'ol/style/Circle.js'
import Fill from 'ol/style/Fill.js'
import Stroke from 'ol/style/Stroke.js'
import Style from 'ol/style/Style.js'
import 'ol/ol.css'
import { feature } from 'topojson-client'
import type { FeatureLike } from 'ol/Feature.js'
import type { Feature as GeoJsonFeature, FeatureCollection, Geometry } from 'geojson'
import type { Topology } from 'topojson-specification'
import type { NetworkNode } from '../data/network'

export interface GlobeSurface {
  /** Equirectangular map: longitude -180 → +180 across x, latitude +90 → -90 down y. */
  canvas: HTMLCanvasElement
  width: number
  height: number
}

type CountryProperties = { name?: string }
type CountryFeature = GeoJsonFeature<Geometry, CountryProperties>

/** 2:1 canvas — the aspect ratio a sphere texture needs. */
const WIDTH = 2048
const HEIGHT = 1024
const WORLD_EXTENT: [number, number, number, number] = [-180, -90, 180, 90]

/* Navy ocean, grey land, white boundaries — the palette asked for on the hero globe. */
const OCEAN_CORE = '#12456f'
const OCEAN_MID = '#0b2b4a'
const OCEAN_EDGE = '#061a2e'

/** Greyscale atlas: neighbouring countries differ just enough to read as separate places. */
const LAND_PALETTE = [
  '#dfe3e7',
  '#cdd2d7',
  '#bcc2c8',
  '#abb2b9',
  '#9aa2aa',
  '#8a929a',
  '#7a838b',
  '#6b747c',
]
const ICE = '#f7fafc'
/** Wide enough to survive mip-mapping on the sphere — boundaries must stay visible. */
const LAND_BORDER = 'rgba(255, 255, 255, 0.95)'
const BORDER_WIDTH = 2.2
const COAST_GLOW = 'rgba(186, 222, 255, 0.22)'
const COAST_GLOW_WIDTH = 6
const GRATICULE_LINE = 'rgba(198, 224, 246, 0.12)'
const GRATICULE_MAIN = 'rgba(214, 234, 250, 0.3)'

const NODE_STYLES = {
  hq: { halo: 'rgba(255, 255, 255, 0.22)', haloRadius: 32, core: '#ffffff', coreRadius: 8 },
  branch: { halo: 'rgba(255, 255, 255, 0.14)', haloRadius: 20, core: '#eef0f2', coreRadius: 5 },
  partner: { halo: 'rgba(226, 229, 232, 0.14)', haloRadius: 20, core: '#cfd3d7', coreRadius: 5 },
} as const

/**
 * Renders the world with OpenLayers and returns the finished canvas.
 * Resolves to `null` when the browser cannot rasterise it (SSR, no 2D context…),
 * in which case the caller falls back to the plain WebGL globe.
 */
export async function buildGlobeSurface(nodes: NetworkNode[]): Promise<GlobeSurface | null> {
  if (typeof document === 'undefined') return null

  const container = document.createElement('div')
  container.setAttribute('aria-hidden', 'true')
  Object.assign(container.style, {
    position: 'fixed',
    top: '0',
    left: '-10000px',
    width: `${WIDTH}px`,
    height: `${HEIGHT}px`,
    pointerEvents: 'none',
  })
  document.body.appendChild(container)

  let map: OlMap | null = null
  try {
    const graticule = new VectorLayer({
      source: new VectorSource({ features: buildGraticule() }),
      style: graticuleStyle,
    })
    const land = new VectorLayer({
      source: new VectorSource(),
      style: countryStyle,
    })
    const markers = new VectorLayer({
      source: new VectorSource({ features: buildNodeMarkers(nodes) }),
      style: markerStyle,
    })

    map = new OlMap({
      target: container,
      layers: [graticule, land, markers],
      controls: [],
      interactions: [],
      pixelRatio: 1,
      view: new View({
        projection: 'EPSG:4326',
        center: [0, 0],
        resolution: 360 / WIDTH,
        extent: WORLD_EXTENT,
        constrainResolution: false,
        multiWorld: false,
        rotation: 0,
      }),
    })

    // A missing world dataset must not cost us the whole globe: the ocean,
    // graticule and network markers are still drawn underneath.
    let countries: CountryFeature[] = []
    try {
      countries = await loadCountries()
    } catch (error) {
      console.warn(
        '[globeTexture] Country boundaries unavailable — drawing the base map only.',
        error,
      )
    }

    if (countries.length) {
      const collection: FeatureCollection<Geometry, CountryProperties> = {
        type: 'FeatureCollection',
        features: countries,
      }
      land
        .getSource()
        ?.addFeatures(
          new GeoJSON().readFeatures(collection, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:4326',
          }),
        )
    }

    await renderOnce(map)
    return composite(container)
  } catch (error) {
    console.warn('[globeTexture] OpenLayers could not build the globe surface.', error)
    return null
  } finally {
    map?.setTarget(undefined)
    container.remove()
  }
}

/** PNG data URL of an already-built surface — used by the flat, no-WebGL fallback view. */
export function surfaceToDataUrl(surface: GlobeSurface): string {
  try {
    return surface.canvas.toDataURL('image/png')
  } catch {
    return ''
  }
}

async function loadCountries(): Promise<CountryFeature[]> {
  const response = await fetch(`${import.meta.env.BASE_URL}countries-110m.json`)
  if (!response.ok) throw new Error(`Country data request failed (${response.status})`)

  const topology = (await response.json()) as Topology
  const countriesObject = topology.objects['countries']
  if (!countriesObject || countriesObject.type !== 'GeometryCollection') {
    throw new Error('Country topology has an unexpected shape')
  }

  const collection = feature(
    topology,
    countriesObject,
  ) as unknown as FeatureCollection<Geometry, CountryProperties>

  return collection.features.filter(
    (country): country is CountryFeature => Boolean(country.geometry),
  )
}

function buildGraticule(): Feature<LineString>[] {
  const features: Feature<LineString>[] = []

  for (let lon = -180; lon <= 180; lon += 15) {
    const main = lon === 0 || lon === -180 || lon === 180
    const line = new Feature(new LineString([lon, -90, lon, 90]))
    line.set('main', main)
    features.push(line)
  }
  for (let lat = -75; lat <= 75; lat += 15) {
    const line = new Feature(new LineString([-180, lat, 180, lat]))
    line.set('main', lat === 0)
    features.push(line)
  }

  return features
}

function graticuleStyle(feature: FeatureLike): Style {
  return new Style({
    stroke: new Stroke({
      color: feature.get('main') ? GRATICULE_MAIN : GRATICULE_LINE,
      width: feature.get('main') ? 1.2 : 0.9,
    }),
  })
}

function buildNodeMarkers(nodes: NetworkNode[]): Feature<Point>[] {
  return nodes.map((node) => {
    const marker = new Feature(new Point([node.lng, node.lat]))
    marker.set('kind', node.kind)
    return marker
  })
}

function markerStyle(feature: FeatureLike): Style[] {
  const tone = NODE_STYLES[(feature.get('kind') as NetworkNode['kind']) ?? 'branch'] ?? NODE_STYLES.branch
  return [
    new Style({
      image: new CircleStyle({
        radius: tone.haloRadius,
        fill: new Fill({ color: tone.halo }),
      }),
    }),
    new Style({
      image: new CircleStyle({
        radius: tone.coreRadius,
        fill: new Fill({ color: tone.core }),
        stroke: new Stroke({ color: 'rgba(8, 10, 12, 0.85)', width: 1.4 }),
      }),
    }),
  ]
}

const countryStyleCache = new Map<string, Style[]>()

/** Two passes: a soft coast glow, then the crisp white boundary and silver fill. */
function countryStyle(feature: FeatureLike): Style[] {
  const name = String(feature.get('name') ?? '')
  const cached = countryStyleCache.get(name)
  if (cached) return cached

  const styles = [
    new Style({
      stroke: new Stroke({ color: COAST_GLOW, width: COAST_GLOW_WIDTH }),
    }),
    new Style({
      fill: new Fill({ color: landColor(name) }),
      stroke: new Stroke({ color: LAND_BORDER, width: BORDER_WIDTH }),
    }),
  ]
  countryStyleCache.set(name, styles)
  return styles
}

function landColor(name: string): string {
  if (/greenland|antarctica|svalbard|iceland|frozen/i.test(name)) return ICE
  let hash = 0
  for (let index = 0; index < name.length; index += 1) {
    hash = (hash * 31 + name.charCodeAt(index)) >>> 0
  }
  return LAND_PALETTE[hash % LAND_PALETTE.length] ?? ICE
}

function renderOnce(map: OlMap): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      window.clearTimeout(timer)
      resolve()
    }
    const timer = window.setTimeout(done, 5000)
    map.once('rendercomplete', done)
    map.renderSync()
  })
}

/** Paints the ocean gradient under the OpenLayers layers and flattens them into one canvas. */
function composite(container: HTMLElement): GlobeSurface | null {
  const canvas = document.createElement('canvas')
  canvas.width = WIDTH
  canvas.height = HEIGHT

  const context = canvas.getContext('2d')
  if (!context) return null

  // Kept low-contrast on purpose: a wide gradient shows up as a dark cap at the poles,
  // because the top and bottom texture rows are stretched over the sphere's poles.
  const ocean = context.createRadialGradient(
    WIDTH * 0.5,
    HEIGHT * 0.5,
    HEIGHT * 0.3,
    WIDTH * 0.5,
    HEIGHT * 0.5,
    HEIGHT * 1.1,
  )
  ocean.addColorStop(0, OCEAN_CORE)
  ocean.addColorStop(0.6, OCEAN_MID)
  ocean.addColorStop(1, OCEAN_EDGE)
  context.fillStyle = ocean
  context.fillRect(0, 0, WIDTH, HEIGHT)

  for (const layer of Array.from(container.querySelectorAll('canvas'))) {
    if (!layer.width || !layer.height) continue
    context.drawImage(layer, 0, 0, WIDTH, HEIGHT)
  }

  paintIceCaps(context)

  return { canvas, width: WIDTH, height: HEIGHT }
}

/**
 * Sea ice over the poles. The texture's top and bottom rows are stretched across the
 * sphere's poles, so a soft band there reads as a natural ice cap instead of a dark one.
 */
function paintIceCaps(context: CanvasRenderingContext2D) {
  const north = context.createLinearGradient(0, 0, 0, HEIGHT * 0.115)
  north.addColorStop(0, 'rgba(247, 251, 254, 0.96)')
  north.addColorStop(0.42, 'rgba(238, 246, 252, 0.5)')
  north.addColorStop(1, 'rgba(238, 246, 252, 0)')
  context.fillStyle = north
  context.fillRect(0, 0, WIDTH, HEIGHT * 0.115)

  const south = context.createLinearGradient(0, HEIGHT, 0, HEIGHT * 0.9)
  south.addColorStop(0, 'rgba(247, 251, 254, 0.98)')
  south.addColorStop(0.4, 'rgba(238, 246, 252, 0.62)')
  south.addColorStop(1, 'rgba(238, 246, 252, 0)')
  context.fillStyle = south
  context.fillRect(0, HEIGHT * 0.9, WIDTH, HEIGHT * 0.1)
}
