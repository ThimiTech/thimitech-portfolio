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
    const { data } = await api.get<Project[]>('projects/')
    projects.value = Array.isArray(data) ? data : []
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section id="projects" class="projects-band" aria-labelledby="projects-title">
    <div class="studio-wrap studio-section">
      <header class="section-head">
        <div>
          <p class="studio-kicker">Portfolio</p>
          <h2 id="projects-title">Current projects</h2>
        </div>
        <p class="section-intro">Platforms we’re actively building right now.</p>
      </header>

      <div v-if="loading" class="card-grid" aria-busy="true" aria-label="Loading projects">
        <div v-for="n in 3" :key="n" class="card skeleton" />
      </div>

      <p v-else-if="error" role="alert" class="state">
        We couldn’t load our projects.
        <button type="button" class="state-action" @click="load">Try again</button>
      </p>

      <p v-else-if="!projects.length" class="state">
        New project stories are on their way.
        <a href="#contact" class="state-action">Work with us</a>
      </p>

      <div v-else class="card-grid project-grid">
        <article v-for="(project, index) in projects" :key="project.id" class="card project-card">
          <RouterLink
            :to="'/projects/' + project.id"
            class="project-media"
            :aria-label="'View ' + project.name"
          >
            <img
              v-if="project.image && !brokenImages.has(project.id)"
              :src="project.image"
              :alt="project.name"
              loading="lazy"
              @error="brokenImages.add(project.id)"
            />
            <ProjectCover v-else :variant="index" />
          </RouterLink>

          <div class="project-body">
            <h3>
              <RouterLink :to="'/projects/' + project.id">{{ project.name }}</RouterLink>
            </h3>
            <p v-if="project.subtitle" class="project-subtitle">{{ project.subtitle }}</p>
            <p class="project-text">{{ project.description }}</p>
          </div>

          <RouterLink :to="'/projects/' + project.id" class="card-link">
            View details
          </RouterLink>
        </article>
      </div>

      <p class="section-note">
        <strong>Every project here is live work</strong>, built with the team that runs it — from the
        first field survey to the dashboards their staff open on a Monday morning. Want a closer
        look at the data model, the stack or what changed for the client?
        <a href="#contact">Ask us for a walkthrough</a>.
      </p>
    </div>
  </section>
</template>

<style scoped>
.projects-band {
  background: #ffffff;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.project-card {
  padding: 0;
  overflow: hidden;
  gap: 0;
}

.project-media {
  display: block;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-bottom: 1px solid rgb(10 10 10 / 0.1);
  background: #f5f6f7;
}

.project-media img,
.project-media :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.project-card:hover .project-media img,
.project-card:hover .project-media :deep(canvas) {
  transform: scale(1.03);
}

.project-body {
  display: grid;
  gap: 10px;
  padding: clamp(20px, 2vw, 26px) clamp(20px, 2vw, 26px) 0;
}

.project-body h3 a {
  color: inherit;
  text-decoration: none;
}

.project-subtitle {
  font: 500 13px/1.5 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #000000;
}

.project-text {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  font-size: 18px;
  line-height: 1.62;
  color: #000000;
}

.project-card .card-link {
  margin: 20px clamp(20px, 2vw, 26px) clamp(20px, 2vw, 26px);
  padding-top: 16px;
  border-top: 1px solid rgb(10 10 10 / 0.1);
}

.skeleton {
  height: 380px;
  border-radius: 14px;
  background: linear-gradient(90deg, #f5f6f7, #eceef0 40%, #f5f6f7 80%);
  animation: shimmer 1.4s ease-in-out infinite;
}

.state {
  padding: 40px 0;
  font-size: 16px;
  color: #5b6169;
}

.state-action {
  margin-left: 8px;
  border: 0;
  border-bottom: 1px solid currentColor;
  background: none;
  font: inherit;
  color: #0a0a0a;
  cursor: pointer;
}

@keyframes shimmer {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

@media (max-width: 1023px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }

  .project-card:hover .project-media img,
  .project-card:hover .project-media :deep(canvas) {
    transform: none;
  }
}
</style>
