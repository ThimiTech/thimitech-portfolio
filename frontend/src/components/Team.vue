<script setup lang="ts">
import { useApiCollection } from '../composables/useApiCollection'

interface Member {
  id: number
  name: string
  role: string
  photo?: string | null
}
const { items: team, visible } = useApiCollection<Member>('team/')

const colors = [
  'from-river to-emerald-500',
  'from-ink to-river',
  'from-contour to-flag',
]

const initials = (name: string) =>
  name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

</script>

<template>
  <section v-if="visible" id="team" class="border-t border-ink/10 bg-paper py-32">
    <div class="mx-auto max-w-7xl px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">The team</h2>
        <p class="mt-4 text-ink/65">
          A collective of engineers and innovators, driven by precision and purpose,
          building geospatial solutions that inspire progress.
        </p>
      </div>

      <div class="mt-16">

        <div class="grid grid-cols-1 gap-8 sm:grid-cols-3">
          <div
            v-for="(m, i) in team"
            :key="m.id"
            class="flex flex-col items-center rounded-3xl border border-ink/10 bg-panel px-6 py-16 text-center"
          >
            <img
              v-if="m.photo"
              :src="m.photo"
              :alt="m.name"
              class="h-36 w-36 rounded-full object-cover"
            />
            <div
              v-else
              :class="colors[i % colors.length]"
              class="flex h-36 w-36 items-center justify-center rounded-full bg-gradient-to-br font-display text-5xl font-semibold text-paper"
            >
              {{ initials(m.name) }}
            </div>
            <h3 class="mt-8 font-display text-2xl font-medium text-ink">{{ m.name }}</h3>
            <p class="mt-2 font-mono text-sm tracking-wide text-ink/60">{{ m.role }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>