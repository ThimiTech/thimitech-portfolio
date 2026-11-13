<script setup lang="ts">
/**
 * /new — "The descent". The page is one continuous zoom: it opens in orbit and ends at
 * street level in Thimi. Scroll position is altitude; the instrument on the right reads it out,
 * and the page goes from night to daylight on the way down.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuth } from '../stores/auth'
import { canAnimate, gsap, ScrollTrigger } from '../components/descent/motion'
import DescentHero from '../components/descent/DescentHero.vue'
import DescentLayers from '../components/descent/DescentLayers.vue'
import DescentWork from '../components/descent/DescentWork.vue'
import DescentGround from '../components/descent/DescentGround.vue'
import DescentContact from '../components/descent/DescentContact.vue'
import DescentFooter from '../components/descent/DescentFooter.vue'

const { isLoggedIn, user, fetchMe, hasRole } = useAuth()

// [element id, band name, altitude in metres where it starts]; each band ends at the next one's altitude.
// The first four are marks inside the opening scene (DescentHero); the rest are sections.
const BANDS = [
  ['home', 'Orbit', 705_000],
  ['about', 'Country', 400_000],
  ['valley', 'Valley', 12_000],
  ['thimi', 'Thimi', 1326],
  ['services', 'Layers', 600],
  ['projects', 'Field notes', 120],
  ['mission', 'Founder’s note', 30],
  ['hiring', 'Open roles', 2],
  ['contact', 'Street level', 1],
] as const
const HOME = [27.6806, 85.3875] // Madhyapur Thimi
const FAR = [28.3949, 84.124] // centre of Nepal

const root = ref<HTMLElement | null>(null)
const progress = ref(0)
const at = ref({ i: 0, t: 0 }) // which section is at mid-screen, and how far through it (0..1)

/** Find the section under the middle of the screen. A pinned section is measured by its spacer. */
function locate() {
  const mid = window.innerHeight / 2
  for (let i = BANDS.length - 1; i >= 0; i--) {
    const el = document.getElementById(BANDS[i]![0])
    const box = (el?.parentElement?.classList.contains('pin-spacer') ? el.parentElement : el)?.getBoundingClientRect()
    // The page opens on the first band, so that one is measured from the top of the screen and starts at 0.
    const from = i ? mid : 0
    if (box && box.top <= from) return void (at.value = { i, t: Math.min(1, (from - box.top) / (box.height - mid + from)) })
  }
}

const band = computed(() => BANDS[at.value.i]![1])
const metres = computed(() => {
  const { i, t } = at.value
  const from = BANDS[i]![2]
  const to = BANDS[i + 1]?.[2]
  return to ? from * (to / from) ** t : from * (1 - t) // log scale on the way down, straight to zero at the end
})
const altitude = computed(() => {
  const m = metres.value
  if (m >= 10_000) return `${Math.round(m / 1000)} km`
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`
  return `${m < 10 ? m.toFixed(1) : Math.round(m)} m`
})
const zoom = computed(() => String(Math.round(19 - (17 * Math.log(Math.max(1, metres.value))) / Math.log(705_000))).padStart(2, '0'))
const fix = computed(() => {
  // far away in orbit, homing in while the map zooms, on Thimi from then on
  const t = at.value.i === 0 ? 0 : at.value.i === 1 ? Math.min(1, at.value.t / 0.7) : 1
  const [lat, lon] = [0, 1].map((k) => FAR[k]! + (HOME[k]! - FAR[k]!) * t)
  return `${lat!.toFixed(4)}° N  ${lon!.toFixed(4)}° E`
})

let ctx: gsap.Context | undefined
let observer: ResizeObserver | undefined
let settle: ReturnType<typeof setTimeout> | undefined

onMounted(() => {
  if (isLoggedIn.value && !user.value) fetchMe()
  if (!canAnimate || !root.value) return
  ctx = gsap.context(() => {
    ScrollTrigger.create({
      start: 0,
      end: 'max',
      onUpdate: (self) => {
        progress.value = self.progress
        locate()
      },
    })
    // Daybreak: one number drives every colour on the page (see --bg / --fg below).
    gsap.fromTo(root.value, { '--day': 0 }, {
      '--day': 1,
      ease: 'none',
      scrollTrigger: { trigger: '#mission', start: 'top 88%', end: 'top 30%', scrub: true },
    })
    // The footer is night again, so the bar over it is too.
    ScrollTrigger.create({ trigger: '.foot', start: 'top 64px', toggleClass: { targets: '.bar', className: 'night' } })
  }, root.value)
  // Projects, people and roles load after first paint and change the page height.
  observer = new ResizeObserver(() => {
    clearTimeout(settle)
    settle = setTimeout(() => ScrollTrigger.refresh(), 200)
  })
  observer.observe(root.value)
})
onBeforeUnmount(() => {
  clearTimeout(settle)
  observer?.disconnect()
  ctx?.revert()
})
</script>

<template>
  <div ref="root" class="descent" :class="{ 'is-static': !canAnimate }">
    <a href="#main-content" class="skip">Skip to content</a>

    <header class="bar">
      <RouterLink to="/new#home" class="brand">Thimi Tech</RouterLink>
      <nav aria-label="Sections">
        <RouterLink to="/new#services">Services</RouterLink>
        <RouterLink to="/new#projects">Work</RouterLink>
        <RouterLink to="/new#mission">Founder</RouterLink>
        <RouterLink to="/new#hiring">Careers</RouterLink>
        <RouterLink to="/new#contact">Contact</RouterLink>
      </nav>
      <RouterLink v-if="hasRole('employee')" to="/app" class="enter">Workspace →</RouterLink>
      <RouterLink v-else-if="!isLoggedIn" to="/login" class="enter">Sign in</RouterLink>
    </header>

    <!-- The altimeter. Decorative: the same information is in each section's heading. -->
    <aside v-if="canAnimate" class="hud" aria-hidden="true">
      <div class="rail"><span class="mark" :style="{ top: `${progress * 100}%` }" /></div>
      <dl>
        <div><dt>Alt</dt><dd>{{ altitude }}</dd></div>
        <div><dt>Zoom</dt><dd>z{{ zoom }}</dd></div>
        <div class="wide"><dt>Fix</dt><dd>{{ fix }}</dd></div>
        <div class="wide"><dt>Band</dt><dd>{{ band }}</dd></div>
      </dl>
    </aside>

    <main id="main-content">
      <DescentHero />
      <DescentLayers />
      <DescentWork />
      <DescentGround />
      <DescentContact />
    </main>

    <DescentFooter />
  </div>
</template>

<style>
/* Unscoped on purpose: the section components share these tokens. Everything is namespaced under .descent. */
.descent,
.descent .daylight,
.descent .night {
  --night: #06080a;
  --paper: #f3f0e9;
  --signal: #ff5a1f;
  --bg: color-mix(in oklab, var(--paper) calc(var(--day) * 100%), var(--night));
  --fg: color-mix(in oklab, #0b0d0f calc(var(--day) * 100%), #f2efe8);
  --dim: color-mix(in oklab, var(--fg) 62%, var(--bg));
  --line: color-mix(in oklab, var(--fg) 16%, var(--bg));
  --line-strong: color-mix(in oklab, var(--fg) 38%, var(--bg));
}
.descent {
  --day: 0;
  --wrap: min(100vw - 48px, 1320px);
  background: var(--bg);
  color: var(--fg);
  font-family: var(--font-body);
  overflow-x: clip;
}
/* Without scroll animation there is no daybreak tween: the lower sections are simply light. */
.descent.is-static .daylight {
  --day: 1;
}
/* The footer is night again whatever the time of day above it. */
.descent .night {
  --day: 0;
}
.descent section,
.descent .foot {
  background: var(--bg);
  color: var(--fg);
}

.descent .wrap {
  width: var(--wrap);
  margin-inline: auto;
}
/* Wide screens: keep the text column clear of the altimeter on the right edge. */
@media (min-width: 1101px) {
  .descent:not(.is-static) {
    --wrap: min(100vw - 340px, 1320px);
  }
}
.descent h2 {
  font-size: clamp(38px, 5.6vw, 92px);
  font-weight: 500;
  line-height: 0.98;
  letter-spacing: -0.05em;
  text-wrap: balance;
}
.descent .kicker {
  margin: 0;
  font: 400 11px/1.6 var(--font-mono);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--dim);
}
.descent .kicker::before {
  content: '';
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 10px;
  border-radius: 50%;
  background: var(--signal);
}
.descent .btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 15px 26px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: none;
  font: 500 15px/1 var(--font-body);
  color: var(--fg);
  text-decoration: none;
  cursor: pointer;
  transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}
.descent .btn:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: #0a0a0a;
}
.descent .btn-solid {
  border-color: var(--fg);
  background: var(--fg);
  color: var(--bg);
}
.descent .btn:disabled {
  opacity: 0.5;
  cursor: progress;
}
.descent :focus-visible {
  outline: 2px solid var(--signal);
  outline-offset: 3px;
}
.descent .sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.descent .skip {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 60;
  padding: 10px 14px;
  background: var(--signal);
  color: #0a0a0a;
  transform: translateY(-200%);
}
.descent .skip:focus {
  transform: none;
}

/* The bar takes the page colour (night, then day) so text scrolling under it stays readable. */
.descent .bar {
  position: fixed;
  inset: 0 0 auto;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 16px calc((100vw - var(--wrap)) / 2);
  background: color-mix(in oklab, var(--bg) 78%, transparent);
  backdrop-filter: blur(14px);
  font-size: 14.5px;
  color: var(--fg);
  transition: background-color 0.3s ease, color 0.3s ease;
}
.descent .bar a {
  color: inherit;
  text-decoration: none;
}
.descent .bar .brand {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.03em;
}
.descent .bar nav {
  display: flex;
  gap: 26px;
  margin-left: auto;
}
.descent .bar nav a {
  opacity: 0.72;
  transition: opacity 0.2s ease;
}
.descent .bar nav a:hover {
  opacity: 1;
}
.descent .bar .enter {
  padding: 9px 16px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
}
.descent .bar .enter:hover {
  background: var(--fg);
  color: var(--bg);
}

/* The altimeter floats over night and day sections alike; `difference` keeps it legible on both. */
.descent .hud {
  position: fixed;
  z-index: 50;
  color: #fff;
  mix-blend-mode: difference;
  top: 50%;
  right: 22px;
  display: flex;
  gap: 14px;
  translate: 0 -50%;
  pointer-events: none;
  font: 400 10.5px/1.5 var(--font-mono);
  letter-spacing: 0.1em;
}
.descent .hud .rail {
  position: relative;
  width: 9px;
  height: 34svh;
  background: repeating-linear-gradient(to bottom, currentColor 0 1px, transparent 1px 12px);
  opacity: 0.55;
}
.descent .hud .mark {
  position: absolute;
  left: -5px;
  width: 19px;
  height: 2px;
  background: currentColor;
}
.descent .hud dl {
  display: grid;
  width: 108px;
  align-content: center;
  gap: 10px;
  margin: 0;
}
.descent .hud dt {
  text-transform: uppercase;
  opacity: 0.55;
}
.descent .hud dd {
  margin: 0;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1100px) {
  /* Compact altimeter: one line, bottom-left */
  .descent .hud {
    inset: auto auto 14px 16px;
    translate: none;
  }
  .descent .hud .rail,
  .descent .hud .wide {
    display: none;
  }
  .descent .hud dl {
    display: flex;
    width: auto;
    gap: 14px;
  }
  .descent .hud dl > div {
    display: flex;
    gap: 6px;
  }
}
@media (max-width: 760px) {
  .descent .bar nav a:not(:last-child),
  .descent .hud {
    display: none;
  }
}
</style>
