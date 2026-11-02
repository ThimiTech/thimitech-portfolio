<script setup lang="ts">
defineOptions({ name: 'StudioStack' })

import { ICONS } from '../data/icons'

const groups = [
  {
    icon: ICONS.map,
    title: 'Mapping in the browser',
    tools: ['Leaflet', 'MapLibre GL', 'OpenLayers', 'Vue 3', 'TypeScript'],
  },
  {
    icon: ICONS.database,
    title: 'Servers & databases',
    tools: ['PostGIS', 'GeoServer', 'Node.js', 'Docker'],
  },
  {
    icon: ICONS.chart,
    title: 'Data & analysis',
    tools: ['QGIS', 'GDAL', 'Python', 'Vector tiles'],
  },
  {
    icon: ICONS.mobile,
    title: 'Field data & mobile',
    tools: ['ODK Collect', 'KoboToolbox', 'GPS survey'],
  },
  {
    icon: ICONS.cloud,
    title: 'Cloud & deployment',
    tools: ['AWS', 'Nginx', 'GitHub Actions', 'Linux'],
  },
  {
    icon: ICONS.code,
    title: 'Design & frontend',
    tools: ['Figma', 'Tailwind CSS', 'Vite', 'D3.js'],
  },
]
</script>

<template>
  <section id="stack" class="stack" aria-labelledby="stack-title">
    <div class="studio-wrap studio-section">
      <header class="section-head">
        <div>
          <p class="studio-kicker">Stack</p>
          <h2 id="stack-title">Tools we trust</h2>
        </div>
        <p class="section-intro">
          From field survey to the finished platform, this is the stack we rely on at every stage of
          a project.
        </p>
      </header>

      <div class="card-grid">
        <article v-for="group in groups" :key="group.title" class="card stack-card">
          <span class="icon-badge" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="group.icon" />
            </svg>
          </span>
          <h3>{{ group.title }}</h3>
          <ul class="chip-list">
            <li v-for="tool in group.tools" :key="tool" class="chip">{{ tool }}</li>
          </ul>
        </article>
      </div>

      <p class="section-note">
        <strong>Toolchain reviewed per project.</strong> We would rather use what your team can
        maintain after we hand over than force a stack on you — and when a project needs something
        we have not used before, we say so before we start.
      </p>
    </div>
  </section>
</template>

<style scoped>
.stack {
  background: #ffffff;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.stack-card {
  gap: 18px;
  background: #f5f6f7;
  border-color: transparent;
}

.stack-card:hover {
  border-color: transparent;
  box-shadow: none;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.chip {
  background: #ffffff;
}

@media (max-width: 1023px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
