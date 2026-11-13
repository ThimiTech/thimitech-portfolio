<script setup lang="ts">
/** The page ends back in the dark: a last call, the site map (profile and recent work from the backend), and the name at full width. */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { canAnimate, gsap } from './motion'
import { useSite } from './site'

const { site, cases } = useSite()
const year = new Date().getFullYear()
const root = ref<HTMLElement | null>(null)
const spot = ref<SVGRadialGradientElement | null>(null)
const clock = ref('')
let ctx: gsap.Context | undefined
let timer: ReturnType<typeof setInterval> | undefined

const socials = computed(() =>
  ([['GitHub', site.value.github], ['LinkedIn', site.value.linkedin], ['YouTube', site.value.youtube], ['Website', site.value.website]] as const).filter(([, url]) => url),
)
const tick = () => (clock.value = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kathmandu' }).format(new Date()))

/** The lit patch on the wordmark follows the pointer. */
function light(e: PointerEvent) {
  const box = (e.currentTarget as SVGElement).getBoundingClientRect()
  spot.value?.setAttribute('cx', String(((e.clientX - box.left) / box.width) * 1000))
}
const ascend = () => window.scrollTo({ top: 0, behavior: canAnimate ? 'smooth' : 'auto' })

onMounted(() => {
  tick()
  timer = setInterval(tick, 30_000)
  if (!canAnimate || !root.value) return
  ctx = gsap.context(() => {
    gsap.from('.wordmark text', {
      y: 130,
      ease: 'none',
      scrollTrigger: { trigger: '.wordmark', start: 'top bottom', end: 'bottom bottom', scrub: 0.6 },
    })
  }, root.value)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  ctx?.revert()
})
</script>

<template>
  <footer ref="root" class="foot night">
    <div class="wrap">
      <div class="call">
        <p class="kicker">Next waypoint</p>
        <p class="big">Somewhere on your map<br />is a problem <em>worth solving.</em></p>
        <div class="cta">
          <RouterLink to="/new#contact" class="btn btn-solid">Start a project <span aria-hidden="true">→</span></RouterLink>
          <a :href="`mailto:${site.email}`" class="btn">{{ site.email }}</a>
        </div>
      </div>

      <div class="cols">
        <div class="brand">
          <p class="name">{{ site.name }}</p>
          <p>{{ site.tagline }}</p>
          <p class="where">
            <span>{{ site.address }}</span>
            <span>27.6806° N · 85.3875° E</span>
            <span v-if="clock"><i aria-hidden="true" /> {{ clock }} in Thimi (GMT +5:45)</span>
          </p>
        </div>
        <nav aria-label="Footer">
          <p class="label">Explore</p>
          <RouterLink to="/new#services">Services</RouterLink>
          <RouterLink to="/new#projects">Work</RouterLink>
          <RouterLink to="/new#mission">Founder’s note</RouterLink>
          <RouterLink to="/new#hiring">Careers</RouterLink>
          <RouterLink to="/new#contact">Contact</RouterLink>
        </nav>
        <nav aria-label="Recent work">
          <p class="label">Recent work</p>
          <RouterLink v-for="c in cases.slice(0, 4)" :key="c.slug" :to="`/work/${c.slug}`">{{ c.name }}</RouterLink>
          <RouterLink to="/work">All case studies <span aria-hidden="true">→</span></RouterLink>
        </nav>
        <div class="reach">
          <p class="label">Reach us</p>
          <a :href="`mailto:${site.email}`">{{ site.email }}</a>
          <a v-if="site.phone" :href="`tel:${site.phone.replace(/\s+/g, '')}`">{{ site.phone }}</a>
          <a v-for="[name, url] in socials" :key="name" :href="url" target="_blank" rel="noopener">{{ name }} <span aria-hidden="true">↗</span></a>
        </div>
      </div>
    </div>

    <!-- Back in orbit: the satellite from the first screen passes over the name. -->
    <svg class="wordmark" viewBox="0 0 1000 250" aria-hidden="true" @pointermove="light">
      <defs>
        <linearGradient id="df-fade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0.25" stop-color="#f2efe8" stop-opacity="0.9" />
          <stop offset="1" stop-color="#f2efe8" stop-opacity="0.04" />
        </linearGradient>
        <radialGradient id="df-spot" ref="spot" gradientUnits="userSpaceOnUse" cx="760" cy="170" r="240">
          <stop offset="0" stop-color="#ff5a1f" />
          <stop offset="1" stop-color="#ff5a1f" stop-opacity="0" />
        </radialGradient>
        <clipPath id="df-clip"><rect width="1000" height="250" /></clipPath>
      </defs>
      <path id="df-orbit" d="M-40 96 Q500 -34 1040 96" class="orbit" />
      <g v-if="canAnimate">
        <circle r="3.5" class="sat" />
        <circle r="9" class="sat-ring" />
        <animateMotion dur="18s" repeatCount="indefinite"><mpath href="#df-orbit" /></animateMotion>
      </g>
      <g clip-path="url(#df-clip)">
        <text x="0" y="238" textLength="1000" lengthAdjust="spacingAndGlyphs" fill="url(#df-fade)">THIMI TECH</text>
        <text x="0" y="238" textLength="1000" lengthAdjust="spacingAndGlyphs" fill="url(#df-spot)">THIMI TECH</text>
      </g>
    </svg>

    <div class="wrap legal">
      <p>© {{ year }} {{ site.name }} · Built in Thimi, Nepal</p>
      <p>
        <RouterLink to="/work">Case studies</RouterLink>
        <RouterLink to="/">Classic site</RouterLink>
        <button type="button" @click="ascend">Ascend <span aria-hidden="true">↑</span></button>
      </p>
    </div>
  </footer>
</template>

<style scoped>
.foot {
  position: relative;
  overflow: hidden;
  padding-top: clamp(80px, 11vw, 160px);
  background:
    radial-gradient(60% 46% at 76% 100%, rgb(255 90 31 / 0.2), transparent 70%),
    linear-gradient(var(--line) 1px, transparent 1px) 0 0 / 100% 88px,
    linear-gradient(90deg, var(--line) 1px, transparent 1px) 0 0 / 88px 100%,
    var(--bg);
}
/* the survey grid thins out towards the top */
.foot::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(var(--bg) 0%, transparent 85%);
  pointer-events: none;
}
.foot > * {
  position: relative;
}

.big {
  margin: 18px 0 0;
  font-size: clamp(38px, 6.4vw, 108px);
  font-weight: 500;
  line-height: 0.98;
  letter-spacing: -0.05em;
  text-wrap: balance;
}
.big em {
  font-style: normal;
  color: var(--signal);
}
.cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: clamp(26px, 3.4vw, 48px);
}

.cols {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) repeat(3, minmax(0, 1fr));
  gap: 40px clamp(20px, 3vw, 56px);
  margin-top: clamp(64px, 9vw, 130px);
  padding-top: 36px;
  border-top: 1px solid var(--line-strong);
}
.cols p {
  margin: 0;
}
.brand {
  display: grid;
  align-content: start;
  gap: 12px;
  max-width: 36ch;
  line-height: 1.55;
  color: var(--dim);
}
.name {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--fg);
}
.where {
  display: grid;
  gap: 4px;
  margin-top: 8px;
  font: 400 11.5px/1.6 var(--font-mono);
  letter-spacing: 0.06em;
}
.where i {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--signal);
  animation: beat 2s ease-in-out infinite;
}
@keyframes beat {
  50% {
    opacity: 0.25;
  }
}
.cols nav,
.reach {
  display: grid;
  align-content: start;
  justify-items: start;
  gap: 10px;
}
.label {
  margin-bottom: 8px;
  font: 400 10.5px/1.6 var(--font-mono);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--dim);
}
.cols a {
  font-size: 17px;
  color: var(--fg);
  text-decoration: none;
  overflow-wrap: anywhere;
  background: linear-gradient(var(--signal), var(--signal)) 0 100% / 0 1px no-repeat;
  transition: background-size 0.3s ease, color 0.3s ease;
}
.cols a:hover {
  background-size: 100% 1px;
  color: var(--signal);
}

.wordmark {
  display: block;
  width: var(--wrap);
  margin: clamp(40px, 6vw, 90px) auto 0;
  overflow: visible;
}
.wordmark text {
  font: 600 200px/1 var(--font-body);
  letter-spacing: -0.04em;
}
.orbit {
  fill: none;
  stroke: rgb(242 239 232 / 0.28);
  stroke-width: 1;
  stroke-dasharray: 2 7;
  vector-effect: non-scaling-stroke;
}
.sat {
  fill: var(--signal);
}
.sat-ring {
  fill: none;
  stroke: var(--signal);
  stroke-opacity: 0.5;
}

.legal {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px 32px;
  padding-block: 22px 30px;
  border-top: 1px solid var(--line);
  font: 400 11.5px/1.6 var(--font-mono);
  letter-spacing: 0.08em;
  color: var(--dim);
}
.legal p {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  margin: 0;
}
.legal a,
.legal button {
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  letter-spacing: inherit;
  color: var(--fg);
  cursor: pointer;
}
.legal button span {
  display: inline-block;
  color: var(--signal);
  transition: transform 0.3s ease;
}
.legal button:hover span {
  transform: translateY(-4px);
}

@media (max-width: 860px) {
  .cols {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .brand {
    grid-column: 1 / -1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .where i {
    animation: none;
  }
}
</style>
