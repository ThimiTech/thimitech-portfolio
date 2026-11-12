<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { canAnimate, gsap } from './motion'

const root = ref<HTMLElement | null>(null)
let ctx: gsap.Context | undefined

onMounted(() => {
  if (!canAnimate || !root.value) return
  ctx = gsap.context(() => {
    gsap.from('.line > span', { yPercent: 115, duration: 1.1, ease: 'power4.out', stagger: 0.12, delay: 0.1 })
    gsap.from('.kicker, .lede, .cta, .hint', { autoAlpha: 0, y: 16, duration: 0.8, ease: 'power2.out', stagger: 0.08, delay: 0.7 })
    // Leaving orbit: the planet swells towards the viewer while the title lifts away.
    const scrub = { trigger: root.value, start: 'top top', end: 'bottom top', scrub: true }
    gsap.to('.limb', { scale: 1.55, yPercent: -6, transformOrigin: '50% 100%', ease: 'none', scrollTrigger: scrub })
    gsap.to('.copy', { yPercent: -28, autoAlpha: 0, ease: 'none', scrollTrigger: { ...scrub, end: '70% top' } })
    gsap.to('.stars', { yPercent: 18, ease: 'none', scrollTrigger: scrub })
  }, root.value)
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section id="home" ref="root" class="hero">
    <div class="stars" aria-hidden="true" />
    <svg class="limb" viewBox="0 0 1000 420" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <defs>
        <radialGradient id="dh-atmo" cx="50%" cy="50%" r="50%">
          <stop offset="94%" stop-color="#ff5a1f" stop-opacity="0" />
          <stop offset="98.4%" stop-color="#ff5a1f" stop-opacity="0.42" />
          <stop offset="100%" stop-color="#ff5a1f" stop-opacity="0" />
        </radialGradient>
      </defs>
      <circle cx="500" cy="1290" r="1040" fill="url(#dh-atmo)" />
      <circle cx="500" cy="1290" r="1000" class="planet" />
      <ellipse v-for="rx in [240, 520, 790]" :key="rx" cx="500" cy="1290" :rx="rx" ry="1000" class="graticule" />
      <ellipse v-for="ry in [985, 960, 925]" :key="ry" cx="500" cy="1290" rx="1000" :ry="ry" class="graticule" />
      <path id="dh-orbit" d="M-60 372 Q500 196 1060 372" class="orbit" />
      <g v-if="canAnimate">
        <circle r="3.5" class="sat" />
        <circle r="9" class="sat-ring" />
        <animateMotion dur="16s" repeatCount="indefinite"><mpath href="#dh-orbit" /></animateMotion>
      </g>
    </svg>

    <div class="copy wrap">
      <p class="kicker">Thimi Tech · Web GIS studio · Kathmandu, Nepal</p>
      <h1>
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

    <p class="hint" aria-hidden="true">Scroll to descend <span>↓</span></p>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  display: flex;
  min-height: 100svh;
  align-items: center;
  overflow: hidden;
  padding-block: 120px 28svh;
}

.stars {
  position: absolute;
  inset: -20% 0;
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

.limb {
  position: absolute;
  inset: auto 0 0;
  width: 100%;
  height: 62svh;
  pointer-events: none;
}
.planet {
  fill: #0b1014;
  stroke: rgb(242 239 232 / 0.5);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
}
.graticule {
  fill: none;
  stroke: rgb(242 239 232 / 0.09);
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
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

.copy {
  position: relative;
  z-index: 1;
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
  position: absolute;
  bottom: 26px;
  left: 50%;
  margin: 0;
  translate: -50% 0;
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
@media (prefers-reduced-motion: reduce) {
  .hint span {
    animation: none;
  }
}
</style>
