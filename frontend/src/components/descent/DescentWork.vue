<script setup lang="ts">
/**
 * Published case studies (`/api/pm/public/`) as a deck: each project is a full-width plate
 * that sticks under the bar, and the next one slides over it while it sinks back.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ProjectCover from '../ProjectCover.vue'
import { canAnimate, gsap, ScrollTrigger } from './motion'
import { loadCases, useSite } from './site'

const { cases, casesState } = useSite()
const broken = ref(new Set<string>())
const root = ref<HTMLElement | null>(null)
let ctx: gsap.Context | undefined

const year = (c: { start_date: string | null; published_at: string | null }) => (c.start_date ?? c.published_at ?? '').slice(0, 4)

/** A plate sinks while the next one covers it. The `.at` markers are in normal flow, so they measure correctly; slots are sticky. */
async function stack() {
  ctx?.revert()
  if (!canAnimate || !root.value) return
  await nextTick()
  ctx = gsap.context(() => {
    const marks = gsap.utils.toArray<HTMLElement>('.at')
    gsap.utils.toArray<HTMLElement>('.plate').slice(0, -1).forEach((plate, i) => {
      gsap.to(plate, {
        scale: 0.93,
        filter: 'brightness(0.4)',
        ease: 'none',
        scrollTrigger: { trigger: marks[i + 1], start: 'top 90%', end: 'top 15%', scrub: true },
      })
    })
  }, root.value)
  ScrollTrigger.refresh()
}

onMounted(() => watch(cases, stack, { immediate: true }))
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section id="projects" ref="root" class="work" aria-labelledby="projects-title">
    <div class="wrap">
      <header class="lead">
        <div>
          <p class="kicker">Altitude 120 m · field notes</p>
          <h2 id="projects-title">Work you can walk through.</h2>
        </div>
        <p>
          Straight from our delivery workspace: a project appears here the day its team publishes
          it, with the story, the stack and where it stands.
        </p>
      </header>

      <p v-if="casesState === 'failed'" class="state" role="alert">
        We couldn’t load our projects.
        <button type="button" @click="loadCases">Try again</button>
      </p>
      <p v-else-if="casesState === 'ready' && !cases.length" class="state">Case studies are on their way.</p>

      <div class="deck">
        <template v-for="(c, i) in cases" :key="c.slug">
          <i class="at" aria-hidden="true" />
          <article class="slot" :style="{ '--i': i }">
          <RouterLink :to="`/work/${c.slug}`" class="plate" :aria-label="`${c.name}: read the case study`">
            <div class="words">
              <p class="idx">
                <span>N° {{ String(i + 1).padStart(2, '0') }}</span>
                <span>{{ c.key }}</span>
                <span v-if="year(c)">{{ year(c) }}</span>
              </p>
              <h3>{{ c.name }}</h3>
              <p v-if="c.tagline" class="text">{{ c.tagline }}</p>
              <ul v-if="c.tech.length" class="tech" aria-label="Built with">
                <li v-for="t in c.tech.slice(0, 6)" :key="t">{{ t }}</li>
              </ul>
              <p class="go">Read the case study <span aria-hidden="true">→</span></p>
            </div>
            <div class="shot">
              <img v-if="c.cover && !broken.has(c.slug)" :src="c.cover" :alt="''" loading="lazy" @error="broken.add(c.slug)" />
              <ProjectCover v-else :variant="i" />
            </div>
          </RouterLink>
          </article>
        </template>
      </div>

      <RouterLink to="/work" class="more">
        <span>All case studies</span>
        <span aria-hidden="true">→</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.work {
  padding-block: clamp(72px, 12svh, 128px);
}
.lead {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
  align-items: end;
  gap: 24px 56px;
  margin-bottom: clamp(36px, 5vw, 72px);
}
.lead h2 {
  margin: 16px 0 0;
}
.lead > p {
  margin: 0;
  font-size: clamp(16px, 1.3vw, 19px);
  line-height: 1.6;
  color: var(--dim);
}

.at {
  display: block;
}
/* Every plate sticks a little lower than the one before, so the deck's edges stay visible. */
.slot {
  position: sticky;
  top: calc(84px + var(--i) * 12px);
  padding-bottom: clamp(20px, 3vw, 40px);
}
.plate {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
  min-height: min(68svh, 600px);
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: color-mix(in oklab, var(--fg) 5%, var(--bg));
  color: var(--fg);
  text-decoration: none;
  transform-origin: 50% 0;
  transition: border-color 0.3s ease;
}
.plate:hover {
  border-color: var(--signal);
}
.words {
  display: flex;
  flex-direction: column;
  padding: clamp(22px, 3vw, 48px);
}
.idx {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin: 0;
  font: 400 11px/1.5 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--dim);
}
.idx span:first-child {
  color: var(--signal);
}
h3 {
  margin: auto 0 0;
  padding-top: 28px;
  font-size: clamp(30px, 4vw, 68px);
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.045em;
  text-wrap: balance;
}
.text {
  max-width: 44ch;
  margin: 16px 0 0;
  font-size: clamp(16px, 1.25vw, 19px);
  line-height: 1.55;
  color: var(--dim);
}
.tech {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
}
.tech li {
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font: 400 11px/1.4 var(--font-mono);
  letter-spacing: 0.06em;
}
.go {
  margin: 26px 0 0;
  font: 400 12px/1 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.go span {
  display: inline-block;
  margin-left: 6px;
  color: var(--signal);
  transition: transform 0.3s ease;
}
.plate:hover .go span {
  transform: translateX(6px);
}

.shot {
  position: relative;
  overflow: hidden;
  border-left: 1px solid var(--line);
}
.shot img,
.shot :deep(canvas),
.shot :deep(svg) {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.8s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.plate:hover .shot img,
.plate:hover .shot :deep(canvas),
.plate:hover .shot :deep(svg) {
  transform: scale(1.04);
}

.more {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: clamp(8px, 2vw, 24px);
  padding-block: clamp(18px, 2.2vw, 30px);
  border-block: 1px solid var(--line);
  font-size: clamp(24px, 3vw, 46px);
  font-weight: 500;
  letter-spacing: -0.04em;
  color: var(--fg);
  text-decoration: none;
  transition: padding 0.3s ease, color 0.3s ease;
}
.more:hover {
  padding-inline: 16px;
  color: var(--signal);
}

.state {
  margin: 0 0 32px;
  color: var(--dim);
}
.state button {
  margin-left: 8px;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  color: var(--signal);
  text-decoration: underline;
  cursor: pointer;
}

@media (max-width: 860px) {
  .lead {
    grid-template-columns: minmax(0, 1fr);
  }
  .plate {
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
  }
  .shot {
    order: -1;
    aspect-ratio: 16 / 9;
    border-left: 0;
    border-bottom: 1px solid var(--line);
  }
  h3 {
    padding-top: 18px;
  }
}
/* Short screens can't hold a whole plate: let the deck scroll as a plain list. */
@media (max-height: 560px) {
  .slot {
    position: static;
  }
}
</style>
