<script setup lang="ts">
defineOptions({ name: 'StudioServices' })
import { onMounted, ref } from 'vue'
import api from '../api/api'
interface Service {
  id: number
  title: string
  description: string
}
const services = ref<Service[]>([])
const loading = ref(true)
const error = ref(false)
async function load() {
  error.value = false
  loading.value = true
  try {
    services.value = (await api.get<Service[]>('services/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<template>
  <section id="services" class="studio-section services-section">
    <div class="studio-wrap">
      <h2>Complex problems.<br />Considered solutions.</h2>
      <p class="section-intro">
        From the first layer of data to the software people use every day.
      </p>
      <div v-if="loading" class="mt-12 grid gap-4" aria-busy="true" aria-label="Loading services">
        <div v-for="n in 3" :key="n" class="h-24 animate-pulse bg-panel" />
      </div>
      <p v-else-if="error" role="alert" class="mt-10">
        Services are temporarily unavailable.
        <button class="underline" @click="load">Try again</button>
      </p>
      <p v-else-if="!services.length" class="mt-10 text-ink/65">
        Have a geospatial or software challenge?
        <a href="#contact" class="underline">Tell us about it.</a>
      </p>
      <div v-else class="service-list">
        <article v-for="(s, i) in services" :key="s.id" class="service-row">
          <span class="service-index" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <h3>{{ s.title }}</h3>
          <p>{{ s.description }}</p>
          <span class="service-arrow" aria-hidden="true">↗</span>
        </article>
      </div>
    </div>
  </section>
</template>
