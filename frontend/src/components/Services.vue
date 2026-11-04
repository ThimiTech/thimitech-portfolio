<script setup lang="ts">
defineOptions({ name: 'StudioServices' })

import { onMounted, ref } from 'vue'
import api from '../api/api'

/** Services are managed in the backend; the frontend only renders them. */
interface Service {
  id: number
  title: string
  description: string
}

const services = ref<Service[]>([])
const loading = ref(true)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const { data } = await api.get<Service[]>('services/')
    services.value = Array.isArray(data) ? data : []
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section id="services" class="studio-wrap studio-section" aria-labelledby="services-title">
    <header class="section-head">
      <div>
        <p class="studio-kicker">Services</p>
        <h2 id="services-title">What we build</h2>
      </div>
      <p class="section-intro">
        A focused set of services, from the first line of data to the finished platform. Every
        engagement follows the same order: understand the decision, structure the data, then build
        the interface around it.
      </p>
    </header>

    <div v-if="loading" class="card-grid" aria-busy="true" aria-label="Loading services">
      <div v-for="n in 3" :key="n" class="card skeleton" />
    </div>

    <p v-else-if="error" role="alert" class="state">
      We couldn’t load our services.
      <button type="button" class="state-action" @click="load">Try again</button>
    </p>

    <p v-else-if="!services.length" class="state">
      Our services are being updated.
      <a href="#contact" class="state-action">Start the conversation</a>
    </p>

    <div v-else class="card-grid">
      <article v-for="service in services" :key="service.id" class="card service-card">
        <h3>{{ service.title }}</h3>
        <p>{{ service.description }}</p>
      </article>
    </div>

    <p v-if="!loading && !error && services.length" class="section-note">
      <strong>Not sure which one you need?</strong> Describe the problem and the data you already
      have — a spreadsheet, a survey, a pile of PDFs. We will tell you where to start, what it would
      take, and what we would leave out. <a href="#contact">Start the conversation</a>.
    </p>
  </section>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.service-card p {
  font-size: 18px;
  line-height: 1.66;
  color: #000000;
}

.skeleton {
  height: 220px;
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

@media (max-width: 640px) {
  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>
