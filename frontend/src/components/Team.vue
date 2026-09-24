<template>
  <section id="team" class="px-8 py-20 bg-gray-50">
    <div class="max-w-6xl mx-auto">

      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold">
          OUR TEAM
        </h2>

        <p class="text-gray-500 mt-4 max-w-2xl mx-auto">
          Meet the people behind our technology and geospatial solutions.
        </p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">

        <article
          v-for="member in team"
          :key="member.id"
          class="rounded-xl border bg-white p-6 text-center hover:shadow-xl transition"
        >

          <img
            v-if="member.image"
            :src="`http://127.0.0.1:8000${member.image}`"
            :alt="member.name"
            class="mx-auto h-32 w-32 rounded-full object-cover"
          />

          <div
            v-else
            class="mx-auto flex h-32 w-32 items-center justify-center rounded-full bg-gray-200 text-2xl font-bold"
          >
            {{ member.initials }}
          </div>

          <h3 class="text-xl font-bold mt-5">
            {{ member.name }}
          </h3>

          <p class="text-gray-500 mt-1">
            {{ member.role }}
          </p>

          <div
            v-if="member.social_media.length"
            class="flex justify-center gap-4 mt-5"
          >
            <a
              v-for="social in member.social_media"
              :key="social.id"
              :href="social.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-gray-500 hover:text-blue-600"
            >
              {{ social.platform }}
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

const team = ref([])

onMounted(async () => {
  const response = await api.get('team/')
  team.value = response.data
})
</script>