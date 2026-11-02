<script setup lang="ts">
defineOptions({ name: 'HeroSection' })

import { computed } from 'vue'
import GlobeScene from './GlobeScene.vue'

const props = withDefaults(defineProps<{ variant?: 'root' | 'new' }>(), { variant: 'root' })

const isNew = computed(() => props.variant === 'new')

const headline = computed(() => (isNew.value ? 'From place to ' : 'Turning Geographic Data into '))
const headlineAccent = computed(() => (isNew.value ? 'possibility.' : 'Digital Solutions.'))

const description = computed(() =>
  isNew.value
    ? 'From Nepal to the world: we build web GIS platforms, software and AI that turn location data into tools people actually use. Municipalities, tourism boards and startups come to us with a map nobody can read — and leave with a platform their teams open every morning.'
    : 'Thimi Tech designs and develops modern web GIS platforms that turn complex spatial data into simple, interactive experiences — helping organisations visualise, manage and analyse location-based data with confidence. We cover the whole path: field survey, data pipelines, the map itself, and the software around it.',
)

const primaryLabel = computed(() => (isNew.value ? 'Explore our work' : 'See our work'))
const projectHref = computed(() => (isNew.value ? '/new#projects' : '#projects'))
const contactHref = computed(() => (isNew.value ? '/new#contact' : '#contact'))

/**
 * What the studio actually does — the four areas from the services list. Real
 * capabilities instead of invented statistics.
 */
const capabilities = [
  { title: 'Web GIS platforms', text: 'Interactive maps for spatial data' },
  { title: 'Custom software', text: 'Web apps, APIs and dashboards' },
  { title: 'Field & mobile', text: 'Offline-first data collection' },
  { title: 'Earth observation', text: 'Satellite and remote sensing' },
]
</script>

<template>
  <section id="home" class="hero relative isolate overflow-hidden">
    <div class="hero__glow" aria-hidden="true"></div>
    <div class="hero__dots" aria-hidden="true"></div>

    <div class="hero__shell">
      <div class="hero__grid">
        <div class="hero__copy">
          <h1 class="hero__title">
            {{ headline }}<span class="hero__title-accent">{{ headlineAccent }}</span>
          </h1>

          <p class="hero__description">{{ description }}</p>

          <div class="hero__actions">
            <a :href="projectHref" class="studio-button">
              <span>{{ primaryLabel }}</span>
              <span aria-hidden="true">↗</span>
            </a>
            <a :href="contactHref" class="studio-button studio-button--ghost">Talk to us</a>
          </div>

          <ul class="hero__capabilities">
            <li v-for="capability in capabilities" :key="capability.title" class="hero__capability">
              <span class="hero__capability-title">{{ capability.title }}</span>
              <span class="hero__capability-text">{{ capability.text }}</span>
            </li>
          </ul>
        </div>

        <figure class="hero__globe" aria-label="Interactive globe of the Thimi Tech network">
          <div class="hero__globe-stage">
            <GlobeScene />
          </div>

          <figcaption class="sr-only">
            Interactive 3D globe showing Thimi Tech's headquarters in Bhaktapur and its worldwide
            delivery network. Drag to rotate, scroll to zoom.
          </figcaption>
        </figure>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  background: #ffffff;
  color: #000000;
  border-bottom: 1px solid rgb(10 10 10 / 0.13);
}

.hero__glow,
.hero__dots {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.hero__glow {
  background:
    radial-gradient(ellipse 46% 46% at 72% 46%, rgb(12 43 74 / 0.09), transparent 68%),
    radial-gradient(ellipse 90% 60% at 12% 0%, rgb(10 10 10 / 0.04), transparent 70%);
}

.hero__dots {
  opacity: 0.55;
  background-image: radial-gradient(rgb(10 10 10 / 0.16) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(to bottom, black, transparent 82%);
  -webkit-mask-image: linear-gradient(to bottom, black, transparent 82%);
}

.hero__shell {
  position: relative;
  z-index: 2;
  width: min(100% - 56px, 1400px);
  margin-inline: auto;
}

.hero__grid {
  display: grid;
  grid-template-columns: minmax(0, 0.94fr) minmax(0, 1.06fr);
  gap: clamp(28px, 4.4vw, 72px);
  /* Both columns share one height, so the globe is centred against the copy
     instead of floating low with dead space above it. */
  align-items: stretch;
  padding-block: clamp(46px, 5.6vw, 84px);
}

.hero__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  /* One gap between every block: headline, copy, buttons, stats. */
  justify-content: center;
  gap: clamp(24px, 2.4vw, 34px);
}

.hero__title {
  max-width: 12ch;
  font-family: var(--font-display);
  font-size: clamp(46px, 5.4vw, 84px);
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.05em;
  text-wrap: balance;
  color: #000000;
}

.hero__title-accent {
  display: block;
  color: #000000;
}

.hero__description {
  max-width: 52ch;
  font-size: clamp(18px, 1.45vw, 21px);
  line-height: 1.62;
  color: #000000;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero__capabilities {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  padding: 0;
  list-style: none;
}

.hero__capability {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
  padding: 15px 14px 0 0;
  border-top: 1px solid rgb(10 10 10 / 0.13);
  border-right: 1px solid rgb(10 10 10 / 0.13);
}

.hero__capability:not(:first-child) {
  padding-left: 16px;
}

.hero__capability:last-child {
  border-right: 0;
}

.hero__capability-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.02em;
  color: #000000;
}

.hero__capability-text {
  font-size: 15px;
  line-height: 1.45;
  color: #000000;
}

.hero__globe {
  position: relative;
  display: grid;
  min-width: 0;
  margin: 0;
}

.hero__globe-stage {
  position: relative;
  height: 100%;
  min-height: clamp(420px, 52vh, 640px);
}

.hero__globe-stage :deep(> *) {
  position: relative;
  z-index: 1;
  height: 100%;
}

.hero :is(a, button):focus-visible {
  outline: 2px solid #0a0a0a;
  outline-offset: 4px;
}

@media (max-width: 1199px) {
  .hero__shell {
    width: calc(100% - 48px);
  }

  .hero__grid {
    gap: 34px;
  }

  .hero__globe-stage {
    min-height: clamp(400px, 50vh, 560px);
  }
}

@media (max-width: 1023px) {
  .hero__grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 30px;
    padding-block: 40px 44px;
  }

  .hero__title {
    max-width: 14ch;
  }

  .hero__description {
    max-width: 62ch;
  }

  .hero__capabilities {
    max-width: 640px;
  }

  /* Stacked: the globe gets its own fixed stage again. */
  .hero__globe-stage {
    height: clamp(400px, 56vh, 580px);
    min-height: 400px;
  }
}

@media (max-width: 767px) {
  .hero__shell {
    width: calc(100% - 40px);
  }

  .hero__grid {
    gap: 26px;
    padding-block: 32px 36px;
  }

  .hero__title {
    font-size: clamp(42px, 11vw, 60px);
  }

  .hero__description {
    font-size: 19px;
  }

  .hero__capabilities {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero__capability {
    padding-block: 14px 16px;
  }

  .hero__capability:nth-child(2) {
    border-right: 0;
  }

  .hero__capability:nth-child(3) {
    padding-left: 0;
  }

  .hero__capability:nth-child(4) {
    padding-left: 16px;
    border-right: 0;
  }

  .hero__globe-stage {
    height: 380px;
    min-height: 380px;
  }
}
</style>
