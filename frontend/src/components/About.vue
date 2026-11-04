<script setup lang="ts">
defineOptions({ name: 'StudioAbout' })

import { ICONS } from '../data/icons'

const facts = [
  { icon: ICONS.target, label: 'Founded', value: '2021' },
  { icon: ICONS.pin, label: 'Based in', value: 'Bhaktapur, Nepal' },
  { icon: ICONS.layers, label: 'Delivery', value: 'Two-week cycles' },
  { icon: ICONS.map, label: 'Focus', value: 'Web GIS & spatial data' },
]

const stats = [
  { value: '4+', label: 'Years mapping' },
  { value: '12+', label: 'Platforms shipped' },
  { value: '3', label: 'Live platforms' },
]
</script>

<template>
  <section id="about" class="studio-wrap studio-section" aria-labelledby="about-title">
    <div class="about-grid">
      <header class="about-head">
        <p class="studio-kicker">About us</p>
        <h2 id="about-title">Built by people who read maps for a living.</h2>
      </header>

      <div class="about-body">
        <p>
          Thimi Tech started as a two-person GIS consultancy mapping flood risk for a local ward
          office. Today we build full web platforms — mapping, data pipelines and the interfaces on
          top — for municipalities, tourism boards and startups that need their data to live on a
          map, not in a spreadsheet.
        </p>
        <p>
          We work in small teams, ship in two-week cycles, and keep every client in the room while
          the map is still being drawn. The same team covers the whole stack: GIS analysts who verify
          the data, engineers who build the pipelines and the API, and designers who make the result
          readable at first glance.
        </p>
      </div>

      <aside class="fact-card" aria-label="Studio facts">
        <div v-for="fact in facts" :key="fact.label" class="fact">
          <span class="icon-badge" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="fact.icon" />
            </svg>
          </span>
          <p class="fact-label">{{ fact.label }}</p>
          <p class="fact-value">{{ fact.value }}</p>
        </div>
      </aside>

      <dl class="about-stats">
        <div v-for="stat in stats" :key="stat.label">
          <dd>{{ stat.value }}</dd>
          <dt>{{ stat.label }}</dt>
        </div>
      </dl>
    </div>
  </section>
</template>

<style scoped>
/* Heading spans the row, then the copy and the fact partition share one row so
   the panel starts and ends exactly with the description. */
.about-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  grid-template-areas:
    'head head'
    'body facts'
    'stats stats';
  gap: clamp(20px, 2.2vw, 28px) clamp(32px, 5vw, 80px);
}

.about-head {
  display: grid;
  grid-area: head;
  gap: 10px;
}

.about-head h2 {
  max-width: 24ch;
}

.about-body {
  display: grid;
  grid-area: body;
  gap: 18px;
  align-content: start;
}

.about-body p {
  max-width: 64ch;
  font-size: 19px;
  line-height: 1.68;
  color: #000000;
}

/* Partition panel: four facts, two rows sharing the panel's height. */
.fact-card {
  display: grid;
  grid-area: facts;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(0, 1fr);
  overflow: hidden;
  border-radius: 16px;
  background: #f5f6f7;
}

.fact {
  display: grid;
  gap: 10px;
  align-content: center;
  padding: clamp(18px, 2vw, 26px);
}

.fact:nth-child(2n) {
  border-left: 1px solid rgb(10 10 10 / 0.1);
}

.fact:nth-child(n + 3) {
  border-top: 1px solid rgb(10 10 10 / 0.1);
}

.fact .icon-badge {
  width: 46px;
  height: 46px;
  background: #ffffff;
}

.fact .icon-badge svg {
  width: 21px;
  height: 21px;
}

.fact-label {
  margin-top: 2px;
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #000000;
}

.fact-value {
  font-size: 19px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: -0.015em;
  color: #000000;
}

.about-stats {
  display: grid;
  grid-area: stats;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 4px;
  padding-top: 24px;
  border-top: 1px solid rgb(10 10 10 / 0.13);
}

.about-stats dd {
  font-family: var(--font-display);
  font-size: clamp(30px, 2.8vw, 40px);
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.045em;
  color: #000000;
}

.about-stats dt {
  margin-top: 9px;
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #000000;
}

@media (max-width: 1023px) {
  .about-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'head'
      'body'
      'facts'
      'stats';
    gap: 24px;
  }

  .fact-card {
    grid-auto-rows: auto;
  }
}

@media (max-width: 560px) {
  .about-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 22px;
  }

  .fact-card {
    grid-template-columns: minmax(0, 1fr);
  }

  .fact:nth-child(2n) {
    border-left: 0;
  }

  .fact:nth-child(n + 2) {
    border-top: 1px solid rgb(10 10 10 / 0.1);
  }
}
</style>
