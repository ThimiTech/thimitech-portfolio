<script setup lang="ts">
import { useApiCollection } from '../composables/useApiCollection'
import { RouterLink } from 'vue-router'

interface Project {
  id: number
  name: string
  image: string
  subtitle: string
  description: string
  url?: string
}
const { items: projects, visible } = useApiCollection<Project>('projects/')
</script>

<template>
  <section v-if="visible" id="projects" class="border-t border-ink/10 bg-panel px-6 py-10">
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
            :src="`${p.image}`"
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


  </section>
</template>
