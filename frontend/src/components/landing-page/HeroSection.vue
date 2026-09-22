<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import WaterRipple from './WaterRipple.vue'

interface TitleChar {
  char: string
  delay: number
}

interface MagneticItem {
  el: HTMLElement
  strength: number
  rect: DOMRect | null
  targetX: number
  targetY: number
  currentX: number
  currentY: number
}

const trustedBy = ['ICIMOD', 'APEC', 'Bagmati Pradesh']

const factsLine = 'Kathmandu-based · Est. 2021'

const TITLE_CHAR_BASE_DELAY = 0.4
const TITLE_CHAR_STEP = 0.06

function splitTitleLine(line: string, offset: number): TitleChar[] {
  return Array.from(line, (char, index) => ({
    char: char === ' ' ? '\u00a0' : char,
    delay: TITLE_CHAR_BASE_DELAY + (offset + index) * TITLE_CHAR_STEP,
  }))
}

const titleLineOne = splitTitleLine('we map', 0)
const titleLineTwo = splitTitleLine('what matters.', 'we map'.length)

const RING_LERP = 0.22
const PARALLAX_LERP = 0.09
const MAGNETIC_LERP = 0.18
const PARALLAX_MAX = 6
const RING_EPSILON = 0.1
const PARALLAX_EPSILON = 0.02
const MAGNETIC_EPSILON = 0.05

const sectionEl = ref<HTMLElement | null>(null)
const parallaxEl = ref<HTMLElement | null>(null)
const cursorDotEl = ref<HTMLElement | null>(null)
const cursorRingEl = ref<HTMLElement | null>(null)

const cursorEnabled = ref(false)
const cursorActive = ref(false)
const cursorHover = ref(false)

let reducedMotion = false
let finePointer = false
let pointerInside = false
let inViewport = true

let rafId = 0
let loopRunning = false
let rectsDirty = false

let heroRect: DOMRect | null = null
let pointerX = 0
let pointerY = 0
let dotX = 0
let dotY = 0
let ringX = 0
let ringY = 0
let parallaxX = 0
let parallaxY = 0
let parallaxTargetX = 0
let parallaxTargetY = 0
let parallaxWrittenX = 0
let parallaxWrittenY = 0

const magneticItems: MagneticItem[] = []
const cleanups: Array<() => void> = []

let intersectionObserver: IntersectionObserver | null = null

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function track<E extends Event>(
  target: EventTarget,
  type: string,
  handler: (event: E) => void,
  options?: AddEventListenerOptions,
): void {
  const listener = handler as EventListener
  target.addEventListener(type, listener, options)
  cleanups.push(() => target.removeEventListener(type, listener, options))
}

function writeCursor(): void {
  const dot = cursorDotEl.value
  if (dot) {
    dot.style.transform = `translate3d(${dotX.toFixed(2)}px, ${dotY.toFixed(2)}px, 0) translate(-50%, -50%)`
  }
  const ring = cursorRingEl.value
  if (ring) {
    ring.style.transform = `translate3d(${ringX.toFixed(2)}px, ${ringY.toFixed(2)}px, 0) translate(-50%, -50%)`
  }
}

function writeParallax(): void {
  const el = parallaxEl.value
  if (!el) return
  if (Math.abs(parallaxX - parallaxWrittenX) < 0.01 && Math.abs(parallaxY - parallaxWrittenY) < 0.01) return
  parallaxWrittenX = parallaxX
  parallaxWrittenY = parallaxY
  el.style.transform = `translate3d(${parallaxX.toFixed(2)}px, ${parallaxY.toFixed(2)}px, 0)`
}

function updateParallaxTarget(): void {
  if (!heroRect || heroRect.width === 0 || heroRect.height === 0) return
  const nx = clamp(((pointerX - heroRect.left) / heroRect.width) * 2 - 1, -1, 1)
  const ny = clamp(((pointerY - heroRect.top) / heroRect.height) * 2 - 1, -1, 1)
  parallaxTargetX = nx * -PARALLAX_MAX
  parallaxTargetY = ny * -PARALLAX_MAX
}

function measure(): void {
  const section = sectionEl.value
  if (!section) return
  heroRect = section.getBoundingClientRect()
  for (const item of magneticItems) {
    if (!item.rect) continue
    item.rect = item.el.getBoundingClientRect()
  }
  updateParallaxTarget()
}

function stepCursor(): void {
  if (!cursorActive.value) return
  dotX = pointerX
  dotY = pointerY
  if (Math.abs(dotX - ringX) < RING_EPSILON && Math.abs(dotY - ringY) < RING_EPSILON) {
    ringX = dotX
    ringY = dotY
  } else {
    ringX += (dotX - ringX) * RING_LERP
    ringY += (dotY - ringY) * RING_LERP
  }
  writeCursor()
}

function stepParallax(): void {
  if (Math.abs(parallaxTargetX - parallaxX) < PARALLAX_EPSILON && Math.abs(parallaxTargetY - parallaxY) < PARALLAX_EPSILON) {
    parallaxX = parallaxTargetX
    parallaxY = parallaxTargetY
  } else {
    parallaxX += (parallaxTargetX - parallaxX) * PARALLAX_LERP
    parallaxY += (parallaxTargetY - parallaxY) * PARALLAX_LERP
  }
  writeParallax()
}

function stepMagnetic(): void {
  for (const item of magneticItems) {
    if (!item.rect) continue
    const settledX = Math.abs(item.targetX - item.currentX) < MAGNETIC_EPSILON
    const settledY = Math.abs(item.targetY - item.currentY) < MAGNETIC_EPSILON
    if (settledX && settledY) {
      item.currentX = item.targetX
      item.currentY = item.targetY
    } else {
      item.currentX += (item.targetX - item.currentX) * MAGNETIC_LERP
      item.currentY += (item.targetY - item.currentY) * MAGNETIC_LERP
    }
    if (item.targetX === 0 && item.targetY === 0 && item.currentX === 0 && item.currentY === 0) {
      item.el.style.transform = ''
      item.rect = null
      continue
    }
    item.el.style.transform = `translate3d(${item.currentX.toFixed(2)}px, ${item.currentY.toFixed(2)}px, 0)`
  }
}

function needsAnimation(): boolean {
  if (Math.abs(parallaxTargetX - parallaxX) > PARALLAX_EPSILON || Math.abs(parallaxTargetY - parallaxY) > PARALLAX_EPSILON) {
    return true
  }
  if (cursorActive.value && (Math.abs(dotX - ringX) > RING_EPSILON || Math.abs(dotY - ringY) > RING_EPSILON)) {
    return true
  }
  for (const item of magneticItems) {
    if (Math.abs(item.targetX - item.currentX) > MAGNETIC_EPSILON || Math.abs(item.targetY - item.currentY) > MAGNETIC_EPSILON) {
      return true
    }
  }
  return false
}

function stopLoop(): void {
  loopRunning = false
  if (rafId !== 0) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
}

function startLoop(): void {
  if (loopRunning || !finePointer || reducedMotion || !inViewport || document.hidden) return
  loopRunning = true
  rafId = requestAnimationFrame(animate)
}

function animate(): void {
  rafId = 0
  if (!loopRunning) return

  if (rectsDirty) {
    measure()
    rectsDirty = false
  }

  stepCursor()
  stepParallax()
  stepMagnetic()

  if (!needsAnimation()) {
    stopLoop()
    return
  }
  rafId = requestAnimationFrame(animate)
}

function syncCursorState(): void {
  cursorActive.value = cursorEnabled.value && pointerInside && inViewport && !document.hidden
}

function releasePointer(): void {
  pointerInside = false
  cursorHover.value = false
  parallaxTargetX = 0
  parallaxTargetY = 0
  for (const item of magneticItems) {
    item.targetX = 0
    item.targetY = 0
  }
  syncCursorState()
  startLoop()
}

function onPointerEnter(event: PointerEvent): void {
  pointerInside = true
  pointerX = event.clientX
  pointerY = event.clientY
  dotX = pointerX
  dotY = pointerY
  ringX = pointerX
  ringY = pointerY
  rectsDirty = true
  syncCursorState()
  writeCursor()
  startLoop()
}

function onPointerMove(event: PointerEvent): void {
  pointerX = event.clientX
  pointerY = event.clientY
  if (heroRect === null) rectsDirty = true
  updateParallaxTarget()
  startLoop()
}

function onPointerLeave(): void {
  releasePointer()
}

function onWindowBlur(): void {
  releasePointer()
}

function onResize(): void {
  rectsDirty = true
  startLoop()
}

function onScroll(): void {
  rectsDirty = true
  startLoop()
}

function onVisibilityChange(): void {
  syncCursorState()
  if (inViewport && !document.hidden) startLoop()
  else stopLoop()
}

function bindHoverTargets(): void {
  const section = sectionEl.value
  if (!section) return
  for (const el of section.querySelectorAll<HTMLElement>('a, button, [data-magnetic], .hero-badge')) {
    track<PointerEvent>(el, 'pointerenter', () => {
      cursorHover.value = true
    })
    track<PointerEvent>(el, 'pointerleave', () => {
      cursorHover.value = false
    })
  }
}

function bindMagneticItems(): void {
  const section = sectionEl.value
  if (!section) return
  for (const el of section.querySelectorAll<HTMLElement>('[data-magnetic]')) {
    const item: MagneticItem = {
      el,
      strength: el.classList.contains('hero-btn') ? 0.35 : 0.15,
      rect: null,
      targetX: 0,
      targetY: 0,
      currentX: 0,
      currentY: 0,
    }
    magneticItems.push(item)

    track<PointerEvent>(el, 'pointerenter', () => {
      item.rect = el.getBoundingClientRect()
    })
    track<PointerEvent>(
      el,
      'pointermove',
      (event) => {
        if (!item.rect) return
        item.targetX = (event.clientX - item.rect.left - item.rect.width / 2) * item.strength
        item.targetY = (event.clientY - item.rect.top - item.rect.height / 2) * item.strength
        startLoop()
      },
      { passive: true },
    )
    track<PointerEvent>(el, 'pointerleave', () => {
      item.targetX = 0
      item.targetY = 0
      startLoop()
    })
  }
}

onMounted(() => {
  const section = sectionEl.value
  if (!section) return

  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  finePointer = !reducedMotion && window.matchMedia('(hover: hover) and (pointer: fine)').matches

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      inViewport = entry ? entry.isIntersecting : true
      syncCursorState()
      if (inViewport) startLoop()
      else stopLoop()
    },
    { threshold: 0 },
  )
  intersectionObserver.observe(section)

  track<Event>(document, 'visibilitychange', onVisibilityChange)
  track<Event>(window, 'resize', onResize, { passive: true })
  track<Event>(window, 'scroll', onScroll, { passive: true })
  track<Event>(window, 'blur', onWindowBlur)

  if (!finePointer) return

  cursorEnabled.value = true

  track<PointerEvent>(section, 'pointerenter', onPointerEnter)
  track<PointerEvent>(section, 'pointermove', onPointerMove, { passive: true })
  track<PointerEvent>(section, 'pointerleave', onPointerLeave)
  track<PointerEvent>(section, 'pointercancel', onPointerLeave)

  bindHoverTargets()
  bindMagneticItems()
})

onBeforeUnmount(() => {
  stopLoop()
  intersectionObserver?.disconnect()
  intersectionObserver = null
  for (const cleanup of cleanups) cleanup()
  cleanups.length = 0
  magneticItems.length = 0
})
</script>

<template>
  <section
    id="home"
    ref="sectionEl"
    class="hero-section isolate overflow-hidden relative flex w-full flex-col min-h-[100vh] min-h-[100svh]"
    :class="{ 'is-fine-pointer': cursorEnabled, 'is-cursor-active': cursorActive }"
  >
    <WaterRipple deep-color="#2f5a7d" mid-color="#5c8fb2" crest-color="#b3d7e8" glow-color="#eef8ff" />

    <div class="hero-glow pointer-events-none absolute inset-0 z-[1]" aria-hidden="true"></div>
    <div class="hero-scrim pointer-events-none absolute inset-0 z-[2]" aria-hidden="true"></div>
    <div class="hero-vignette pointer-events-none absolute inset-0 z-[2]" aria-hidden="true"></div>
    <div class="hero-center-darken pointer-events-none absolute inset-0 z-[3]" aria-hidden="true"></div>

    <div ref="cursorDotEl" class="hero-cursor-dot" :class="{ 'is-hover': cursorHover }" aria-hidden="true"></div>
    <div ref="cursorRingEl" class="hero-cursor-ring" :class="{ 'is-hover': cursorHover }" aria-hidden="true"></div>

    <div class="relative z-10 flex grow items-center justify-center px-6 lg:px-16">
      <div ref="parallaxEl" class="hero-parallax mx-auto flex w-full max-w-[1200px] flex-1 flex-col justify-center pb-10 text-center">
        <div class="hero-reveal mb-6 flex justify-center" style="animation-delay: 0.05s">
          <span class="hero-badge">AI • Geospatial • Data • Digital Innovation</span>
        </div>

        <p class="hero-reveal hero-serif hero-serif-line mb-3" style="animation-delay: 0.25s">
          From terrain to <span class="hero-serif-accent">insight</span>,
        </p>

        <h1 class="hero-title mb-7">
          <span class="sr-only">we map what matters.</span>
          <span class="block" aria-hidden="true">
            <span
              v-for="(item, index) in titleLineOne"
              :key="`line-one-${index}-${item.char}`"
              class="hero-reveal-char"
              :style="{ animationDelay: `${item.delay}s` }"
              >{{ item.char }}</span
            >
          </span>
          <span class="block" aria-hidden="true">
            <span
              v-for="(item, index) in titleLineTwo"
              :key="`line-two-${index}-${item.char}`"
              class="hero-reveal-char"
              :style="{ animationDelay: `${item.delay}s` }"
              >{{ item.char }}</span
            >
          </span>
        </h1>

        <p class="hero-reveal hero-serif hero-serif-line mb-8" style="animation-delay: 1.4s">
          so you can <span class="hero-serif-accent">decide</span>.
        </p>

        <div class="hero-reveal flex justify-center" style="animation-delay: 1.7s">
          <a href="#projects" data-magnetic class="hero-btn hero-btn-primary">
            <span class="hero-btn-fill" aria-hidden="true"></span>
            <span class="hero-btn-label">Explore More</span>
            <svg
              class="hero-btn-arrow"
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>

        <p class="hero-reveal hero-facts mt-6" style="animation-delay: 1.9s">{{ factsLine }}</p>

        <div class="hero-reveal mt-10 w-full max-w-[920px] self-center" style="animation-delay: 2.05s">
          <p class="hero-label">Trusted by</p>
          <ul class="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 sm:gap-x-10 sm:gap-y-3">
            <li v-for="org in trustedBy" :key="org" class="hero-trusted-item">{{ org }}</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero-section {
  --hero-bg: #35566f;
  --hero-fg: #ffffff;
  --hero-muted: rgba(255, 255, 255, 0.72);
  --hero-accent: #ffd9a0;
  --hero-border: rgba(255, 255, 255, 0.16);
  --hero-nav-height: 80px;

  background-color: var(--hero-bg);
  color: var(--hero-fg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.hero-section.is-cursor-active,
.hero-section.is-cursor-active * {
  cursor: none;
}

.hero-section :focus-visible {
  outline: 2px solid var(--hero-accent);
  outline-offset: 3px;
}

.hero-glow {
  background:
    radial-gradient(62% 46% at 50% -6%, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(92% 72% at 50% 112%, rgba(210, 238, 255, 0.18) 0%, rgba(210, 238, 255, 0) 72%);
}

.hero-scrim {
  background: linear-gradient(180deg, rgba(16, 38, 60, 0.5) 0%, rgba(16, 38, 60, 0.14) 18%, rgba(16, 38, 60, 0) 36%);
}

.hero-vignette {
  background: radial-gradient(ellipse at center, transparent 64%, rgba(24, 52, 78, 0.34) 100%);
}

.hero-center-darken {
  background: radial-gradient(
    ellipse 78% 66% at center,
    rgba(22, 48, 74, 0.34) 0%,
    rgba(22, 48, 74, 0.16) 34%,
    rgba(22, 48, 74, 0.05) 64%,
    transparent 88%
  );
}

.hero-parallax {
  padding-top: max(6rem, calc(var(--hero-nav-height) + env(safe-area-inset-top, 0px) + 2rem));
  will-change: transform;
}

.hero-cursor-dot,
.hero-cursor-ring {
  position: fixed;
  top: 0;
  left: 0;
  display: none;
  border-radius: 50%;
  pointer-events: none;
  mix-blend-mode: screen;
  will-change: transform;
}

.hero-section.is-fine-pointer.is-cursor-active .hero-cursor-dot,
.hero-section.is-fine-pointer.is-cursor-active .hero-cursor-ring {
  display: block;
}

.hero-cursor-dot {
  z-index: var(--z-index-cursor);
  width: 6px;
  height: 6px;
  background: var(--hero-fg);
  transition:
    width 0.3s,
    height 0.3s,
    background-color 0.3s;
}

.hero-cursor-ring {
  z-index: var(--z-index-cursor-ring);
  width: 38px;
  height: 38px;
  border: 1px solid rgba(234, 240, 245, 0.4);
  transition:
    width 0.4s cubic-bezier(0.22, 1, 0.36, 1),
    height 0.4s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.3s;
}

.hero-cursor-dot.is-hover {
  width: 4px;
  height: 4px;
}

.hero-cursor-ring.is-hover {
  width: 72px;
  height: 72px;
  border-color: var(--hero-fg);
}

.hero-badge {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0.5rem 1.05rem;
  border: 1px solid var(--hero-border);
  border-radius: 9999px;
  background: rgba(22, 48, 74, 0.28);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  font-family: 'Bricolage Grotesque', 'Space Grotesk', sans-serif;
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--hero-fg);
  white-space: nowrap;
}

.hero-serif {
  font-family: 'Fraunces', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-variation-settings: 'SOFT' 20, 'WONK' 0;
  letter-spacing: 0.005em;
}

.hero-serif-line {
  font-size: clamp(1.35rem, 2.5vw, 1.9rem);
  line-height: 1.3;
  letter-spacing: 0;
  color: rgba(244, 248, 252, 0.88);
  text-wrap: balance;
}

.hero-serif-accent {
  color: var(--hero-accent);
}

.hero-facts {
  font-size: 1rem;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.72);
}

.hero-label {
  font-family: 'Bricolage Grotesque', 'Space Grotesk', sans-serif;
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--hero-muted);
}

.hero-title {
  font-family: 'Bricolage Grotesque', 'Space Grotesk', sans-serif;
  font-style: normal;
  font-weight: 600;
  font-variation-settings: 'opsz' 96;
  font-size: clamp(2.9rem, min(12.5vw, 19vh), 11rem);
  line-height: 0.9;
  letter-spacing: -0.035em;
  color: var(--hero-fg);
  text-shadow: 0 4px 44px rgba(16, 38, 60, 0.35);
}

.hero-reveal {
  opacity: 0;
  animation: hero-reveal 1s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.hero-reveal-char {
  display: inline-block;
  opacity: 0;
  animation: hero-reveal-char 0.9s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes hero-reveal {
  from {
    opacity: 0;
    transform: translate3d(0, 50px, 0);
    filter: blur(10px);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes hero-reveal-char {
  from {
    opacity: 0;
    transform: translate3d(0, 0.45em, 0);
    filter: blur(0.08em);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

.hero-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.95rem 1.6rem;
  border-radius: 9999px;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 0.012em;
  text-decoration: none;
  overflow: hidden;
  will-change: transform;
  transition:
    box-shadow 0.18s ease-in-out,
    border-color 0.18s ease-in-out,
    background-color 0.18s ease-in-out,
    color 0.18s ease-in-out;
}

.hero-btn-label,
.hero-btn-arrow {
  position: relative;
  z-index: 1;
}

.hero-btn-fill {
  position: absolute;
  inset: 0;
  z-index: 0;
  border-radius: inherit;
  background: #0d2136;
  clip-path: circle(0% at 50% 50%);
  transition: clip-path 0.38s cubic-bezier(0.22, 1, 0.36, 1);
}

.hero-btn-label {
  white-space: nowrap;
}

.hero-btn-arrow {
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.hero-btn-primary {
  background-color: var(--hero-fg);
  color: var(--hero-bg);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

.hero-btn-primary:hover,
.hero-btn-primary:focus-visible {
  color: #ffffff;
  box-shadow: 0 16px 46px -14px rgba(13, 33, 54, 0.65);
}

.hero-btn-primary:hover .hero-btn-fill,
.hero-btn-primary:focus-visible .hero-btn-fill {
  clip-path: circle(140% at 50% 50%);
}

.hero-btn-primary:hover .hero-btn-arrow,
.hero-btn-primary:focus-visible .hero-btn-arrow {
  transform: translate3d(4px, 0, 0);
}

.hero-trusted-item {
  font-family: 'Bricolage Grotesque', 'Space Grotesk', sans-serif;
  font-size: 1.05rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.68);
  transition: color 0.18s ease-in-out;
}

.hero-trusted-item:hover {
  color: rgba(255, 255, 255, 0.95);
}

@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .hero-badge {
    background-color: rgba(30, 62, 92, 0.92);
  }
}

@media (max-width: 640px) {
  .hero-badge {
    padding: 0.45rem 0.85rem;
    font-size: 0.64rem;
  }

  .hero-trusted-item {
    font-size: 0.82rem;
    letter-spacing: 0.08em;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-section *,
  .hero-section *::before,
  .hero-section *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .hero-reveal,
  .hero-reveal-char {
    opacity: 1;
    animation: none;
    filter: none;
    transform: none;
  }
}
</style>
