<script setup lang="ts">
const stack = [
  {
    group: 'Mapping in the browser',
    items: [
      { name: 'Leaflet', use: 'interactive maps' },
      { name: 'MapLibre GL', use: 'vector rendering' },
      { name: 'OpenLayers', use: 'advanced GIS' },
      { name: 'Vue 3', use: 'interfaces' },
      { name: 'TypeScript', use: 'reliable code' },
    ],
  },
  {
    group: 'Servers & databases',
    items: [
      { name: 'PostGIS', use: 'spatial storage' },
      { name: 'GeoServer', use: 'map services' },
      { name: 'Node.js', use: 'APIs' },
      { name: 'Docker', use: 'deployments' },
    ],
  },
  {
    group: 'Data & analysis',
    items: [
      { name: 'QGIS', use: 'desktop GIS' },
      { name: 'GDAL', use: 'data conversion' },
      { name: 'Python', use: 'automation' },
      { name: 'Vector tiles', use: 'fast delivery' },
    ],
  },
]

const totalTools = stack.reduce((sum, group) => sum + group.items.length, 0)
</script>

<template>
  <section
    id="stack"
    aria-labelledby="stack-heading"
    class="flex -mx-8 flex-col justify-between gap-10 border-t border-ink/10 bg-panel px-8 py-16 lg:-mx-[6vw] lg:min-h-[60svh] lg:px-[6vw] lg:py-12"
  >
    <header class="grid gap-8 lg:grid-cols-12 lg:items-end">
      <div class="lg:col-span-7">
        <p
          class="flex items-center gap-3 font-mono text-xs uppercase tracking-[0.32em] text-ink/65"
        >
          <span aria-hidden="true" class="h-1.5 w-1.5 rounded-full bg-river"></span>
          Our toolkit
        </p>
        <h2
          id="stack-heading"
          class="mt-6 text-balance font-display text-5xl font-semibold leading-[0.92] tracking-tight text-ink sm:text-6xl lg:text-7xl"
        >
          Tools we <span class="font-serif font-normal italic text-river">trust</span>
        </h2>
      </div>

      <div class="lg:col-span-5 lg:pb-1">
        <p class="max-w-md text-base leading-relaxed text-ink/70">
          Open source first, chosen for the long run — so maps stay fast, data stays portable, and
          the interface stays out of the way.
        </p>
        <div
          class="mt-5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 font-mono text-[11px] uppercase tracking-[0.2em] text-ink/65"
        >
          <p>({{ String(totalTools).padStart(2, '0') }} tools · in production)</p>
          <a
            href="#projects"
            class="inline-flex items-center gap-1.5 text-river transition-colors duration-150 ease-in-out hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-river"
          >
            See it in our work
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-3 w-3"
              aria-hidden="true"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </div>
    </header>

    <div class="grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
      <article v-for="(group, index) in stack" :key="group.group" class="group flex flex-col">
        <div class="relative flex items-baseline justify-between gap-4 border-t border-ink/15 pt-4">
          <h3 class="font-display text-lg font-medium tracking-tight text-ink lg:text-xl">
            {{ group.group }}
          </h3>
          <span
            class="font-mono text-[11px] tracking-[0.2em] text-ink/65 transition-colors duration-150 ease-in-out group-hover:text-river motion-reduce:transition-none"
          >
            {{ String(index + 1).padStart(2, '0') }}
          </span>
          <span
            aria-hidden="true"
            class="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-river transition-transform duration-200 ease-in-out group-hover:scale-x-100 motion-reduce:transition-none"
          ></span>
        </div>

        <ul class="mt-3">
          <li
            v-for="tool in group.items"
            :key="tool.name"
            class="flex items-baseline justify-between gap-4 border-b border-ink/10 py-2 last:border-b-0"
          >
            <span class="font-display text-base font-medium text-ink">{{ tool.name }}</span>
            <span class="shrink-0 font-mono text-[11px] tracking-[0.08em] text-ink/65">
              {{ tool.use }}
            </span>
          </li>
        </ul>
      </article>
    </div>
  </section>
</template>
