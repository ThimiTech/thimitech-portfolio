<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/api'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import ProjectCover from '../components/ProjectCover.vue'
import '../assets/studio.css'
export interface CaseCard {
  slug: string
  name: string
  key: string
  tagline: string
  cover: string | null
  tech: string[]
  health: string
  start_date: string | null
  due_date: string | null
  published_at: string | null
}
const cases = ref<CaseCard[]>([])
const loading = ref(true)
const error = ref(false)
async function load() {
  loading.value = true
  error.value = false
  try {
    cases.value = (await api.get<CaseCard[]>('pm/public/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  document.title = 'Our work · Thimitech'
  load()
})
</script>
<template>
  <div class="studio bg-paper font-body text-ink">
    <Navbar />
    <main class="studio-wrap studio-section">
      <p class="studio-kicker">Case studies</p>
      <h1 class="mt-5 max-w-3xl text-4xl font-normal leading-tight tracking-tight md:text-6xl">What we build, and how it went.</h1>
      <p class="mt-5 max-w-2xl text-base leading-8 text-ink/65">Live projects from our delivery team — the problem, the approach and where each one stands today.</p>
      <div v-if="loading" class="mt-14 grid gap-8 md:grid-cols-2" aria-busy="true" aria-label="Loading projects">
        <div v-for="i in 4" :key="i" class="aspect-[4/3] animate-pulse bg-panel" />
      </div>
      <div v-else-if="error" class="py-20">
        <p class="text-ink/65">Could not load projects.</p>
        <button class="btn-ink mt-6" @click="load">Try again</button>
      </div>
      <p v-else-if="!cases.length" class="py-20 text-ink/65">Case studies are on their way.</p>
      <div v-else class="mt-14 grid gap-x-8 gap-y-14 md:grid-cols-2">
        <RouterLink v-for="(c, i) in cases" :key="c.slug" :to="`/work/${c.slug}`" class="group block" :class="i % 2 ? 'md:mt-16' : ''">
          <div class="aspect-[4/3] overflow-hidden bg-panel">
            <img v-if="c.cover" :src="c.cover" :alt="c.name" class="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]" loading="lazy" />
            <ProjectCover v-else :variant="i % 4" />
          </div>
          <div class="mt-5 flex items-baseline justify-between gap-4">
            <h2 class="!text-2xl font-normal tracking-tight group-hover:text-river">{{ c.name }}</h2>
            <span class="shrink-0 font-mono text-xs text-ink/50">{{ c.key }}</span>
          </div>
          <p v-if="c.tagline" class="mt-2 text-ink/65">{{ c.tagline }}</p>
          <p v-if="c.tech.length" class="mt-3 font-mono text-xs text-ink/50">{{ c.tech.slice(0, 5).join(' · ') }}</p>
        </RouterLink>
      </div>
    </main>
    <Footer />
  </div>
</template>
