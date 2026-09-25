<script setup lang="ts">
const steps = [
  { title: 'Understand the question', text: 'We learn what your team needs to decide, and which data and users are involved.' },
  { title: 'Prepare the data', text: 'We check quality, fix projections and load everything into one clean database.' },
  { title: 'Build and review', text: 'You see a working map every two weeks, while feedback is still cheap to act on.' },
  { title: 'Launch and support', text: 'We deploy, train your team, and stay on for updates and new layers.' },
]
</script>

<template>
  <section id="process" class="border-t border-ink/10 bg-paper py-32">
    <div class="mx-auto max-w-[1280px] px-6">
      <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">How a project runs</h2>
      <ol class="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <li v-for="(s, i) in steps" :key="s.title" class="border-t-2 border-ink pt-4">
          <span class="font-mono text-sm text-river">{{ String(i + 1).padStart(2, '0') }}</span>
          <h3 class="mt-2 font-display text-lg font-medium text-ink">{{ s.title }}</h3>
          <p class="mt-2 text-sm text-ink/70">{{ s.text }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>