<script setup lang="ts">
const stack = [
  { group: 'Mapping in the browser', items: ['Leaflet', 'MapLibre GL', 'OpenLayers', 'Vue 3', 'TypeScript'] },
  { group: 'Servers & databases', items: ['PostGIS', 'GeoServer', 'Node.js', 'Docker'] },
  { group: 'Data & analysis', items: ['QGIS', 'GDAL', 'Python', 'Vector tiles'] },
]
</script>

<template>
  <section id="stack" class="border-t border-ink/10 bg-paper py-24">
    <div class="mx-auto max-w-6xl px-6">
      <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">Tools we trust</h2>
      <div class="mt-12 grid gap-10 sm:grid-cols-3">
        <div v-for="g in stack" :key="g.group">
          <h3 class="border-b border-ink/15 pb-3 font-medium text-ink">{{ g.group }}</h3>
          <ul class="mt-4 flex flex-wrap gap-2 font-mono text-sm">
            <li v-for="i in g.items" :key="i" class="rounded-full border border-ink/20 px-3 py-1 text-ink/70">{{ i }}</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>