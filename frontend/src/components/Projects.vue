<script setup lang="ts">
defineOptions({ name: 'StudioWork' })
import { onMounted, ref } from 'vue'
import api from '../api/api'
import ProjectCover from './ProjectCover.vue'
interface Project {
  id: number
  name: string
  subtitle: string
  description: string
  image: string | null
  url: string
}
const projects = ref<Project[]>([])
const loading = ref(true)
const error = ref(false)
const brokenImages = ref(new Set<number>())
async function load() {
  loading.value = true
  error.value = false
  try {
    projects.value = (await api.get<Project[]>('projects/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<template>
  <section id="projects" class="studio-wrap studio-section">
    <h2>Ideas, out in the world.</h2>
    <p class="section-intro">A closer look at the platforms we’re building.</p>
    <div v-if="loading" class="work-grid" aria-busy="true" aria-label="Loading projects">
      <div v-for="n in 2" :key="n" class="aspect-[4/3] animate-pulse bg-panel" />
    </div>
    <p v-else-if="error" role="alert" class="mt-10">
      We couldn’t load our projects. <button class="underline" @click="load">Try again</button>
    </p>
    <p v-else-if="!projects.length" class="mt-10 text-ink/65">
      New project stories are on their way.
    </p>
    <div v-else class="work-grid">
      <article
        v-for="(p, index) in projects"
        :key="p.id"
        class="work-item"
        :class="index % 2 ? 'work-offset' : ''"
      >
        <RouterLink :to="'/projects/' + p.id" class="work-image" :aria-label="'View ' + p.name">
          <img
            v-if="p.image && !brokenImages.has(p.id)"
            :src="p.image"
            :alt="p.name"
            loading="lazy"
            @error="brokenImages.add(p.id)"
          />
          <ProjectCover v-else :variant="index" />
        </RouterLink>
        <div class="work-title">
          <h3>
            <RouterLink :to="'/projects/' + p.id">{{ p.name }}</RouterLink>
          </h3>
          <span aria-hidden="true">↗</span>
        </div>
        <p class="work-category">{{ p.subtitle }}</p>
        <p class="work-description">{{ p.description }}</p>
      </article>
    </div>
  </section>
</template>
