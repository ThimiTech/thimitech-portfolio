<script setup lang="ts">
const projects = [
  {
    title: 'Plan My Nepal',
    status: 'In development',
    text: 'A trip-planning platform that maps treks, routes and destinations across Nepal.',
    tags: ['Travel', 'Route planning', 'Leaflet'],
    art: 'bg-gradient-to-br from-flag to-contour',
  },
  {
    title: 'Pure Nepal',
    status: 'In development',
    text: 'A tourism showcase mapping the culture, nature and heritage sites of Nepal.',
    tags: ['Tourism', 'Culture', 'Web map'],
    art: 'bg-gradient-to-br from-river to-emerald-500',
  },
  {
    title: 'The Bot Bazar',
    status: 'In development',
    text: 'A location-aware online marketplace connecting nearby buyers and sellers.',
    tags: ['Marketplace', 'Chatbot', 'Geolocation'],
    art: 'bg-gradient-to-br from-ink to-river',
  },
]
</script>

<template>
  <section id="projects" class="border-t border-ink/10 bg-panel py-32">
    <div class="mx-auto max-w-7xl px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">Current Projects</h2>
        <p class="mt-4 text-ink/65">Platforms we're actively building right now.</p>
      </div>

      <div class="mt-12 grid gap-6 sm:grid-cols-2">
        <article
          v-for="p in projects"
          :key="p.title"
          class="overflow-hidden rounded-2xl border border-ink/12 bg-paper transition-shadow hover:shadow-[0_8px_24px_rgba(14,27,42,0.08)]"
        >
          <div :class="p.art" class="h-36"></div>
          <div class="p-6">
            <span class="inline-flex w-fit items-center gap-1.5 rounded-full border border-ink/15 px-3 py-1 font-mono text-[11px] text-ink/60">
              <span class="h-1.5 w-1.5 rounded-full bg-river"></span>
              {{ p.status }}
            </span>
            <h3 class="mt-3 font-display text-xl font-medium text-ink">{{ p.title }}</h3>
            <p class="mt-2 text-sm text-ink/65">{{ p.text }}</p>
            <ul class="mt-4 flex flex-wrap gap-2 font-mono text-[11px]">
              <li v-for="t in p.tags" :key="t" class="rounded-full border border-ink/20 px-2.5 py-1 text-ink/55">{{ t }}</li>
            </ul>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>