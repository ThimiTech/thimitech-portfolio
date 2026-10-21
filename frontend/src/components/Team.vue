<script setup lang="ts">
defineOptions({ name: 'StudioTeam' })
import { onMounted, ref } from 'vue'
import api from '../api/api'
interface Member {
  id: number
  name: string
  role: string
  photo?: string | null
}
const team = ref<Member[]>([])
const loading = ref(true)
const error = ref(false)
const initials = (name: string) =>
  name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
async function load() {
  loading.value = true
  error.value = false
  try {
    team.value = (await api.get<Member[]>('team/')).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<template>
  <section id="team" class="studio-wrap studio-section team-section">
    <h2>The people behind<br />the perspective.</h2>
    <p class="section-intro">
      Engineers, mapmakers, and problem solvers. Working closely, building with care.
    </p>
    <p v-if="loading" class="mt-10" role="status">Loading our team…</p>
    <p v-else-if="error" role="alert" class="mt-10">
      Our team is temporarily unavailable.
      <button class="underline" @click="load">Try again</button>
    </p>
    <p v-else-if="!team.length" class="mt-10">Meet the team here soon.</p>
    <div v-else class="people-grid">
      <article v-for="m in team" :key="m.id" class="person">
        <div class="person-portrait">
          <img v-if="m.photo" :src="m.photo" :alt="m.name" loading="lazy" /><span
            v-else
            aria-hidden="true"
            >{{ initials(m.name) }}</span
          >
        </div>
        <h3>{{ m.name }}</h3>
        <p>{{ m.role }}</p>
      </article>
    </div>
  </section>
</template>
