<script setup lang="ts">
const tools = [
  { title: 'Mapping', names: 'QGIS / PostGIS / Leaflet / MapLibre' },
  { title: 'Engineering', names: 'Python / Django / Vue / TypeScript' },
  { title: 'Delivery', names: 'Docker / Linux / GitHub Actions' },
]
</script>
<template><section id="stack" class="studio-wrap studio-section stack-section"><h2>Good tools.<br>Thoughtfully applied.</h2><div class="stack-list"><div v-for="t in tools" :key="t.title"><h3>{{ t.title }}</h3><p>{{ t.names }}</p></div></div></section></template>
