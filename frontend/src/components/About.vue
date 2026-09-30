<script setup lang="ts">
const facts = [
  {
    k: 'Founded',
    v: '2021',
    icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    accent: 'text-river border-river/30 bg-river/5',
  },
  {
    k: 'Based in',
    v: 'Kathmandu, Nepal',
    icon: 'M12 21c-4.5-4.5-7-8.25-7-11.5A7 7 0 0112 2a7 7 0 017 7.5c0 3.25-2.5 7-7 11.5zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z',
    accent: 'text-contour border-contour/30 bg-contour/5',
  },
  {
    k: 'Team',
    v: '4 people',
    icon: 'M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-2.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4',
    accent: 'text-flag border-flag/30 bg-flag/5',
  },
  {
    k: 'Focus',
    v: 'Web GIS & spatial data',
    icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
    accent: 'text-river border-river/30 bg-river/5',
  },
]

const stats = [
  { value: '4+', label: 'Years mapping' },
  { value: '12+', label: 'Platforms shipped' },
  { value: '77', label: 'Districts covered' },
]
</script>

<template>
  <section id="about" class="border-t border-ink/10 bg-paper py-32">
    <div class="mx-auto max-w-7xl px-6">

      <div class="grid gap-14 lg:grid-cols-[1.15fr_1fr] lg:items-start">

        <div>
          <p class="font-mono text-xs uppercase tracking-wide text-river">About us</p>
          <h2 class="mt-3 font-display text-3xl font-semibold leading-snug text-ink lg:text-4xl">
            Built by people who read maps for a living.
          </h2>

          <p class="mt-6 max-w-xl text-ink/65">
            Thimitech started as a two-person GIS consultancy mapping flood risk for a
            local ward office. Today we build full web platforms — mapping, data pipelines
            and the interfaces on top — for tourism boards, municipalities and startups
            who need their data to live on a map, not in a spreadsheet.
          </p>
          <p class="mt-4 max-w-xl text-ink/65">
            We work in small teams, ship in two-week cycles, and keep every client in
            the room while the map is still being drawn.
          </p>

          <div class="mt-10 grid grid-cols-3 gap-6 border-t border-ink/10 pt-8">
            <div v-for="s in stats" :key="s.label">
              <p class="font-display text-3xl font-semibold text-ink">{{ s.value }}</p>
              <p class="mt-1 text-xs text-ink/55">{{ s.label }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-ink/10 bg-panel p-8">
          <div class="grid grid-cols-2 gap-8">
            <div v-for="f in facts" :key="f.k">
              <div :class="f.accent" class="flex h-10 w-10 items-center justify-center rounded-lg border">
                <svg
                  viewBox="0 0 24 24"
                  class="h-4.5 w-4.5"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path :d="f.icon" />
                </svg>
              </div>
              <p class="mt-3 font-mono text-xs uppercase tracking-wide text-ink/45">{{ f.k }}</p>
              <p class="mt-1 font-mono text-lg font-medium text-ink">{{ f.v }}</p>
            </div>
          </div>
        </div>

      </div>

    </div>
  </section>
</template>
