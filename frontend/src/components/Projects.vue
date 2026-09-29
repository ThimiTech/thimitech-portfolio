<script setup lang="ts">
// const projects = [
//   {
//     title: 'Plan My Nepal',
//     status: 'In development',
//     text: 'A trip-planning platform that maps treks, routes and destinations across Nepal.',
//     tags: ['Travel', 'Route planning', 'Leaflet'],
//     art: 'bg-gradient-to-br from-flag to-contour',
//   },
//   {
//     title: 'Pure Nepal',
//     status: 'In development',
//     text: 'A tourism showcase mapping the culture, nature and heritage sites of Nepal.',
//     tags: ['Tourism', 'Culture', 'Web map'],
//     art: 'bg-gradient-to-br from-river to-emerald-500',
//   },
//   {
//     title: 'The Bot Bazar',
//     status: 'In development',
//     text: 'A location-aware online marketplace connecting nearby buyers and sellers.',
//     tags: ['Marketplace', 'Chatbot', 'Geolocation'],
//     art: 'bg-gradient-to-br from-ink to-river',
//   },
// ]

import api from "../api/api"
import {ref,onMounted} from "vue"
const projects=ref([])
const getProjects=async()=>{ 
  try{
   const res= await api.get("projects/")
   console.log(res.data)
   projects.value=res.data
  }
  catch{

  }
}
onMounted(()=>{ 
  getProjects()
})
</script>

<template>
  <section id="projects" class="border-t border-ink/10 bg-panel py-32">
    <div class="mx-auto max-w-7xl px-6">

      <!-- Section Heading -->
      <div class="max-w-xl">
        <h2
          class="font-display text-3xl font-semibold text-ink lg:text-4xl"
        >
          Current Projects
        </h2>

        <p class="mt-4 text-ink/65">
          Platforms we're actively building right now.
        </p>
      </div>

      <!-- Projects Grid -->
      <div class="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">

        <!-- Project Card -->
        <article
          v-for="p in projects"
          :key="p.id"
          class="group overflow-hidden rounded-2xl border border-ink/10 bg-paper transition-all duration-300 hover:-translate-y-1 hover:shadow-lg"
        >

          <!-- Project Image -->
          <div class="h-56 w-full overflow-hidden bg-gray-100">
            <img
              v-if="p.image" 
              :src="`http://127.0.0.1:8000${p.image}`"
              :alt="p.name"
              class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />

            <!-- Show this if there is no image -->
            <div
              v-else
              class="flex h-full items-center justify-center bg-gray-100 text-sm text-ink/40"
            >
              No image available
            </div>
          </div>

          <!-- Project Content -->
          <div class="p-6">

            <!-- Subtitle -->
            <span
              v-if="p.subtitle"
              class="inline-flex rounded-full border border-ink/15 px-3 py-1 font-mono text-[11px] text-ink/60"
            >
              {{ p.subtitle }}
            </span>

            <!-- Project Name -->
            <h3
              class="mt-4 font-display text-xl font-medium text-ink"
            >
              {{ p.name }}
            </h3>

            <!-- Description -->
            <p class="mt-3 text-sm leading-6 text-ink/65">
              {{ p.description }}
            </p>

            <!-- Project Link -->
            <a
              v-if="p.url"
              :href="p.url"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-5 inline-flex items-center font-mono text-xs text-river transition-colors hover:text-ink"
            >
              View project
              <span class="ml-2">→</span>
            </a>

          </div>
        </article>

      </div>

    </div>
  </section>
</template>