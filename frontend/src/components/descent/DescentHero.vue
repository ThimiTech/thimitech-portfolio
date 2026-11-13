<script setup lang="ts">
/**
 * Orbit to Thimi in one shot. The globe, the country and the town are a single drawing
 * (an orthographic projection facing Nepal) that is only ever scaled about the Thimi pin,
 * so nothing cuts or cross-fades on the way down.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { geoGraticule10, geoOrthographic, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'
import type { Feature, FeatureCollection } from 'geojson'
import { canAnimate, gsap } from './motion'
import { useSite } from './site'

const CENTRE: [number, number] = [500, 280]
const RADIUS = 7000 // globe radius in viewBox units at zoom 1, where Nepal fills the frame
const K0 = 0.04 // opening zoom: the whole globe in view
const K_VALLEY = 3.4
const K_TOWN = 12

const face = () => geoOrthographic().rotate([-84.12, -28.39]).scale(RADIUS).translate(CENTRE).clipAngle(90)
const [px, py] = face()([85.3875, 27.6806]) as [number, number] // Madhyapur Thimi

// Wide screens leave empty map space on the left for the copy.
const viewBox = typeof window.matchMedia === 'function' && window.matchMedia('(min-width: 761px)').matches ? '-330 0 1330 560' : '0 0 1000 560'

const districts = ref<{ name: string; d: string }[]>([])
const land = ref('')
const graticule = canAnimate ? (geoPath(face().precision(6))(geoGraticule10()) ?? '') : ''
const root = ref<HTMLElement | null>(null)
const world = ref<SVGGElement | null>(null)
const far = ref<SVGGElement | null>(null)
let ctx: gsap.Context | undefined

const { site } = useSite()
const facts = computed(() => {
  const s = site.value.stats
  return [
    { value: site.value.founded.slice(0, 4), label: 'Founded' },
    { value: s ? String(s.people) : '—', label: 'People' },
    { value: s ? String(s.projects) : '—', label: 'Case studies' },
    { value: s ? String(s.open_roles) : '—', label: 'Open roles' },
  ]
})

const clamp01 = (n: number) => Math.min(1, Math.max(0, n))
const zoom = { z: Math.log(K0) } // log scale, so equal scroll feels like equal descent

function draw() {
  const k = Math.exp(zoom.z)
  world.value?.setAttribute('transform', `matrix(${k} 0 0 ${k} ${px * (1 - k)} ${py * (1 - k)})`)
  // From orbit Nepal is one lit shape; the districts resolve on the way in, and the globe fades behind them.
  root.value?.style.setProperty('--detail', String(clamp01((zoom.z - Math.log(0.1)) / Math.log(6))))
  const globe = 1 - clamp01((zoom.z - Math.log(0.3)) / -Math.log(0.3))
  if (far.value) {
    far.value.style.opacity = String(globe)
    far.value.style.visibility = globe ? 'visible' : 'hidden'
  }
}

onMounted(async () => {
  if (canAnimate && root.value) {
    ctx = gsap.context(() => {
      gsap.from('.line > span', { yPercent: 115, duration: 1.1, ease: 'power4.out', stagger: 0.12, delay: 0.1 })
      gsap.from('.copy .kicker, .lede, .cta', { autoAlpha: 0, y: 16, duration: 0.8, ease: 'power2.out', stagger: 0.08, delay: 0.7 })

      const caps = gsap.utils.toArray<HTMLElement>('.cap')
      const show = { autoAlpha: 1, y: 0, duration: 0.05 }
      const hide = { autoAlpha: 0, y: -24, duration: 0.04 }
      // Positions are fractions of the scene's scroll; the altimeter marks in the template follow them.
      gsap
        .timeline({
          defaults: { ease: 'none' },
          onUpdate: draw,
          scrollTrigger: { trigger: root.value, start: 'top top', end: 'bottom bottom', scrub: 0.7 },
        })
        .fromTo('.copy', { autoAlpha: 1, yPercent: 0 }, { autoAlpha: 0, yPercent: -16, duration: 0.09, immediateRender: false }, 0)
        .fromTo('.hint', { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.04, immediateRender: false }, 0)
        .to('.stars', { autoAlpha: 0, scale: 1.35, duration: 0.24 }, 0.02)
        .to(zoom, { z: 0, duration: 0.27, ease: 'power1.inOut' }, 0.01)
        .fromTo(caps[0]!, { autoAlpha: 0, y: 24 }, show, 0.27)
        .to(caps[0]!, hide, 0.44)
        .to(zoom, { z: Math.log(K_VALLEY), duration: 0.14, ease: 'power1.inOut' }, 0.44)
        .fromTo(caps[1]!, { autoAlpha: 0, y: 24 }, show, 0.55)
        .to(caps[1]!, hide, 0.69)
        .to(zoom, { z: Math.log(K_TOWN), duration: 0.15, ease: 'power1.inOut' }, 0.69)
        .fromTo(caps[2]!, { autoAlpha: 0, y: 24 }, show, 0.81)
        .fromTo('.pin-label', { autoAlpha: 0, x: -8 }, { autoAlpha: 1, x: 0, duration: 0.05 }, 0.81)
        .to({}, { duration: 0.14 }, 0.86)
      draw()
    }, root.value)
  }
  const json = async (url: string) => (await fetch(url)).json()
  // The pin and the captions still tell the story if either drawing fails to load.
  json('/nepal-districts.geojson')
    .then((data: FeatureCollection) => {
      const path = geoPath(face())
      districts.value = data.features.map((f: Feature) => ({ name: String(f.properties?.name ?? ''), d: path(f) ?? '' }))
    })
    .catch(() => undefined)
  if (canAnimate) {
    json('/countries-110m.json')
      .then((topology) => (land.value = geoPath(face().precision(6))(feature(topology, topology.objects.land)) ?? ''))
      .catch(() => undefined)
  }
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section ref="root" class="scene" :class="{ 'is-static': !canAnimate }" aria-labelledby="home-title">
    <!-- What the altimeter measures: one mark per band of the descent. -->
    <span id="home" class="mark" style="top: 0; height: 174svh" />
    <span id="about" class="mark" style="top: 174svh; height: 129svh" />
    <span id="valley" class="mark" style="top: 303svh; height: 120svh" />
    <span id="thimi" class="mark" style="top: 423svh; bottom: 0" />

    <div class="stage">
      <div class="stars" aria-hidden="true" />

      <svg class="map" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet" role="img" aria-label="The globe, zooming in to Nepal's districts with Thimi marked in the Kathmandu valley">
        <defs>
          <radialGradient id="dh-atmo">
            <stop offset="95%" stop-color="#ff5a1f" stop-opacity="0" />
            <stop offset="97.6%" stop-color="#ff5a1f" stop-opacity="0.5" />
            <stop offset="100%" stop-color="#ff5a1f" stop-opacity="0" />
          </radialGradient>
          <radialGradient id="dh-sphere" cx="38%" cy="30%" r="75%">
            <stop offset="0%" stop-color="#17212a" />
            <stop offset="70%" stop-color="#0a0f13" />
            <stop offset="100%" stop-color="#05070a" />
          </radialGradient>
        </defs>
        <g ref="world">
          <g v-if="canAnimate" ref="far">
            <circle :cx="CENTRE[0]" :cy="CENTRE[1]" :r="RADIUS * 1.025" fill="url(#dh-atmo)" />
            <circle :cx="CENTRE[0]" :cy="CENTRE[1]" :r="RADIUS" class="sphere" />
            <path :d="graticule" class="graticule" />
            <path :d="land" class="land" />
          </g>
          <g class="country">
            <path v-for="d in districts" :key="d.name" :d="d.d" :class="{ home: d.name === 'Bhaktapur' }" />
          </g>
        </g>
        <g :transform="`translate(${px} ${py})`">
          <circle r="16" class="pulse" />
          <circle r="4.5" class="dot" />
          <text x="14" y="4" class="pin-label">Thimi · 27.6806° N, 85.3875° E</text>
        </g>
      </svg>

      <div class="copy wrap">
        <p class="kicker">Thimi Tech · Web GIS studio · Kathmandu, Nepal</p>
        <h1 id="home-title">
          <span class="line"><span>From place </span></span>
          <span class="line"><span>to <em>possibility.</em></span></span>
        </h1>
        <div class="below">
          <p class="lede">
            We build web GIS platforms, software and AI that turn location data into tools people
            actually use. Scroll, and come down with us: from the satellite, to the country, to the
            street where the work gets done.
          </p>
          <div class="cta">
            <RouterLink to="/new#projects" class="btn btn-solid">Explore our work</RouterLink>
            <RouterLink to="/new#contact" class="btn">Start a project</RouterLink>
          </div>
        </div>
      </div>

      <div class="caps wrap">
        <div class="cap">
          <p class="kicker">Altitude 400 km · the country</p>
          <h2>Seventy-seven districts.<br />We map them for a living.</h2>
          <p>
            Thimi Tech started as a two-person GIS consultancy mapping flood risk for a local ward
            office. Today we build full web platforms for municipalities, tourism boards and startups
            that need their data to live on a map, not in a spreadsheet.
          </p>
        </div>
        <div class="cap">
          <p class="kicker">Altitude 12 km · the valley</p>
          <h2>One valley,<br />every layer of the stack.</h2>
          <p>
            The same team covers it all: GIS analysts who verify the data, engineers who build the
            pipelines and the API, and designers who make the result readable at first glance.
          </p>
        </div>
        <div class="cap">
          <p class="kicker">Altitude 1,326 m · home</p>
          <h2>One town.<br />Thimi.</h2>
          <p>Small teams, two-week cycles, and every client in the room while the map is still being drawn.</p>
          <dl class="facts">
            <div v-for="f in facts" :key="f.label">
              <dt>{{ f.label }}</dt>
              <dd>{{ f.value }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <p class="hint" aria-hidden="true">Scroll to descend <span>↓</span></p>
    </div>
  </section>
</template>

<style scoped>
.scene {
  --detail: 1;
  position: relative;
  height: 560svh; /* one screen of stage + 460svh of descent; the marks above assume this */
}
.mark {
  position: absolute;
  left: 0;
  width: 1px;
  pointer-events: none;
}
.stage {
  position: sticky;
  top: 0;
  display: grid;
  height: 100svh;
  min-height: 620px;
  overflow: hidden;
}
.stage > * {
  grid-area: 1 / 1;
}

.stars {
  background-image:
    radial-gradient(1px 1px at 12% 22%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 31% 64%, #fff 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 47% 12%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 58% 41%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 72% 18%, #fff 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 86% 55%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 93% 9%, #fff 50%, transparent 51%),
    radial-gradient(1px 1px at 6% 78%, #fff 50%, transparent 51%);
  background-size: 620px 460px, 540px 520px, 700px 480px, 480px 610px, 660px 540px, 580px 430px, 720px 590px, 500px 500px;
  opacity: 0.5;
}

.map {
  width: 100%;
  height: 100%;
  -webkit-mask-image: linear-gradient(to right, transparent 4%, #000 50%);
  mask-image: linear-gradient(to right, transparent 4%, #000 50%);
  animation: arrive 1.8s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
@keyframes arrive {
  from {
    opacity: 0;
    transform: scale(0.94);
  }
}
.map path,
.map .sphere {
  vector-effect: non-scaling-stroke;
}
.sphere {
  fill: url(#dh-sphere);
  stroke: rgb(242 239 232 / 0.45);
  stroke-width: 1;
}
.graticule {
  fill: none;
  stroke: rgb(242 239 232 / 0.07);
  stroke-width: 1;
}
.land {
  fill: rgb(242 239 232 / 0.075);
  stroke: rgb(242 239 232 / 0.3);
  stroke-width: 0.7;
}
.country path {
  fill: rgb(255 90 31 / calc(1 - var(--detail)));
  stroke: rgb(242 239 232 / calc(var(--detail) * 0.34));
  stroke-width: 0.8;
}
.country path.home {
  fill: rgb(255 90 31 / calc(1 - var(--detail) * 0.8));
  stroke: rgb(255 90 31 / var(--detail));
}
.dot {
  fill: var(--signal);
}
.pulse {
  fill: none;
  stroke: var(--signal);
  transform-box: fill-box;
  transform-origin: center;
  animation: ping 2.4s ease-out infinite;
}
.pin-label {
  fill: var(--fg);
  font: 400 11px var(--font-mono);
  letter-spacing: 0.06em;
}
@keyframes ping {
  from {
    transform: scale(0.3);
    opacity: 0.9;
  }
  to {
    transform: scale(1.5);
    opacity: 0;
  }
}

.copy {
  z-index: 1;
  align-self: center;
  padding-block: 96px 9svh;
}
h1 {
  margin: 22px 0 0;
  font-size: clamp(52px, 11.4vw, 196px);
  font-weight: 500;
  line-height: 0.9;
  letter-spacing: -0.055em;
}
.line {
  display: block;
  overflow: hidden;
  padding-bottom: 0.08em;
}
.line > span {
  display: inline-block;
}
h1 em {
  font-style: normal;
  color: var(--signal);
}
.below {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  justify-content: space-between;
  gap: 28px 48px;
  margin-top: clamp(28px, 4vw, 52px);
}
.lede {
  max-width: 46ch;
  margin: 0;
  font-size: clamp(17px, 1.35vw, 21px);
  line-height: 1.55;
  color: var(--dim);
}
.cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.hint {
  z-index: 1;
  place-self: end center;
  margin: 0 0 26px;
  font: 400 11px/1 var(--font-mono);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--dim);
}
.hint span {
  display: inline-block;
  color: var(--signal);
  animation: drop 1.6s ease-in-out infinite;
}
@keyframes drop {
  50% {
    transform: translateY(6px);
  }
}

.caps {
  z-index: 1;
  display: grid;
  align-self: end;
  padding-bottom: clamp(36px, 8svh, 96px);
}
/* One grid cell: the three captions sit on top of each other and take turns. */
.cap {
  grid-area: 1 / 1;
  align-self: end;
  max-width: 560px;
}
.scene:not(.is-static) .cap {
  visibility: hidden; /* until the timeline brings each one in */
}
.cap h2 {
  margin: 16px 0 18px;
}
.cap p:not(.kicker) {
  margin: 0;
  font-size: clamp(16px, 1.25vw, 19px);
  line-height: 1.6;
  color: var(--dim);
}
.facts {
  display: grid;
  grid-template-columns: repeat(4, auto);
  justify-content: start;
  gap: 8px 36px;
  margin: 26px 0 0;
}
.facts dt {
  font: 400 10.5px/1.6 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--dim);
}
.facts dd {
  margin: 0;
  font-size: clamp(26px, 2.6vw, 40px);
  font-weight: 500;
  letter-spacing: -0.04em;
}

/* No scroll animation: the title, the map of Nepal and the three captions, one after another. */
.is-static {
  height: auto;
  padding-block: 120px 96px;
}
.is-static .stage {
  position: static;
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: 0;
}
.is-static .stars,
.is-static .hint {
  display: none;
}
.is-static .copy {
  order: -1; /* the map is drawn first so the copy can sit over it; here it reads title, map, captions */
  padding-block: 0 56px;
}
.is-static .caps {
  align-self: auto;
}
.is-static .map {
  height: auto;
  -webkit-mask-image: none;
  mask-image: none;
  animation: none;
}
.is-static .cap {
  grid-area: auto;
  margin-top: 56px;
}

@media (max-width: 760px) {
  .map {
    align-self: start;
    height: 46svh;
    margin-top: 8svh;
    -webkit-mask-image: linear-gradient(to bottom, #000 66%, transparent);
    mask-image: linear-gradient(to bottom, #000 66%, transparent);
  }
  .copy {
    align-self: end;
    padding-bottom: 12svh;
  }
  .facts {
    grid-template-columns: repeat(2, auto);
  }
  .pin-label {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pulse,
  .hint span {
    animation: none;
  }
}
</style>
