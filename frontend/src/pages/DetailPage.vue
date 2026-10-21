<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/api'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
import ProjectCover from '../components/ProjectCover.vue'
import '../assets/studio.css'
interface PortfolioProject {
  id: number
  name: string
  subtitle: string
  description: string
  image: string | null
  url: string
}
const route = useRoute()
const project = ref<PortfolioProject | null>(null)
const loading = ref(true)
const error = ref(false)
const imageFailed = ref(false)
const externalUrl = computed(() =>
  /^https?:\/\//.test(project.value?.url || '') ? project.value!.url : null,
)
async function load() {
  loading.value = true
  error.value = false
  try {
    project.value = (await api.get<PortfolioProject>('projects/' + route.params.id + '/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<template>
  <div class="studio bg-paper font-body text-ink">
    <Navbar />
    <main class="studio-wrap studio-section">
      <RouterLink to="/#projects" class="text-sm text-ink/65 hover:text-ink"
        >← Back to our work</RouterLink
      >
      <div
        v-if="loading"
        class="mt-10 h-96 animate-pulse bg-panel"
        aria-busy="true"
        aria-label="Loading project"
      />
      <div v-else-if="error || !project" class="py-20">
        <h1 class="text-3xl font-medium">This project is unavailable.</h1>
        <p class="mt-4 text-ink/65">Try again or return to our other work.</p>
        <button class="btn-ink mt-6" @click="load">Try again</button>
      </div>
      <article v-else class="mt-10">
        <p class="studio-kicker">{{ project.subtitle }}</p>
        <h1 class="mt-5 max-w-4xl text-4xl font-normal leading-tight tracking-tight md:text-6xl">
          {{ project.name }}
        </h1>
        <div class="mt-10 grid items-start gap-10 md:grid-cols-[1.3fr_1fr]">
          <div class="aspect-[4/3] overflow-hidden bg-panel">
            <img
              v-if="project.image && !imageFailed"
              :src="project.image"
              :alt="project.name"
              class="h-full w-full object-cover"
              @error="imageFailed = true"
            />
            <ProjectCover v-else :variant="(project.id - 1) % 4" />
          </div>
          <div class="md:pt-3">
            <h2 class="!text-2xl">The project</h2>
            <p class="mt-5 whitespace-pre-wrap text-base leading-8 text-ink/65">
              {{ project.description }}
            </p>
            <a
              v-if="externalUrl"
              :href="externalUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="studio-button"
              >Visit the project <span aria-hidden="true">↗</span></a
            ><a v-else href="/#contact" class="studio-button"
              >Discuss a similar project <span aria-hidden="true">↗</span></a
            >
          </div>
        </div>
      </article>
    </main>
    <Footer />
  </div>
</template>
