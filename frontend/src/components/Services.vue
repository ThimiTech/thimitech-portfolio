<script setup lang="ts">
import { useApiCollection } from '../composables/useApiCollection'

interface Service {
  id: number
  title: string
  description: string
}
const { items: services, visible } = useApiCollection<Service>('services/')
</script>

<template>
  <section v-if="visible" id="services" class="border-t border-ink/10 bg-paper px-6 py-10">

    <!-- Header -->
    <div class="mx-auto max-w-7xl">
      <h2 class="font-display text-3xl font-bold text-ink lg:text-4xl">
        What we build
      </h2>

      <p class="mt-2 text-ink/60">
        A focused set of services, from the first line of data to the finished platform.
      </p>
    </div>
    <!-- Services -->
    <div
      class="mx-auto mt-8 grid max-w-7xl grid-cols-1 items-stretch gap-6 sm:grid-cols-2 lg:grid-cols-4"
    >

      <!-- SERVICE LOOP -->
      <article
        v-for="s in services"
        :key="s.id"
        class="flex h-full flex-col rounded-2xl bg-paper p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
      >

        <!-- Icon -->
        <div
          class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-river/10 text-river"
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
            <path
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
          </svg>
        </div>

        <!-- Service Content -->
        <div class="flex flex-1 flex-col">

          <!-- Title -->
          <h3 class="mt-5 line-clamp-2 font-display text-lg font-semibold text-ink">
            {{ s.title }}
          </h3>

          <!-- Description -->
          <p
            class="mt-3 line-clamp-4 text-sm leading-6 text-ink/65"
          >
            {{ s.description }}
          </p>

          <!-- Spacer -->
          <div class="flex-1"></div>

          <!-- Bottom Indicator -->
          <div class="mt-6 flex items-center gap-2 text-xs font-medium text-river">
            <span class="h-1.5 w-1.5 rounded-full bg-river"></span>
            Our Service
          </div>

        </div>
      </article>

    </div>


  </section>
</template>