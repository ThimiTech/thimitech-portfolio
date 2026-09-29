<script setup>
import axios from "axios"
import { ref, onMounted } from "vue"
const api=axios.create({ 
    baseURL: "https://planmynepal.com/api/"
})
const planmynepal = ref([])

const getActivity = async () => {
  try {
    const res = await api.get("activity/")

    console.log(res.data)

    planmynepal.value = res.data
  } catch (error) {
    console.log(error)
  }
}

onMounted(() => {
  getActivity()
})
</script>

<template>

  <div class="min-h-screen bg-gray-100 px-6 py-10">

    <!-- Page Title -->
    <div class="mx-auto mb-8 max-w-7xl">
      <h1 class="text-3xl font-bold text-gray-800">
        Activities
      </h1>

      <p class="mt-2 text-gray-500">
        Explore different activities in Nepal
      </p>
    </div>


    <!-- OUTER LOOP -->
    <div
      class="mx-auto grid max-w-7xl gap-6 sm:grid-cols-2 lg:grid-cols-3"
    >

      <div
        v-for="activity in planmynepal"
        :key="activity.id"
        class="overflow-hidden rounded-2xl bg-white shadow-md transition hover:-translate-y-1 hover:shadow-xl"
      >

        <!-- Activity Image -->
        <img
          :src="activity.cover_image"
          :alt="activity.name"
          class="h-52 w-full object-cover"
        />


        <!-- Card Content -->
        <div class="p-5">

          <!-- Activity Name -->
          <h2 class="text-2xl font-bold text-gray-800">
            {{ activity.name }}
          </h2>


          <!-- Description -->
          <p class="mt-2 line-clamp-3 text-sm leading-6 text-gray-600">
            {{ activity.description }}
          </p>


          <!-- Destination -->
          <div class="mt-4">
            <p class="text-sm text-gray-500">
              Destination
            </p>

            <p class="font-semibold text-gray-800">
              {{ activity.destination.name }}
            </p>
          </div>


          <!-- Activity Type -->
          <div class="mt-3">
            <p class="text-sm text-gray-500">
              Activity Type
            </p>

            <p class="font-semibold text-gray-800">
              {{ activity.activity_type.name }}
            </p>
          </div>


          <!-- Duration + Difficulty -->
          <div class="mt-4 flex gap-3">

            <div class="rounded-lg bg-gray-100 px-3 py-2">
              <p class="text-xs text-gray-500">
                Duration
              </p>

              <p class="font-semibold text-gray-800">
                {{ activity.duration }}
              </p>
            </div>


            <div class="rounded-lg bg-gray-100 px-3 py-2">
              <p class="text-xs text-gray-500">
                Difficulty
              </p>

              <p class="font-semibold text-gray-800">
                {{ activity.difficulty_level }}
              </p>
            </div>

          </div>


          <!-- INNER LOOP -->
          <div class="mt-5">

            <h3 class="mb-2 font-semibold text-gray-800">
              Pricing
            </h3>

            <div
              v-for="price in activity.pricing"
              :key="price.id"
              class="mb-2 rounded-lg border border-gray-200 p-3"
            >

              <div class="flex items-center justify-between">

                <div>
                  <p class="font-medium text-gray-800">
                    {{ price.nationality }}
                  </p>

                  <p class="text-sm text-gray-500">
                    {{ price.age_group }}
                  </p>
                </div>


                <p class="font-bold text-gray-800">
                  {{ price.currency }} {{ price.price }}
                </p>

              </div>

            </div>

          </div>


          <!-- Provider -->
          <div class="mt-4 border-t pt-4">

            <p class="text-xs text-gray-500">
              Provided by
            </p>

            <p class="font-semibold text-gray-800">
              {{ activity.provider }}
            </p>

          </div>

        </div>

      </div>

    </div>

  </div>

</template>