<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/api'

interface Job {
  id: number
  title: string
  location?: string
  description: string
}

const jobs = ref<Job[]>([])
const loading = ref(true)
const error = ref('')
const email = 'info@thimitech.com'

const getJobs = async () => {
  try {
    const res = await api.get('jobs/')
    jobs.value = res.data
  } catch (err) {
    error.value = 'Could not load open positions right now.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(getJobs)
</script>

<template>
  <section
    id="hiring"
    class="min-h-screen border-t border-ink/10 bg-paper px-6 py-10"
  >
    <div class="mx-auto max-w-7xl">

      <!-- Section Heading -->
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-bold text-ink lg:text-4xl">
          Join the team
        </h2>

        <p class="mt-2 text-ink/60">
          We seek passionate minds who value collaboration,
          who see maps as tools for meaningful impact,
          and who aspire to shape the future with us.
        </p>
      </div>

      <!-- Jobs -->
      <div class="mt-8 space-y-6">

        <!-- JOB LOOP -->
        <article
          v-for="job in jobs"
          :key="job.id"
          class="overflow-hidden rounded-2xl bg-paper shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
        >

          <div class="grid md:grid-cols-2">

            <!-- LEFT SIDE -->
            <div class="p-6 lg:p-7">

              <!-- Job Title -->
              <h3
                class="font-display text-xl font-bold text-ink"
              >
                {{ job.title }}
              </h3>

              <!-- Employment Type -->
              <span
                class="mt-2 inline-flex rounded-full bg-river/10 px-3 py-1 font-mono text-xs font-medium text-river"
              >
                {{ job.employment_type }}
              </span>

              <!-- Description -->
              <p
                class="mt-5 max-w-xl text-sm leading-6 text-ink/65"
              >
                {{ job.description }}
              </p>

            </div>

            <!-- RIGHT SIDE -->
            <div
              class="border-t border-ink/10 p-6 md:border-l md:border-t-0 lg:p-7"
            >

              <!-- Requirements -->
              <div
                v-if="job.requirements && job.requirements.length"
              >
                <h4
                  class="font-display text-lg font-semibold text-ink"
                >
                  Requirements
                </h4>

                <ul
                  class="mt-4 space-y-3"
                >

                  <!-- REQUIREMENTS LOOP -->
                  <li
                    v-for="requirement in job.requirements"
                    :key="requirement.id"
                    class="flex gap-3 text-sm leading-5 text-ink/65"
                  >
                    <span
                      class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-river"
                    ></span>

                    <span>
                      {{ requirement.text }}
                    </span>
                  </li>

                </ul>
              </div>

              <!-- No Requirements -->
              <p
                v-else
                class="text-sm text-ink/50"
              >
                No specific requirements listed.
              </p>

              <!-- Apply Button -->
              <div class="mt-6">

                <button
                  @click="handleApply(job)"
                  class="w-full rounded-lg bg-ink px-4 py-3 text-sm font-semibold text-paper transition hover:opacity-90"
                >
                  Apply for this position →
                </button>

              </div>

            </div>

          </div>

        </article>

      </div>

      <!-- General Application -->
      <p class="mt-8 text-sm text-ink/60">
        Don't see a fit? Send your CV to

        <a
          :href="'mailto:' + email"
          class="font-medium text-river hover:underline"
        >
          {{ email }}
        </a>

        anyway.
      </p>

    </div>

    <!-- Login -->
    <Login
      :open="showLogin"
      @close="showLogin = false"
      @loginSuccess="showLogin = false; showApplicationForm = true"
    />

  </section>
</template>