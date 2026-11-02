<script setup lang="ts">
defineOptions({ name: 'StudioMission' })

import SceneImage, { type SceneKind } from './SceneImage.vue'

/** Values are frontend content, phrased the same way as the services: one idea per card. */
const values: { scene: SceneKind; seed: number; title: string; text: string }[] = [
  {
    scene: 'satellite',
    seed: 61,
    title: 'Data first',
    text: 'Every decision starts from accurate, well-structured spatial data. We check the source, document the schema and fix the gaps before anything is drawn on a map.',
  },
  {
    scene: 'field',
    seed: 29,
    title: 'Built for use',
    text: 'We design maps for the people who open them every day — field staff, planners, ward offices — not for a demo. If it takes training to read, it is not finished.',
  },
  {
    scene: 'terrain',
    seed: 31,
    title: 'Local context',
    text: 'We build for Nepal’s geography, its infrastructure and the way our clients actually work: patchy connectivity, mixed data, decisions made in the field.',
  },
  {
    scene: 'city',
    seed: 43,
    title: 'Built to last',
    text: 'We choose stable, well-supported tools over trends, document what we hand over, and make sure your team can maintain the platform after we leave.',
  },
  {
    scene: 'dashboard',
    seed: 53,
    title: 'Open by default',
    text: 'Shared progress, honest timelines and no black boxes. Clients see the work as it grows, question the assumptions and keep the source.',
  },
  {
    scene: 'orbit',
    seed: 47,
    title: 'People over platforms',
    text: 'Technology is the tool, not the goal. Every project starts with the person who will use it and the decision they are trying to make.',
  },
]
</script>

<template>
  <section id="mission" class="mission" aria-labelledby="mission-title">
    <div class="studio-wrap studio-section">
      <header class="section-head">
        <div>
          <p class="studio-kicker">Our mission</p>
          <h2 id="mission-title">Make Nepal’s geography easy to see, search and act on.</h2>
        </div>
        <p class="section-intro">
          Too much spatial data in Nepal sits locked in spreadsheets and paper records. We build the
          maps and platforms that put it in front of the people who need it — and we hold ourselves
          to six principles while doing it.
        </p>
      </header>

      <div class="card-grid value-grid">
        <article v-for="value in values" :key="value.title" class="card value-card">
          <SceneImage :scene="value.scene" :seed="value.seed" />

          <div class="value-body">
            <h3>{{ value.title }}</h3>
            <p>{{ value.text }}</p>
          </div>
        </article>
      </div>

      <p class="section-note">
        <strong>How we work:</strong> a short discovery to agree on the questions the map has to
        answer, a working prototype in the first weeks, then production hardening — data model,
        permissions, audit trail — with your team testing alongside ours.
      </p>
    </div>
  </section>
</template>

<style scoped>
.mission {
  background: #f5f6f7;
  border-block: 1px solid rgb(10 10 10 / 0.1);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.value-card {
  padding: 0;
  overflow: hidden;
  gap: 0;
}

.value-body {
  display: grid;
  gap: 12px;
  padding: clamp(20px, 2vw, 26px);
}

.value-body p {
  font-size: 18px;
  line-height: 1.66;
  color: #000000;
}

@media (max-width: 1023px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
