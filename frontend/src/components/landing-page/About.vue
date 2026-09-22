<script setup lang="ts">
const facts = [
  { k: 'Founded', v: '2021' },
  { k: 'Based in', v: 'Kathmandu, Nepal' },
  { k: 'Team', v: '9 people' },
  { k: 'Focus', v: 'Web GIS & spatial data' },
]
</script>

<template>
  <section id="about" class="border-t border-ink/10 py-24">
    <div class="grid gap-12 px-6 lg:grid-cols-[1.2fr_1fr]">
      <div>
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">Built by people who read maps for a living.</h2>
        <p class="mt-6 max-w-xl text-ink/70">
          Thimitech started as a two-person GIS consultancy mapping flood risk for a
          local ward office. Today we build full web platforms — mapping, data pipelines
          and the interfaces on top — for tourism boards, municipalities and startups
          who need their data to live on a map, not in a spreadsheet.
        </p>
        <p class="mt-4 max-w-xl text-ink/70">
          We work in small teams, ship in two-week cycles, and keep every client in
          the room while the map is still being drawn.
        </p>
      </div>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-8 self-start rounded-2xl border border-ink/15 bg-panel p-8 font-mono">
        <div v-for="f in facts" :key="f.k">
          <dt class="text-xs text-ink/50">{{ f.k }}</dt>
          <dd class="mt-1 text-lg font-medium text-ink">{{ f.v }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>