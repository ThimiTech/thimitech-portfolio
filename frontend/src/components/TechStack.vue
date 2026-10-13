<script setup lang="ts">
const stack = [
  {
    group: 'Mapping in the browser',
    accent: 'text-river border-river/30 bg-river/5',
    icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
    items: ['Leaflet', 'MapLibre GL', 'OpenLayers', 'Vue 3', 'TypeScript'],
  },
  {
    group: 'Servers & databases',
    accent: 'text-contour border-contour/30 bg-contour/5',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4',
    items: ['PostGIS', 'GeoServer', 'Node.js', 'Docker'],
  },
  {
    group: 'Data & analysis',
    accent: 'text-flag border-flag/30 bg-flag/5',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    items: ['QGIS', 'GDAL', 'Python', 'Vector tiles'],
  },
  {
    group: 'Field data & mobile',
    accent: 'text-river border-river/30 bg-river/5',
    icon: 'M12 21c-4.5-4.5-7-8.25-7-11.5A7 7 0 0112 2a7 7 0 017 7.5c0 3.25-2.5 7-7 11.5zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z',
    items: ['ODK Collect', 'KoboToolbox', 'GPS survey', 'Offline sync'],
  },
  {
    group: 'Cloud & deployment',
    accent: 'text-contour border-contour/30 bg-contour/5',
    icon: 'M3 15a4 4 0 004 4h10a4 4 0 000-8 5 5 0 00-9.6-2A4 4 0 003 15z',
    items: ['AWS', 'Nginx', 'GitHub Actions', 'Linux'],
  },
  {
    group: 'Design & frontend',
    accent: 'text-flag border-flag/30 bg-flag/5',
    icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
    items: ['Figma', 'Tailwind CSS', 'Vite', 'D3.js'],
  },
]
</script>

<template>
  <section id="stack" class="border-t border-ink/10 bg-paper px-10 py-10">
    <div class="mx-auto max-w-none">

      <div class="max-w-xl">
        <h2 class="mt-3 font-display text-3xl font-semibold text-ink lg:text-4xl">
          Tools we trust
        </h2>
        <p class="mt-4 text-sm text-ink/60">
          From field survey to the finished platform, this is the stack we rely on
          at every stage of a project.
        </p>
      </div>

      <div class="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="g in stack"
          :key="g.group"
          class="flex h-full flex-col rounded-2xl bg-panel p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
      >
          <div
            :class="g.accent"
            class="flex h-12 w-12 items-center justify-center rounded-xl border"
          >
            <svg
              viewBox="0 0 24 24"
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="g.icon" />
            </svg>
          </div>

          <h3 class="mt-5 font-display text-lg font-semibold text-ink">{{ g.group }}</h3>

          <ul class="mt-5 flex flex-wrap gap-2">
            <li
              v-for="i in g.items"
              :key="i"
              class="rounded-full border border-ink/15 bg-paper px-3 py-1.5 font-mono text-xs text-ink/70 transition-colors hover:border-ink/40 hover:text-ink"
            >
              {{ i }}
            </li>
          </ul>
        </div>
      </div>

    </div>
  </section>
</template>