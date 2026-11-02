<script setup lang="ts">
defineOptions({ name: 'StudioServices' })

import SceneImage, { type SceneKind } from './SceneImage.vue'

/**
 * Services are frontend content by design: they describe what the studio offers and
 * change with the company, not with the database. Portfolio data (projects, team,
 * jobs) stays API-driven.
 */
interface Service {
  scene: SceneKind
  seed: number
  title: string
  description: string
}

const services: Service[] = [
  {
    scene: 'city',
    seed: 3,
    title: 'WebGIS Development & Geospatial Solutions',
    description:
      'We design and develop advanced WebGIS platforms that integrate spatial data, interactive mapping and geospatial analytics. Layers, imagery and field records become one map your team can search, filter and act on.',
  },
  {
    scene: 'field',
    seed: 5,
    title: 'Mobile Application Development',
    description:
      'We develop intuitive, high-performance mobile applications tailored to diverse business and organisational needs. From field data collection to offline mapping, our apps keep working where the signal does not.',
  },
  {
    scene: 'dashboard',
    seed: 7,
    title: 'Custom Software & Web Application Development',
    description:
      'We deliver secure, scalable and customised software solutions designed to address unique operational challenges. Our engineers cover the data model, the API and the interface your staff open every day.',
  },
  {
    scene: 'orbit',
    seed: 11,
    title: 'Real-World Problem Solving & Digital Innovation',
    description:
      'We transform complex real-world challenges into practical digital solutions through innovative technology and strategic problem-solving — starting from the decision you need to make, not from the tool.',
  },
  {
    scene: 'satellite',
    seed: 13,
    title: 'Remote Sensing & Earth Observation',
    description:
      'We leverage satellite imagery, remote sensing technologies and geospatial analysis to monitor environmental change, assess land use and support evidence-based planning at district and national scale.',
  },
  {
    scene: 'analytics',
    seed: 17,
    title: 'Data Analytics & Business Intelligence',
    description:
      'We transform complex datasets into meaningful insights through interactive dashboards, advanced analytics and intelligent reporting that people actually open — and trust enough to decide with.',
  },
]
</script>

<template>
  <section id="services" class="studio-wrap studio-section" aria-labelledby="services-title">
    <header class="section-head">
      <div>
        <p class="studio-kicker">Services</p>
        <h2 id="services-title">What we build</h2>
      </div>
      <p class="section-intro">
        A focused set of services, from the first line of data to the finished platform. Every
        engagement follows the same order: understand the decision, structure the data, then build
        the interface around it.
      </p>
    </header>

    <div class="card-grid">
      <article v-for="service in services" :key="service.title" class="card service-card">
        <SceneImage :scene="service.scene" :seed="service.seed" />

        <div class="service-body">
          <h3>{{ service.title }}</h3>
          <p>{{ service.description }}</p>
        </div>
      </article>
    </div>

    <p class="section-note">
      <strong>Not sure which one you need?</strong> Describe the problem and the data you already
      have — a spreadsheet, a survey, a pile of PDFs. We will tell you where to start, what it would
      take, and what we would leave out. <a href="#contact">Start the conversation</a>.
    </p>
  </section>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.service-card {
  padding: 0;
  overflow: hidden;
  gap: 0;
}

.service-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  padding: clamp(22px, 2.2vw, 30px);
}

.service-body p {
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
