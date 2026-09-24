
<template>
  <section id="hiring" class="px-8 py-20 bg-gray-50">
    <div class="max-w-6xl mx-auto">

      <!-- Section Heading -->
      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold">
          JOIN THE TEAM
        </h2>

        <p class="text-gray-500 mt-4 max-w-2xl mx-auto">
          Explore opportunities to work with us.
        </p>
      </div>


      <!-- Jobs -->
      <div class="space-y-6">

        <article
          v-for="job in jobs"
          :key="job.id"
          class="rounded-xl border bg-white p-6 hover:shadow-lg transition"
        >

          <div class="grid md:grid-cols-2 gap-8">

            <!-- Left Side -->
            <div>
              <h3 class="text-2xl font-bold">
                {{ job.title }}
              </h3>

              <p class="text-gray-500 mt-2">
                {{ job.employment_type }}
              </p>

              <p class="text-gray-600 mt-5 leading-7">
                {{ job.description }}
              </p>
            </div>


            <!-- Right Side -->
            <div class="md:border-l md:pl-8">

              <div v-if="job.requirements.length">
                <h4 class="text-lg font-semibold">
                  Requirements
                </h4>

                <ul class="mt-3 space-y-2 text-gray-600">

                  <li
                    v-for="requirement in job.requirements"
                    :key="requirement.id"
                    class="flex gap-2"
                  >
                    <span class="mt-1">•</span>

                    <span>
                      {{ requirement.text }}
                    </span>
                  </li>

                </ul>
              </div>


              <!-- Apply Button -->
              <div class="mt-6">

                <button
                  class="rounded-lg border border-gray-300 px-5 py-2 font-semibold hover:bg-gray-100 transition"
                >
                  Apply
                </button>

              </div>

            </div>

          </div>

        </article>

      </div>

    </div>
  </section>
</template>


<script setup>
import api from '../api'
import { onMounted, ref } from 'vue'

const jobs = ref([])

onMounted(async () => {
  const response = await api.get('jobs/')
  jobs.value = response.data
})
</script>

