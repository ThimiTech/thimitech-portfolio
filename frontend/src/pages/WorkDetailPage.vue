<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/api'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import ProjectCover from '../components/ProjectCover.vue'
import MarkdownView from '../components/app/pm/MarkdownView.vue'
import { dateLabel, fileSize, linkLabel } from '../components/app/pm/pm'
import type { CaseCard } from './WorkPage.vue'
import '../assets/studio.css'
interface CaseStudy extends CaseCard {
  sections: string[]
  story?: string
  progress?: { total: number; done: number; percent: number }
  milestones?: { title: string; due_date: string; completed: boolean }[]
  team?: { name: string; role: string; lead: boolean }[]
  links?: { title: string; kind: string; url: string }[]
  gallery?: { id: number; title: string; description: string; url: string }[]
  documents?: { id: number; title: string; extension: string; size: number; url: string }[]
}
const route = useRoute()
const data = ref<CaseStudy | null>(null)
const loading = ref(true)
const missing = ref(false)
const lightbox = ref<number | null>(null)
const shot = computed(() => (lightbox.value === null ? null : data.value?.gallery?.[lightbox.value]))
async function load() {
  loading.value = true
  missing.value = false
  try {
    data.value = (await api.get<CaseStudy>(`pm/public/${route.params.slug}/`)).data
    document.title = `${data.value.name} · Thimitech`
  } catch {
    missing.value = true
  } finally {
    loading.value = false
  }
}
function onKey(e: KeyboardEvent) {
  const n = data.value?.gallery?.length || 0
  const i = lightbox.value
  if (i === null || !n) return
  if (e.key === 'Escape') lightbox.value = null
  if (e.key === 'ArrowRight') lightbox.value = (i + 1) % n
  if (e.key === 'ArrowLeft') lightbox.value = (i - 1 + n) % n
}
watch(() => route.params.slug, load)
onMounted(load)
</script>
<template>
  <div class="studio bg-paper font-body text-ink" @keydown="onKey">
    <Navbar />
    <main class="studio-wrap studio-section">
      <RouterLink to="/work" class="text-sm text-ink/65 hover:text-ink">← All case studies</RouterLink>
      <div v-if="loading" class="mt-10 h-96 animate-pulse bg-panel" aria-busy="true" aria-label="Loading project" />
      <div v-else-if="missing || !data" class="py-20">
        <h1 class="text-3xl font-medium">This project isn’t public.</h1>
        <p class="mt-4 text-ink/65">It may have been unpublished. Take a look at our other work.</p>
        <RouterLink to="/work" class="studio-button">See all projects <span aria-hidden="true">↗</span></RouterLink>
      </div>
      <article v-else class="mt-10">
        <header class="grid gap-8 md:grid-cols-[1.4fr_1fr] md:items-end">
          <div>
            <p class="studio-kicker">{{ data.key }}<template v-if="data.start_date"> · since {{ dateLabel(data.start_date) }}</template></p>
            <h1 class="mt-5 text-4xl font-normal leading-tight tracking-tight md:text-6xl">{{ data.name }}</h1>
            <p v-if="data.tagline" class="mt-5 max-w-2xl text-lg leading-8 text-ink/70">{{ data.tagline }}</p>
          </div>
          <dl v-if="data.progress || data.tech.length" class="grid gap-5 border-l border-ink/15 pl-6">
            <div v-if="data.progress">
              <dt class="font-mono text-xs uppercase tracking-widest text-ink/50">Progress</dt>
              <dd class="mt-2 flex items-center gap-3">
                <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-panel"><span class="block h-full bg-moss" :style="{ width: `${data.progress.percent}%` }" /></span>
                <span class="font-mono text-sm">{{ data.progress.percent }}%</span>
              </dd>
            </div>
            <div v-if="data.tech.length">
              <dt class="font-mono text-xs uppercase tracking-widest text-ink/50">Built with</dt>
              <dd class="mt-2 flex flex-wrap gap-1.5">
                <span v-for="t in data.tech" :key="t" class="rounded-full border border-ink/15 px-2.5 py-0.5 text-xs">{{ t }}</span>
              </dd>
            </div>
          </dl>
        </header>
        <div class="mt-10 aspect-[21/9] overflow-hidden bg-panel">
          <img v-if="data.cover" :src="data.cover" :alt="data.name" class="h-full w-full object-cover" />
          <ProjectCover v-else :variant="data.name.length % 4" />
        </div>

        <div class="mt-14 grid gap-14 lg:grid-cols-[1fr_300px]">
          <div class="min-w-0">
            <section v-if="data.story" class="max-w-3xl text-[17px]">
              <MarkdownView :source="data.story" />
            </section>
            <section v-if="data.gallery?.length" class="mt-14">
              <h2 class="!text-2xl">Gallery</h2>
              <div class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3">
                <button v-for="(g, i) in data.gallery" :key="g.id" class="group aspect-[4/3] overflow-hidden bg-panel" :aria-label="`View ${g.title}`" @click="lightbox = i">
                  <img :src="g.url" :alt="g.title" loading="lazy" class="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
                </button>
              </div>
            </section>
          </div>
          <aside class="grid content-start gap-10">
            <section v-if="data.milestones?.length">
              <h2 class="font-mono text-xs uppercase tracking-widest text-ink/50">Milestones</h2>
              <ol class="mt-4 border-l border-ink/15">
                <li v-for="m in data.milestones" :key="m.title + m.due_date" class="relative pb-5 pl-5">
                  <span class="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-paper" :class="m.completed ? 'bg-moss' : 'bg-ink/25'" />
                  <p class="text-sm" :class="m.completed ? '' : 'text-ink/70'">{{ m.title }}</p>
                  <p class="font-mono text-xs text-ink/50">{{ dateLabel(m.due_date) }} · {{ m.completed ? 'done' : 'planned' }}</p>
                </li>
              </ol>
            </section>
            <section v-if="data.team?.length">
              <h2 class="font-mono text-xs uppercase tracking-widest text-ink/50">Team</h2>
              <ul class="mt-4 grid gap-3">
                <li v-for="p in data.team" :key="p.name" class="text-sm">
                  {{ p.name }}<span v-if="p.lead" class="ml-2 font-mono text-[10px] uppercase text-flag">lead</span>
                  <span v-if="p.role" class="block text-xs text-ink/55">{{ p.role }}</span>
                </li>
              </ul>
            </section>
            <section v-if="data.links?.length">
              <h2 class="font-mono text-xs uppercase tracking-widest text-ink/50">Links</h2>
              <ul class="mt-4 grid gap-2">
                <li v-for="l in data.links" :key="l.url">
                  <a :href="l.url" target="_blank" rel="noopener noreferrer" class="group flex items-baseline justify-between gap-3 border-b border-ink/10 pb-2 text-sm hover:text-river">
                    {{ l.title }}<span class="font-mono text-[10px] uppercase text-ink/45 group-hover:text-river">{{ linkLabel(l.kind) }} ↗</span>
                  </a>
                </li>
              </ul>
            </section>
            <section v-if="data.documents?.length">
              <h2 class="font-mono text-xs uppercase tracking-widest text-ink/50">Downloads</h2>
              <ul class="mt-4 grid gap-2">
                <li v-for="d in data.documents" :key="d.id">
                  <a :href="`${d.url}?download=1`" class="flex items-baseline justify-between gap-3 border-b border-ink/10 pb-2 text-sm hover:text-river">
                    {{ d.title }}<span class="font-mono text-[10px] uppercase text-ink/45">{{ d.extension }} · {{ fileSize(d.size) }}</span>
                  </a>
                </li>
              </ul>
            </section>
            <a href="/#contact" class="studio-button">Start a project like this <span aria-hidden="true">↗</span></a>
          </aside>
        </div>
      </article>
    </main>
    <Footer />
    <div v-if="shot" class="fixed inset-0 z-50 grid place-items-center bg-scrim/90 p-4" role="dialog" aria-modal="true" :aria-label="shot.title" @click.self="lightbox = null">
      <figure class="max-w-5xl">
        <img :src="shot.url" :alt="shot.title" class="max-h-[80vh] w-auto object-contain" />
        <figcaption class="mt-3 text-center text-sm text-paper/80">{{ shot.title }}<span v-if="shot.description"> — {{ shot.description }}</span></figcaption>
      </figure>
      <button class="absolute right-5 top-5 text-2xl text-paper" aria-label="Close" autofocus @click="lightbox = null">✕</button>
    </div>
  </div>
</template>
