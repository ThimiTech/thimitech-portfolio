<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api/api'
import { useTeamDirectory } from '../../composables/useTeamDirectory'
import { canAnimate, gsap } from './motion'

const values = [
  { title: 'Data first', text: 'Every decision starts from accurate, well-structured spatial data. We check the source, document the schema and fix the gaps before anything is drawn on a map.' },
  { title: 'Built for use', text: 'We design maps for the people who open them every day: field staff, planners, ward offices. If it takes training to read, it is not finished.' },
  { title: 'Local context', text: 'We build for Nepal’s geography and the way our clients actually work: patchy connectivity, mixed data, decisions made in the field.' },
  { title: 'Built to last', text: 'Stable, well-supported tools over trends, documented handovers, and a platform your team can maintain after we leave.' },
  { title: 'Open by default', text: 'Shared progress, honest timelines and no black boxes. Clients see the work as it grows and keep the source.' },
  { title: 'People over platforms', text: 'Technology is the tool, not the goal. Every project starts with the person who will use it.' },
]

interface Job { id: number; title: string; employment_type: string; description: string }
const { members, loading: teamLoading } = useTeamDirectory()
const jobs = ref<Job[]>([])
const jobsLoaded = ref(false)
const brokenPhotos = ref(new Set<number>())
const root = ref<HTMLElement | null>(null)
let ctx: gsap.Context | undefined

const initials = (name: string) => name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase()

onMounted(async () => {
  if (canAnimate && root.value) {
    ctx = gsap.context(() => {
      // Each principle inks in as it crosses the middle of the screen, and fades again once passed.
      gsap.utils.toArray<HTMLElement>('.value').forEach((el) => {
        gsap.fromTo(el, { opacity: 0.14 }, {
          opacity: 1, ease: 'none',
          scrollTrigger: { trigger: el, start: 'top 82%', end: 'top 48%', scrub: true },
        })
      })
    }, root.value)
  }
  try {
    const { data } = await api.get<Job[]>('jobs/')
    jobs.value = Array.isArray(data) ? data : []
  } catch {
    /* the empty state below invites an email instead */
  } finally {
    jobsLoaded.value = true
  }
})
onBeforeUnmount(() => ctx?.revert())
</script>

<template>
  <div ref="root">
    <section id="mission" class="band daylight" aria-labelledby="mission-title">
      <div class="wrap">
        <p class="kicker">Altitude 30 m · how we work</p>
        <h2 id="mission-title" class="sr-only">Our principles</h2>
        <ol class="values">
          <li v-for="(v, i) in values" :key="v.title" class="value">
            <span class="num">{{ String(i + 1).padStart(2, '0') }}</span>
            <h3>{{ v.title }}</h3>
            <p>{{ v.text }}</p>
          </li>
        </ol>
      </div>
    </section>

    <section id="team" class="band daylight" aria-labelledby="team-title">
      <div class="wrap">
        <header class="head">
          <div>
            <p class="kicker">Altitude 2 m · eye level</p>
            <h2 id="team-title">The people on the ground.</h2>
          </div>
          <p>Engineers, analysts and designers building geospatial tools that hold up in the field.</p>
        </header>
        <p v-if="!teamLoading && !members.length" class="quiet">Meet the team here soon.</p>
        <ul v-else class="people">
          <li v-for="m in members" :key="m.id" class="person">
            <div class="face">
              <img v-if="m.image && !brokenPhotos.has(m.id)" :src="m.image" :alt="m.name" loading="lazy" @error="brokenPhotos.add(m.id)" />
              <span v-else aria-hidden="true">{{ m.initials?.trim() || initials(m.name) }}</span>
            </div>
            <p class="name">{{ m.name }}</p>
            <p class="role">{{ m.role }}</p>
          </li>
        </ul>
      </div>
    </section>

    <section id="hiring" class="band daylight" aria-labelledby="hiring-title">
      <div class="wrap">
        <header class="head">
          <div>
            <p class="kicker">Open roles</p>
            <h2 id="hiring-title">Walk with us.</h2>
          </div>
          <p>We look for people who see maps as tools for meaningful impact, and want to shape how Nepal works with its own data.</p>
        </header>
        <ul v-if="jobs.length" class="roles">
          <li v-for="j in jobs" :key="j.id">
            <RouterLink :to="`/apply/${j.id}`">
              <span class="role-title">{{ j.title }}</span>
              <span class="role-type">{{ j.employment_type }}</span>
              <span class="role-go">Apply <span aria-hidden="true">→</span></span>
            </RouterLink>
          </li>
        </ul>
        <p v-else-if="jobsLoaded" class="quiet">
          No open roles right now. Introduce yourself at <a href="mailto:info@thimitech.com">info@thimitech.com</a>; we keep good people on file.
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.band {
  padding-block: clamp(72px, 11vw, 150px);
}
.head {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
  align-items: end;
  gap: 24px 56px;
  margin-bottom: clamp(36px, 5vw, 72px);
}
.head h2 {
  margin: 16px 0 0;
}
.head > p,
.quiet {
  margin: 0;
  font-size: clamp(16px, 1.3vw, 19px);
  line-height: 1.6;
  color: var(--dim);
}
.quiet a {
  color: var(--fg);
}

.values {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
}
.value {
  display: grid;
  grid-template-columns: 56px minmax(0, 1.25fr) minmax(0, 1fr);
  align-items: baseline;
  gap: 8px 32px;
  padding-block: clamp(18px, 2.6vw, 36px);
  border-top: 1px solid var(--line);
}
.num {
  font: 400 12px/1 var(--font-mono);
  letter-spacing: 0.12em;
  color: var(--signal);
}
.value h3 {
  margin: 0;
  font-size: clamp(34px, 6.2vw, 104px);
  font-weight: 500;
  line-height: 0.98;
  letter-spacing: -0.05em;
}
.value p {
  margin: 0;
  font-size: clamp(15px, 1.15vw, 18px);
  line-height: 1.6;
  color: var(--dim);
}

.people {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: clamp(20px, 2.6vw, 40px) clamp(16px, 2vw, 28px);
  margin: 0;
  padding: 0;
  list-style: none;
}
.face {
  display: grid;
  aspect-ratio: 4 / 5;
  place-items: center;
  overflow: hidden;
  background: color-mix(in oklab, var(--fg) 7%, var(--bg));
  font-size: 44px;
  font-weight: 500;
  letter-spacing: -0.04em;
  color: var(--dim);
}
.face img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(1);
  transition: filter 0.4s ease, transform 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.person:hover img {
  filter: none;
  transform: scale(1.04);
}
/* People load after first paint, so their entrance is pure CSS (no measuring): each card rises as it scrolls in. */
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .person,
    .roles li {
      animation: arrive linear both;
      animation-timeline: view();
      animation-range: entry 0% entry 70%;
    }
  }
}
@keyframes arrive {
  from {
    opacity: 0;
    transform: translateY(36px);
  }
}
.name {
  margin: 14px 0 2px;
  font-size: 18px;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.role {
  margin: 0;
  font: 400 11px/1.5 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--dim);
}

.roles {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid var(--line);
  list-style: none;
}
.roles a {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: baseline;
  gap: 8px 32px;
  padding: clamp(18px, 2.2vw, 30px) 0;
  border-top: 1px solid var(--line);
  color: var(--fg);
  text-decoration: none;
  transition: padding 0.3s ease, color 0.3s ease;
}
.roles a:hover {
  padding-inline: 16px;
  color: var(--signal);
}
.role-title {
  font-size: clamp(24px, 3vw, 46px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.04em;
}
.role-type,
.role-go {
  font: 400 12px/1 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.role-type {
  color: var(--dim);
}

@media (max-width: 760px) {
  .head,
  .value {
    grid-template-columns: minmax(0, 1fr);
  }
  .people {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .roles a {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .role-type {
    grid-row: 2;
  }
}
</style>
