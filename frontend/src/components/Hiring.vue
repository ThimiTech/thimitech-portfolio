<script setup lang="ts">
defineOptions({ name: 'StudioCareers' })

import { onMounted, ref } from 'vue'
import api from '../api/api'

interface Requirement {
  id: number
  text: string
  display_order: number
}

interface Job {
  id: number
  title: string
  employment_type: string
  description: string
  requirements: Requirement[]
  is_active: boolean
}

const jobs = ref<Job[]>([])
const loading = ref(true)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const { data } = await api.get<Job[]>('jobs/')
    jobs.value = (Array.isArray(data) ? data : []).map((job) => ({
      ...job,
      requirements: Array.isArray(job.requirements) ? job.requirements : [],
    }))
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section id="hiring" class="studio-wrap studio-section" aria-labelledby="hiring-title">
    <header class="section-head">
      <div>
        <p class="studio-kicker">Careers</p>
        <h2 id="hiring-title">Join the team</h2>
      </div>
      <p class="section-intro">
        We look for people who value collaboration, see maps as tools for meaningful impact, and
        want to shape how Nepal works with its own data.
      </p>
    </header>

    <div v-if="loading" class="job-list" aria-busy="true" aria-label="Loading open positions">
      <div v-for="n in 2" :key="n" class="card skeleton" />
    </div>

    <p v-else-if="error" role="alert" class="state">
      We couldn’t load open positions.
      <button type="button" class="state-action" @click="load">Try again</button>
    </p>

    <p v-else-if="!jobs.length" class="state">
      No open roles right now. Introduce yourself at
      <a class="state-action" href="mailto:info@thimitech.com">info@thimitech.com</a>.
    </p>

    <div v-else class="job-list">
      <article v-for="job in jobs" :key="job.id" class="card job-card">
        <div class="job-main">
          <h3>{{ job.title }}</h3>
          <p v-if="job.employment_type" class="chip">{{ job.employment_type }}</p>
          <p class="job-text">{{ job.description }}</p>
        </div>

        <div class="job-side">
          <template v-if="job.requirements.length">
            <p class="job-side-title">Requirements</p>
            <ul class="job-requirements">
              <li v-for="requirement in job.requirements" :key="requirement.id">
                {{ requirement.text }}
              </li>
            </ul>
          </template>

          <RouterLink :to="'/apply/' + job.id" class="studio-button job-apply">
            Apply for this position <span aria-hidden="true">→</span>
          </RouterLink>
        </div>
      </article>
    </div>

    <p class="section-note">
      <strong>Not seeing your role?</strong> Send your CV and a short note about what you would like
      to build to <a href="mailto:info@thimitech.com">info@thimitech.com</a> — we keep good people on
      file and get in touch when something fits.
    </p>
  </section>
</template>

<style scoped>
.job-list {
  display: grid;
  gap: clamp(18px, 2vw, 24px);
}

.job-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: clamp(24px, 4vw, 56px);
  padding: clamp(26px, 3vw, 40px);
}

.job-card:hover {
  transform: none;
  box-shadow: none;
  border-color: rgb(10 10 10 / 0.26);
}

.job-main {
  display: grid;
  gap: 14px;
  align-content: start;
}

.job-main .chip {
  justify-self: start;
  color: #0a0a0a;
}

.job-text {
  font-size: 18px;
  line-height: 1.68;
  color: #000000;
}

.job-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.job-side-title {
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #000000;
}

.job-requirements {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-left: 20px;
  font-size: 17px;
  line-height: 1.62;
  color: #000000;
}

.job-requirements li::marker {
  color: rgb(10 10 10 / 0.4);
}

.job-apply {
  /* pinned to the bottom of the card */
  align-self: flex-start;
  margin-top: auto;
  padding-top: 0;
}

.skeleton {
  height: 280px;
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

@media (max-width: 900px) {
  .job-card {
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>
