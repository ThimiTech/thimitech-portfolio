<script setup lang="ts">
defineOptions({ name: 'StudioCareers' })
import { onMounted, ref } from 'vue'
import api from '../api/api'
interface Job {
  id: number
  title: string
  location?: string
  employment_type?: string
  description: string
}
const jobs = ref<Job[]>([])
const loading = ref(true)
const error = ref(false)
async function load() {
  loading.value = true
  error.value = false
  try {
    jobs.value = (await api.get<Job[]>('jobs/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<template>
  <section id="hiring" class="studio-wrap studio-section careers-section">
    <div>
      <h2>Find your place<br />with us.</h2>
      <p class="section-intro">
        Curious about maps, data, and making things work? We’d like to meet you.
      </p>
    </div>
    <div class="career-list">
      <p v-if="loading" role="status">Loading open positions…</p>
      <p v-else-if="error" role="alert">
        Could not load positions. <button class="underline" @click="load">Try again</button>
      </p>
      <p v-else-if="!jobs.length">
        No open roles right now. Introduce yourself at
        <a href="mailto:info@thimitech.com" class="underline">info@thimitech.com</a>.
      </p>
      <RouterLink v-for="job in jobs" :key="job.id" :to="'/apply/' + job.id" class="career-row"
        ><div>
          <h3>{{ job.title }}</h3>
          <p>
            {{ job.employment_type || 'Join the team'
            }}<span v-if="job.location"> · {{ job.location }}</span>
          </p>
        </div>
        <span aria-hidden="true">↗</span></RouterLink
      >
    </div>
  </section>
</template>
