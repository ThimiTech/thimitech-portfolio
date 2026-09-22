<script setup lang="ts">
const openings = [
  { title: 'Frontend Engineer (Vue)', type: 'Full-time · Kathmandu', text: 'Build the interfaces our clients use every day, working closely with our GIS team.' },
  { title: 'GIS Analyst', type: 'Full-time · Kathmandu', text: 'Prepare, clean and analyse spatial data for client projects across Nepal.' },
]
const email = 'info@thimitech.com'
</script>

<template>
  <section id="hiring" class="border-t border-ink/10 bg-paper py-24">
    <div class="mx-auto max-w-6xl px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">Join the team</h2>
        <p class="mt-4 text-ink/65">We seek passionate minds who value collaboration,
        who see maps as tools for meaningful impact,
        and who aspire to shape the future with us.</p>
      </div>

      <div class="mt-12 divide-y divide-ink/10 border-y border-ink/10">
        <div v-for="o in openings" :key="o.title" class="flex flex-col gap-2 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 class="font-display text-lg font-medium text-ink">{{ o.title }}</h3>
            <p class="mt-1 font-mono text-xs text-ink/50">{{ o.type }}</p>
            <p class="mt-2 max-w-md text-sm text-ink/65">{{ o.text }}</p>
          </div>
          
            <a :href="'mailto:' + email + '?subject=Application: ' + o.title"
            class="w-fit rounded-full border border-ink px-5 py-2 text-sm font-medium text-ink transition-colors hover:bg-ink hover:text-paper"
          >
            Apply
          </a>
        </div>
      </div>

      <p class="mt-8 text-sm text-ink/60">
        Don't see a fit? Send your CV to <a :href="'mailto:' + email" class="text-river hover:underline">{{ email }}</a> anyway.
      </p>
    </div>
  </section>
</template>