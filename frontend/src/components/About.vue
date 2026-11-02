<script setup lang="ts">
defineOptions({ name: 'StudioAbout' })

import { computed } from 'vue'
import { ICONS } from '../data/icons'
import { useTeamDirectory } from '../composables/useTeamDirectory'

const { members, loading } = useTeamDirectory()

const teamCount = computed(() => (loading.value ? '—' : String(members.value.length)))

const facts = computed(() => [
  { icon: ICONS.target, label: 'Founded', value: '2021' },
  { icon: ICONS.pin, label: 'Based in', value: 'Kathmandu, Nepal' },
  { icon: ICONS.users, label: 'Team', value: `${teamCount.value} ${teamCount.value === '1' ? 'person' : 'people'}` },
  { icon: ICONS.map, label: 'Focus', value: 'Web GIS & spatial data' },
])

const stats = [
  { value: '4+', label: 'Years mapping' },
  { value: '12+', label: 'Platforms shipped' },
  { value: '3', label: 'Live platforms' },
]
</script>

<template>
  <section id="about" class="studio-wrap studio-section" aria-labelledby="about-title">
    <div class="about-grid">
      <div class="about-copy">
        <p class="studio-kicker">About us</p>
        <h2 id="about-title">Built by people who read maps for a living.</h2>

        <p>
          Thimi Tech started as a two-person GIS consultancy mapping flood risk for a local ward
          office. Today we build full web platforms — mapping, data pipelines and the interfaces on
          top — for municipalities, tourism boards and startups that need their data to live on a
          map, not in a spreadsheet.
        </p>
        <p>
          We work in small teams, ship in two-week cycles, and keep every client in the room while
          the map is still being drawn.
        </p>
        <p>
          The same team covers the whole stack: GIS analysts who verify the data, engineers who
          build the pipelines and the API, and designers who make the result readable at first
          glance — so nothing is lost between vendors.
        </p>

        <dl class="about-stats">
          <div v-for="stat in stats" :key="stat.label">
            <dd>{{ stat.value }}</dd>
            <dt>{{ stat.label }}</dt>
          </div>
        </dl>
      </div>

      <div class="fact-card card">
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
      </div>
    </div>
  </section>
</template>

<style scoped>
.about-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: clamp(32px, 6vw, 88px);
  align-items: stretch;
}

.about-copy {
  display: flex;
  flex-direction: column;
  gap: clamp(22px, 2vw, 28px);
}

.about-copy h2 {
  max-width: 20ch;
}

.about-copy p {
  max-width: 62ch;
  font-size: 19px;
  line-height: 1.68;
  color: #000000;
}

.about-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding-top: 26px;
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

.fact-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  /* Rows share the card's height, so the facts fill it evenly instead of
     leaving a void above and below the group. */
  grid-auto-rows: minmax(0, 1fr);
  gap: 20px clamp(20px, 3vw, 40px);
  align-content: stretch;
  padding: clamp(26px, 3vw, 44px);
  border-radius: 16px;
  background: #f5f6f7;
  border-color: transparent;
}

.fact {
  display: grid;
  align-content: center;
}

.fact-card:hover {
  transform: none;
  box-shadow: none;
  border-color: transparent;
}

.fact-label {
  margin-top: 16px;
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #000000;
}

.fact-value {
  margin-top: 6px;
  font-size: 19px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: -0.015em;
  color: #000000;
}

@media (max-width: 1023px) {
  .about-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 36px;
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
}
</style>
