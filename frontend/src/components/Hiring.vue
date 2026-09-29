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
  <section id="hiring" class="border-t border-ink/10 bg-paper py-32">
    <div class="mx-auto max-w-7xl px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">Join the team</h2>
        <p class="mt-4 text-ink/65">
          We seek passionate minds who value collaboration, who see maps as tools
          for meaningful impact, and who aspire to shape the future with us.
        </p>
      </div>

      <div class="mt-16">
        <p v-if="loading" class="text-sm text-ink/50">Loading open positions…</p>
        <p v-else-if="error" class="text-sm text-flag">{{ error }}</p>
        <p v-else-if="jobs.length === 0" class="text-sm text-ink/50">
          No open positions right now. Send your CV to
          <a :href="'mailto:' + email" class="text-river hover:underline">{{ email }}</a> anyway.
        </p>

        <div v-else class="divide-y divide-ink/10 border-y border-ink/10">
          <div
            v-for="j in jobs"
            :key="j.id"
            class="flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <h3 class="font-display text-xl font-medium text-ink">{{ j.title }}</h3>
              <p v-if="j.location" class="mt-1 font-mono text-xs text-ink/50">{{ j.location }}</p>
              <p class="mt-2 max-w-xl text-sm text-ink/65">{{ j.description }}</p>
            </div>
            
             <a :href="'mailto:' + email + '?subject=Application: ' + j.title"
              class="w-fit rounded-full border border-ink px-6 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-ink hover:text-paper">
              Apply
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>