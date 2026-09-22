<script setup lang="ts">
import bagmatiShot from '@/assets/images/bagmati-portal.webp'
import botShot from '@/assets/images/ai-bot.webp'
import exploreShot from '@/assets/images/explore-nepal-home.webp'
import { useDragScroll } from '@/composables/useDragScroll'

interface Project {
  title: string
  text: string
  tags: string[]
  image?: string
  alt?: string
  tone?: 'light'
}

interface Card extends Project {
  lead: string
  accent: string
}

const projects: Project[] = [
  {
    title: 'Plan My Nepal',
    text: 'A trip planner that maps treks, routes and destinations, then shapes them around the traveller in front of it.',
    tags: ['Travel', 'Route planning', 'Leaflet'],
    image: exploreShot,
    alt: 'Plan My Nepal interface with destination galleries and traveller onboarding',
  },
  {
    title: 'Pure Nepal',
    text: 'A tourism showcase mapping the culture, nature and heritage sites of Nepal onto one browsable map.',
    tags: ['Tourism', 'Culture', 'Web map'],
  },
  {
    title: 'FRTC',
    text: 'A spatial data platform for forest research and reporting.',
    tags: ['Forestry', 'Reporting', 'Web GIS'],
    tone: 'light',
  },
  {
    title: 'Bagmati Spatial Data Center',
    text: 'A collaborative platform where Palika authorities contribute spatial data and users explore and download datasets securely.',
    tags: ['Government', 'Data portal', 'PostGIS'],
    image: bagmatiShot,
    alt: 'Bagmati Province Spatial Data Center home page with search and dataset links',
  },
  {
    title: 'The Bot Bazar',
    text: 'A location-aware marketplace where nearby buyers and sellers meet through custom AI bots.',
    tags: ['Marketplace', 'Chatbot', 'Geolocation'],
    image: botShot,
    alt: 'The Bot Bazar dashboard listing custom chat bots',
  },
]

function splitTitle(title: string): Pick<Card, 'lead' | 'accent'> {
  const words = title.trim().split(' ')
  const accent = words.length > 1 ? (words.pop() ?? '') : ''
  return { lead: words.join(' '), accent }
}

const cards: Card[] = projects.map((project) => ({ ...project, ...splitTitle(project.title) }))

function cardClass(card: Card): string {
  if (card.tone === 'light') return 'border-ink/12 bg-panel text-ink hover:border-ink/25'
  if (!card.image) {
    return 'border-ink/10 bg-gradient-to-br from-ink via-ink to-river/55 text-paper hover:border-ink/30'
  }
  return 'border-ink/10 bg-ink text-paper hover:border-ink/30'
}

const {
  scrollRef,
  isDragging,
  canScrollPrev,
  canScrollNext,
  progress,
  activeIndex,
  scrollPrev,
  scrollNext,
} = useDragScroll()

const total = String(projects.length).padStart(2, '0')
</script>

<template>
  <section
    id="projects"
    aria-labelledby="projects-heading"
    class="relative mr-[calc(50%-50vw)] ml-[calc(50%-50vw)] w-[100vw] max-w-[100vw] border-t border-ink/10 py-24 lg:py-32"
  >
    <div class="w-full max-w-none px-8 lg:px-[6vw]">
      <header class="grid gap-8 lg:grid-cols-12 lg:items-end">
        <div class="lg:col-span-7">
          <p
            class="flex items-center gap-3 font-mono text-xs uppercase tracking-[0.32em] text-ink/65"
          >
            <span aria-hidden="true" class="h-1.5 w-1.5 rounded-full bg-river"></span>
            Selected work
          </p>
          <h2
            id="projects-heading"
            class="mt-6 text-balance font-display text-5xl font-semibold leading-[0.92] tracking-tight text-ink sm:text-6xl lg:text-7xl"
          >
            Current <span class="font-serif font-normal italic text-river">projects</span>
          </h2>
        </div>

        <div class="lg:col-span-5 lg:pb-1">
          <p class="max-w-md text-base leading-relaxed text-ink/70">
            Platforms we're actively building right now — for travellers, tourism boards, government
            data teams and local marketplaces.
          </p>
          <p class="mt-5 font-mono text-[11px] uppercase tracking-[0.2em] text-ink/65">
            ({{ total }} builds · in development)
          </p>
        </div>
      </header>

      <div
        ref="scrollRef"
        data-testid="projects-track"
        role="region"
        aria-label="Current projects"
        tabindex="0"
        class="rail mt-12 flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-river lg:mt-16 lg:gap-5"
        :class="isDragging ? 'cursor-grabbing' : 'cursor-grab'"
        @keydown.left.prevent="scrollPrev"
        @keydown.right.prevent="scrollNext"
      >
        <article
          v-for="(card, index) in cards"
          :key="card.title"
          data-project-card
          class="group flex w-[82vw] shrink-0 snap-start flex-col overflow-hidden rounded-3xl border transition-colors duration-200 ease-in-out sm:w-[calc((100%-1rem)/2)] lg:w-[calc((100%-3.75rem)/4)]"
          :class="cardClass(card)"
        >
          <div v-if="card.image" class="aspect-[16/9] shrink-0 overflow-hidden bg-ink">
            <img
              :src="card.image"
              :alt="card.alt"
              loading="lazy"
              decoding="async"
              class="h-full w-full object-cover object-top transition-transform duration-200 ease-in-out group-hover:scale-[1.03] motion-reduce:transform-none"
            />
          </div>

          <div class="flex flex-1 flex-col p-5 lg:p-6">
            <div class="flex items-center justify-between gap-4">
              <span
                class="font-mono text-[11px] tracking-[0.24em]"
                :class="card.tone === 'light' ? 'text-ink/45' : 'text-paper/45'"
              >
                {{ String(index + 1).padStart(2, '0') }}
              </span>
              <span
                class="rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em]"
                :class="
                  card.tone === 'light'
                    ? 'border-ink/15 text-ink/70'
                    : 'border-paper/25 text-paper/80'
                "
              >
                In development
              </span>
            </div>

            <div :class="card.image ? 'mt-4' : 'my-auto py-6'">
              <h3 class="font-display text-xl font-medium tracking-tight lg:text-2xl">
                {{ card.lead }}
                <span v-if="card.accent" class="font-serif font-normal italic">{{
                  card.accent
                }}</span>
              </h3>
              <p
                class="mt-3 text-sm leading-relaxed"
                :class="card.tone === 'light' ? 'text-ink/70' : 'text-paper/75'"
              >
                {{ card.text }}
              </p>
              <p
                v-if="!card.image"
                class="mt-3 font-serif text-sm italic"
                :class="card.tone === 'light' ? 'text-ink/50' : 'text-paper/55'"
              >
                Interface preview soon
              </p>
            </div>

            <ul
              class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-5 font-mono text-[10px] uppercase tracking-[0.16em]"
              :class="card.tone === 'light' ? 'text-ink/65' : 'text-paper/60'"
            >
              <li v-for="(tag, tagIndex) in card.tags" :key="tag" class="flex items-center gap-3">
                <span
                  v-if="tagIndex > 0"
                  aria-hidden="true"
                  class="h-3 w-px"
                  :class="card.tone === 'light' ? 'bg-ink/20' : 'bg-paper/25'"
                ></span>
                {{ tag }}
              </li>
            </ul>
          </div>
        </article>
      </div>

      <div class="mt-6 flex items-center gap-5">
        <div data-testid="projects-progress" class="relative h-0.5 flex-1 bg-ink/12">
          <span
            aria-hidden="true"
            class="absolute inset-y-0 left-0 bg-river transition-[width] duration-200 ease-in-out motion-reduce:transition-none"
            :style="{ width: `${Math.round(progress * 100)}%` }"
          ></span>
        </div>

        <p
          data-testid="projects-counter"
          class="shrink-0 font-mono text-[11px] tracking-[0.2em] text-ink/60"
        >
          {{ String(activeIndex + 1).padStart(2, '0') }} / {{ total }}
        </p>

        <div class="ml-auto hidden shrink-0 items-center gap-2 sm:flex">
          <button
            type="button"
            data-testid="projects-prev"
            aria-label="Previous project"
            :disabled="!canScrollPrev"
            class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-ink/20 text-ink transition-colors duration-150 ease-in-out hover:border-river hover:text-river disabled:cursor-not-allowed disabled:opacity-30"
            @click="scrollPrev"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            type="button"
            data-testid="projects-next"
            aria-label="Next project"
            :disabled="!canScrollNext"
            class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-ink/20 text-ink transition-colors duration-150 ease-in-out hover:border-river hover:text-river disabled:cursor-not-allowed disabled:opacity-30"
            @click="scrollNext"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.rail {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.rail::-webkit-scrollbar {
  display: none;
}
</style>
