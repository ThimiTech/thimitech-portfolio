<script setup lang="ts">
const services = [
  {
    title: 'Web Mapping',
    text: 'Interactive maps for viewing, searching and sharing location data — built for the people who use them.',
    icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
    tile: 'bg-river/10 text-river',
  },
  {
    title: 'Spatial Analysis',
    text: 'Turning raw geographic data into land-use, risk and suitability insight your team can act on.',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    tile: 'bg-contour/10 text-contour',
  },
  {
    title: 'GIS Data Management',
    text: 'Clean, structured spatial databases that stay accurate and reliable as your data grows.',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4',
    tile: 'bg-flag/10 text-flag',
  },
  {
    title: 'Custom GIS Applications',
    text: 'Full web platforms — dashboards, portals and field tools — shaped around your workflow.',
    icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
    tile: 'bg-ink/10 text-ink',
  },
]
</script>

<template>
  <section id="services" class="border-t border-ink/10 py-24">
    <div class="px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">What we build</h2>
        <p class="mt-4 text-ink/65">A focused set of services, from the first line of data to the finished platform.</p>
      </div>

      <div class="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="s in services"
          :key="s.title"
          class="rounded-2xl border border-ink/10 bg-paper p-7 transition-shadow hover:shadow-[0_8px_24px_rgba(14,27,42,0.08)]"
        >
          <div class="flex h-11 w-11 items-center justify-center rounded-xl" :class="s.tile">
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path :d="s.icon" />
            </svg>
          </div>
          <h3 class="mt-6 font-display text-lg font-medium text-ink">{{ s.title }}</h3>
          <p class="mt-2 text-sm leading-relaxed text-ink/65">{{ s.text }}</p>
        </div>
      </div>
    </div>
  </section>
</template>