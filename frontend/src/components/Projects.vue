<template>
  <section class="px-8 py-20 bg-white " id="projects">
    <div class="max-w-6xl mx-auto">

      <!-- Heading -->
      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold">
          OUR PROJECTS
        </h2>

        <p class="text-gray-600 mt-4 max-w-2xl mx-auto">
          Focus on scalable, intuitive solutions that drive real-world impact.
        </p>
      </div>

      <!-- Projects -->
      <div class="grid md:grid-cols-2 gap-8">

        <article
          v-for="project in projects"
          :key="project.id"
          class="rounded-xl overflow-hidden border bg-white hover:shadow-xl transition"
        >

          <!-- Image -->
          <img
            v-if="project.image"
            :src="`http://127.0.0.1:8000${project.image}`"
            :alt="project.name"
            class="w-full h-64 object-cover"
          />

          <!-- Content -->
          <div class="p-6">

            <h3 class="text-2xl font-bold">
              {{ project.name }}
            </h3>

            <p class="text-gray-500 mt-2">
              {{ project.subtitle }}
            </p>

            <p class="text-gray-600 mt-4">
              {{ project.description }}
            </p>

            <!-- Project link -->
            <a
              v-if="project.url"
              :href="project.url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-block mt-6 font-semibold hover:underline"
            >
              View Project →
            </a>

          </div>
        </article>

      </div>

    </div>
  </section>
</template>

<script setup>
import api from '../api'
import { onMounted, ref } from 'vue'

const projects = ref([])

onMounted(async () => {
  const response = await api.get(
    'projects/'
  )

  projects.value = await response.data
})
</script>