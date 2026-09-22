<script setup lang="ts">
const values = [
  { title: 'Data first', text: 'Every decision starts from accurate, well-structured spatial data — not assumptions.' },
  { title: 'Built for use', text: 'We design maps for the people who open them every day, not just for a demo.' },
  { title: 'Local context', text: "We build for Nepal's geography, infrastructure and the way our clients actually work." },
]
</script>

<template>
  <section id="mission" class="border-t border-ink/10 bg-panel py-24">
    <div class="px-6">
      <div class="max-w-2xl">
        <p class="font-mono text-xs uppercase tracking-wide text-river">Our mission</p>
        <h2 class="mt-3 font-display text-3xl font-semibold text-ink lg:text-4xl">
          Make Nepal's geography easy to see, search and act on.
        </h2>
        <p class="mt-4 text-ink/65">
          Too much spatial data in Nepal sits locked in spreadsheets and paper records.
          We build the maps and platforms that put it in front of the people who need it.
        </p>
      </div>

      <div class="mt-12 grid gap-6 sm:grid-cols-3">
        <div v-for="v in values" :key="v.title" class="rounded-2xl border border-ink/10 bg-paper p-6">
          <h3 class="font-display text-base font-medium text-ink">{{ v.title }}</h3>
          <p class="mt-2 text-sm text-ink/65">{{ v.text }}</p>
        </div>
      </div>
    </div>
  </section>
</template>