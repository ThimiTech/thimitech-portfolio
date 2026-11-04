<script setup lang="ts">
defineOptions({ name: 'OriginalServices' })

import { onMounted, ref } from 'vue'
import api from '../../api/api'

interface Service {
  id: number
  title: string
  description: string
}

const services = ref<Service[]>([])
const loading = ref(true)
const error = ref('')

const getServices = async () => {
  try {
    const res = await api.get('services/')
    services.value = res.data
  } catch (err) {
    error.value = 'Could not load services right now.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(getServices)
</script>

<template>
  <section id="services" class="min-h-screen border-t border-ink/10 bg-paper px-6 py-10">

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
        <h3 class="line-clamp-2 font-display text-lg font-semibold text-ink">
          {{ s.title }}
        </h3>

        <p class="mt-3 line-clamp-4 text-sm leading-6 text-ink/65">
          {{ s.description }}
        </p>
      </article>

    </div>

    <!-- Empty State -->
    <div
      v-if="services.length === 0"
      class="py-20 text-center text-ink/50"
    >
      No services found.
    </div>

  </section>
</template>