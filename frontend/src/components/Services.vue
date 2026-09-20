<template>
  <section class="px-8 py-20 bg-white" id="services">
    <div class="max-w-6xl mx-auto">

      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold mt-2">
          OUR SERVICES
        </h2>

        <p class="text-gray-600 mt-4 max-w-2xl mx-auto">
          We provide technology solutions combining geospatial data,
          software development, and artificial intelligence.
        </p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">

        <div
          v-for="service in services"
          :key="service.id"
          class="p-6 rounded-xl border hover:shadow-lg transition-shadow duration-300"
        >
          <h3 class="text-xl font-bold mb-3">
            {{ service.title }}
          </h3>

          <p class="text-gray-600">
            {{ service.description }}
          </p>
        </div>

      </div>

    </div>
  </section>
</template>

<script setup>
import api from '../api'
import { onMounted, ref } from 'vue'

const services = ref([])

onMounted(async () => {
  const response = await api.get(
    'services/'
  )

  services.value = await response.data
})
</script>