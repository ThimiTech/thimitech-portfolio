<script setup lang="ts">
const values = [
  {
    title: 'Data first',
    text: 'Every decision starts from accurate, well-structured spatial data — not assumptions.',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    accent: 'text-river border-river/30 bg-river/5',
  },
  {
    title: 'Built for use',
    text: 'We design maps for the people who open them every day, not just for a demo.',
    icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
    accent: 'text-contour border-contour/30 bg-contour/5',
  },
  {
    title: 'Local context',
    text: "We build for Nepal's geography, infrastructure and the way our clients actually work.",
    icon: 'M12 21c-4.5-4.5-7-8.25-7-11.5A7 7 0 0112 2a7 7 0 017 7.5c0 3.25-2.5 7-7 11.5zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z',
    accent: 'text-flag border-flag/30 bg-flag/5',
  },
  {
    title: 'Built to last',
    text: 'We choose stable, well-supported tools over trends, so what we ship keeps working for years.',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4',
    accent: 'text-river border-river/30 bg-river/5',
  },
  {
    title: 'Open by default',
    text: 'We work in the open with our clients — shared progress, honest timelines, no black boxes.',
    icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
    accent: 'text-contour border-contour/30 bg-contour/5',
  },
  {
    title: 'People over platforms',
    text: 'Technology is the tool, not the goal — every project starts with the person who will use it.',
    icon: 'M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-2.13a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4',
    accent: 'text-flag border-flag/30 bg-flag/5',
  },
]
</script>

<template>
  <section id="mission" class="border-t border-ink/10 bg-paper px-10 py-10">
    <div class="mx-auto max-w-none">

      <div class="max-w-2xl">
       <h2 class="font-display text-3xl font-bold text-ink lg:text-4xl">Our Mission</h2>
        <h2 class="mt-3 font-display text-2xl font-semibold text-ink lg:text-2xl">
          Make Nepal's geography easy to see, search and act on.
        </h2>
        <p class="mt-4 text-ink/65">
          Too much spatial data in Nepal sits locked in spreadsheets and paper records.
          We build the maps and platforms that put it in front of the people who need it.
        </p>
      </div>

      <div class="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="v in values"
          :key="v.title"
         class="flex h-full flex-col rounded-2xl bg-panel p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
      >
          <div
            :class="v.accent"
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
              <path :d="v.icon" />
            </svg>
          </div>

          <h3 class="mt-5 font-display text-base font-medium text-ink">{{ v.title }}</h3>
          <p class="mt-2 text-sm text-ink/65">{{ v.text }}</p>
        </div>
      </div>

    </div>
  </section>
</template>