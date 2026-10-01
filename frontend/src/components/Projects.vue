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

import api from "../api/api";
import { ref, onMounted } from "vue";
const projects = ref([]);
const getProjects = async () => {
  try {
    const res = await api.get("projects/");
    console.log(res.data);
    projects.value = res.data;
  } catch {}
};
onMounted(() => {
  getProjects();
});
</script>

<template>
  <section id="projects" class="min-h-screen border-t border-ink/10 bg-panel px-6 py-10">
    <!-- Header -->
    <div class="mx-auto max-w-7xl">
      <h2 class="font-display text-3xl font-bold text-ink lg:text-4xl">Current Projects</h2>

      <p class="mt-2 text-ink/60">Platforms we're actively building right now.</p>
    </div>

    <!-- Projects -->
    <div
      class="mx-auto mt-8 grid max-w-7xl grid-cols-1 items-stretch gap-6 sm:grid-cols-2 lg:grid-cols-3"
    >
      <!-- OUTER LOOP -->
      <article
        v-for="p in projects"
        :key="p.id"
        class="flex h-full flex-col overflow-hidden rounded-2xl bg-paper shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
      >
        <!-- Project Image -->
        <div class="relative h-56 shrink-0 overflow-hidden bg-panel">
          <img
            :src="`http://127.0.0.1:8000${p.image}`"
            :alt="p.name"
            class="h-full w-full object-cover transition duration-300 hover:scale-105"
          />

          <!-- Subtitle Badge -->
          <span
            class="absolute right-3 top-3 rounded-full bg-paper px-3 py-1 text-xs font-semibold text-ink shadow"
          >
            {{ p.subtitle }}
          </span>
        </div>

        <!-- Card Content -->
        <div class="flex flex-1 flex-col p-5">
          <!-- Project Name -->
          <h3 class="line-clamp-1 font-display text-xl font-bold text-ink">
            {{ p.name }}
          </h3>

          <!-- Subtitle -->
          <p class="mt-1 line-clamp-1 font-mono text-xs text-ink/50">
            {{ p.subtitle }}
          </p>

          <!-- Description -->
          <p class="mt-4 line-clamp-3 min-h-[72px] text-sm leading-6 text-ink/65">
            {{ p.description }}
          </p>

          <!-- Spacer -->
          <div class="flex-1"></div>

          <!-- Visit Project -->
          <!-- Project Actions -->
          <div class="mt-6 flex flex-col gap-3">
            <!-- View Details -->
            <RouterLink
              :to="{
                name: 'projects',
                params: { id: p.id },
              }"
              class="flex w-full items-center justify-center rounded-lg bg-river px-4 py-3 font-mono text-xs font-semibold text-paper transition hover:opacity-90"
            >
              View Details →
            </RouterLink>

            <!-- Visit Project -->
            <a
              v-if="p.url"
              :href="p.url"
              target="_blank"
              rel="noopener noreferrer"
              class="flex w-full items-center justify-center rounded-lg border border-ink/10 bg-paper px-4 py-3 font-mono text-xs font-semibold text-ink transition hover:bg-ink hover:text-paper"
            >
              Visit Project ↗
            </a>
          </div>
        </div>
      </article>
    </div>

    <!-- Empty State -->
    <div v-if="projects.length === 0" class="py-20 text-center text-ink/50">No projects found.</div>
  </section>
</template>
