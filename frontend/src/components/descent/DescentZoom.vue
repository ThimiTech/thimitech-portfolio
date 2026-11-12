<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { geoMercator, geoPath } from 'd3-geo'
import type { Feature, FeatureCollection } from 'geojson'
import { useTeamDirectory } from '../../composables/useTeamDirectory'
import { canAnimate, gsap } from './motion'

// A fixed projection (no fit-to-data) so the home pin is known before the districts load.
const projection = geoMercator().center([84.12, 28.39]).scale(6200).translate([500, 280])
const path = geoPath(projection)
const [px, py] = projection([85.3875, 27.6806]) as [number, number] // Madhyapur Thimi

// Wide screens leave empty map space on the left for the captions.
const viewBox = typeof window.matchMedia === 'function' && window.matchMedia('(min-width: 761px)').matches ? '-330 0 1330 560' : '0 0 1000 560'

const districts = ref<{ name: string; d: string }[]>([])
const root = ref<HTMLElement | null>(null)
const { members, loading } = useTeamDirectory()
const facts = computed(() => [
  { value: '2021', label: 'Founded' },
  { value: loading.value ? '—' : String(members.value.length), label: 'People' },
  { value: '12+', label: 'Platforms shipped' },
  { value: '3', label: 'Live today' },
])
let ctx: gsap.Context | undefined

onMounted(async () => {
  if (canAnimate && root.value) {
    ctx = gsap.context(() => {
      const caps = gsap.utils.toArray<HTMLElement>('.cap')
      const tl = gsap.timeline({
        scrollTrigger: { trigger: root.value, start: 'top top', end: '+=240%', pin: true, scrub: 0.5, refreshPriority: 3 },
      })
      // Zooming about the pin keeps Thimi fixed on screen while the country grows past it.
      tl.fromTo('.country', { scale: 1 }, { scale: 12, svgOrigin: `${px} ${py}`, ease: 'power2.inOut', duration: 2 }, 0.3)
        .to(caps[0]!, { autoAlpha: 0, y: -24, duration: 0.3 }, 0.7)
        .fromTo(caps[1]!, { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.3 }, 1.0)
        .to(caps[1]!, { autoAlpha: 0, y: -24, duration: 0.3 }, 1.8)
        .fromTo(caps[2]!, { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.3 }, 2.1)
        .fromTo('.pin-label', { autoAlpha: 0, x: -8 }, { autoAlpha: 1, x: 0, duration: 0.3 }, 2.1)
        .to({}, { duration: 0.5 })
    }, root.value)
  }
  try {
    const data = (await (await fetch('/nepal-districts.geojson')).json()) as FeatureCollection
    districts.value = data.features.map((f: Feature) => ({ name: String(f.properties?.name ?? ''), d: path(f) ?? '' }))
  } catch {
    /* the pin and the captions still tell the story without the outline */
  }
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section id="about" ref="root" class="zoom" :class="{ 'is-static': !canAnimate }" aria-labelledby="about-title">
    <svg class="map" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Map of Nepal's districts with Thimi marked in the Kathmandu valley">
      <g class="country">
        <path v-for="d in districts" :key="d.name" :d="d.d" :class="{ home: d.name === 'Bhaktapur' }" />
      </g>
      <g :transform="`translate(${px} ${py})`">
        <circle r="16" class="pulse" />
        <circle r="4.5" class="dot" />
        <text x="14" y="4" class="pin-label">Thimi · 27.6806° N, 85.3875° E</text>
      </g>
    </svg>

    <div class="caps wrap">
      <div class="cap">
        <p class="kicker">Altitude 400 km · the country</p>
        <h2 id="about-title">Seventy-seven districts.<br />We map them for a living.</h2>
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
  </section>
</template>

<style scoped>
.zoom {
  position: relative;
  display: flex;
  height: 100svh;
  min-height: 620px;
  align-items: end;
  overflow: hidden;
}

.map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  -webkit-mask-image: linear-gradient(to right, transparent 6%, #000 52%);
  mask-image: linear-gradient(to right, transparent 6%, #000 52%);
}
.country path {
  fill: none;
  stroke: rgb(242 239 232 / 0.34);
  stroke-width: 0.8;
  vector-effect: non-scaling-stroke;
}
.country path.home {
  fill: rgb(255 90 31 / 0.2);
  stroke: var(--signal);
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

.caps {
  position: relative;
  display: grid;
  padding-bottom: clamp(36px, 8svh, 96px);
}
/* One grid cell: the three captions sit on top of each other and cross-fade. */
.cap {
  grid-area: 1 / 1;
  align-self: end;
  max-width: 560px;
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

/* No scroll animation: show the three captions one after another under the map. */
.is-static {
  display: block;
  height: auto;
  padding-block: 96px;
}
.is-static .map {
  position: static;
  height: auto;
  -webkit-mask-image: none;
  mask-image: none;
}
.is-static .cap {
  grid-area: auto;
  margin-top: 56px;
}

@media (max-width: 760px) {
  .map {
    inset: 9svh 0 auto;
    height: 42svh;
    -webkit-mask-image: linear-gradient(to bottom, #000 62%, transparent);
    mask-image: linear-gradient(to bottom, #000 62%, transparent);
  }
  .facts {
    grid-template-columns: repeat(2, auto);
  }
  .pin-label {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pulse {
    animation: none;
  }
}
</style>
