<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api/api'
import ProjectCover from '../ProjectCover.vue'
import { canAnimate, gsap, ScrollTrigger } from './motion'

interface Project { id: number; name: string; subtitle: string; description: string; image: string | null }

const projects = ref<Project[]>([])
const failed = ref(false)
const loading = ref(true)
const broken = ref(new Set<number>())
const root = ref<HTMLElement | null>(null)
const track = ref<HTMLElement | null>(null)
// Wide screens: vertical scroll drives the strip sideways. Elsewhere it is a normal swipeable row.
const sideways = canAnimate && window.matchMedia('(min-width: 861px)').matches
let ctx: gsap.Context | undefined

const distance = () => Math.max(0, (track.value?.scrollWidth ?? 0) - window.innerWidth)

async function load() {
  loading.value = true
  failed.value = false
  try {
    const { data } = await api.get<Project[]>('projects/')
    projects.value = Array.isArray(data) ? data : []
  } catch {
    failed.value = true
  } finally {
    loading.value = false
    await nextTick()
    if (sideways) ScrollTrigger.refresh() // the strip now has its real width
  }
}

onMounted(() => {
  if (sideways && root.value) {
    ctx = gsap.context(() => {
      gsap.to(track.value, {
        x: () => -distance(),
        ease: 'none',
        scrollTrigger: {
          trigger: root.value,
          start: 'top top',
          end: () => `+=${distance()}`,
          pin: true,
          scrub: 0.4,
          invalidateOnRefresh: true,
          refreshPriority: 1,
        },
      })
    }, root.value)
  }
  load()
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <section id="projects" ref="root" class="work" :class="{ sideways }" aria-labelledby="projects-title">
    <div ref="track" class="track">
      <header class="lead">
        <p class="kicker">Altitude 120 m · field notes</p>
        <h2 id="projects-title">Work you can walk through.</h2>
        <p>Every project here is live, built with the team that runs it.</p>
      </header>

      <p v-if="failed" class="state" role="alert">
        We couldn’t load our projects.
        <button type="button" @click="load">Try again</button>
      </p>
      <p v-else-if="!loading && !projects.length" class="state">Case studies are on their way.</p>

      <article v-for="(p, i) in projects" :key="p.id" class="note">
        <RouterLink :to="`/projects/${p.id}`" class="shot" :aria-label="`View ${p.name}`">
          <img v-if="p.image && !broken.has(p.id)" :src="p.image" :alt="p.name" loading="lazy" @error="broken.add(p.id)" />
          <ProjectCover v-else :variant="i" />
        </RouterLink>
        <p class="idx">N° {{ String(i + 1).padStart(2, '0') }}<span v-if="p.subtitle"> · {{ p.subtitle }}</span></p>
        <h3><RouterLink :to="`/projects/${p.id}`">{{ p.name }}</RouterLink></h3>
        <p class="text">{{ p.description }}</p>
      </article>

      <RouterLink to="/work" class="more">
        <span>All case studies</span>
        <span aria-hidden="true">→</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.work {
  overflow: hidden;
  padding-block: clamp(72px, 12svh, 128px);
}
.track {
  display: flex;
  align-items: stretch;
  gap: clamp(20px, 2.4vw, 40px);
  padding-inline: calc((100vw - var(--wrap)) / 2);
  overflow-x: auto;
  scroll-snap-type: x proximity;
}
.sideways {
  display: flex;
  height: 100svh;
  align-items: center;
  padding-block: 0;
}
.sideways .track {
  width: max-content;
  overflow: visible;
}

.lead {
  display: flex;
  flex: 0 0 min(78vw, 440px);
  flex-direction: column;
  justify-content: center;
}
.lead h2 {
  margin: 16px 0 18px;
}
.lead p:last-child {
  margin: 0;
  font-size: 18px;
  line-height: 1.55;
  color: var(--dim);
}

.note {
  flex: 0 0 min(78vw, 440px);
  scroll-snap-align: start;
}
.shot {
  display: block;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border: 1px solid var(--line);
  background: rgb(242 239 232 / 0.04);
}
.shot img,
.shot :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.shot:hover img,
.shot:hover :deep(svg) {
  transform: scale(1.04);
}
.idx {
  margin: 18px 0 0;
  font: 400 11px/1.5 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--signal);
}
.note h3 {
  margin: 8px 0 10px;
  font-size: clamp(22px, 2vw, 30px);
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.03em;
}
.note h3 a {
  color: inherit;
  text-decoration: none;
}
.note h3 a:hover {
  color: var(--signal);
}
.text {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  font-size: 16px;
  line-height: 1.55;
  color: var(--dim);
}

.more {
  display: flex;
  flex: 0 0 min(60vw, 300px);
  flex-direction: column;
  justify-content: space-between;
  aspect-ratio: 3 / 4;
  align-self: center;
  padding: 24px;
  border: 1px solid var(--line);
  font-size: clamp(22px, 2vw, 30px);
  font-weight: 500;
  letter-spacing: -0.03em;
  color: var(--fg);
  text-decoration: none;
  transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}
.more:hover {
  border-color: var(--signal);
  background: var(--signal);
  color: #0a0a0a;
}
.more span:last-child {
  align-self: end;
  font-size: 44px;
  line-height: 1;
}

.state {
  align-self: center;
  flex: 0 0 auto;
  margin: 0;
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
</style>
