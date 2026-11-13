<script setup lang="ts">
/** Daylight: the founder's note (text from `/api/org/public/`), what we hold ourselves to, and the open roles (`/api/jobs/`). */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../../api/api'
import { canAnimate, gsap } from './motion'
import { useSite } from './site'

const values = [
  { title: 'Data first', text: 'We check the source, document the schema and fix the gaps before anything is drawn on a map.' },
  { title: 'Built for use', text: 'Maps for the people who open them every day. If it takes training to read, it is not finished.' },
  { title: 'Local context', text: 'Built for Nepal’s geography and the way clients work: patchy signal, mixed data, decisions made in the field.' },
  { title: 'Built to last', text: 'Stable tools over trends, documented handovers, and a platform your team can maintain after we leave.' },
  { title: 'Open by default', text: 'Shared progress, honest timelines and no black boxes. Clients see the work grow and keep the source.' },
  { title: 'People over platforms', text: 'Technology is the tool, not the goal. Every project starts with the person who will use it.' },
]

interface Job { id: number; title: string; employment_type: string; description: string }
const { site } = useSite()
const jobs = ref<Job[]>([])
const jobsLoaded = ref(false)
const photoBroken = ref(false)
const root = ref<HTMLElement | null>(null)
let ctx: gsap.Context | undefined

const words = computed(() => site.value.founder_quote.split(/\s+/).filter(Boolean))
const paragraphs = computed(() => site.value.founder_message.split(/\n\s*\n/).filter((p) => p.trim()))
const initials = computed(() => site.value.founder_name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase())

onMounted(async () => {
  if (canAnimate && root.value) {
    ctx = gsap.context(() => {
      // The quote inks in word by word as it crosses the screen: one number, read by every word (see .quote span).
      gsap.fromTo('.quote', { '--ink': 0 }, {
        '--ink': 1,
        ease: 'none',
        scrollTrigger: { trigger: '.quote', start: 'top 85%', end: 'bottom 45%', scrub: true },
      })
      gsap.fromTo('.portrait', { yPercent: 6 }, {
        yPercent: -6,
        ease: 'none',
        scrollTrigger: { trigger: '.note', start: 'top bottom', end: 'bottom top', scrub: true },
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
    <section id="mission" class="band note daylight" aria-labelledby="mission-title">
      <div class="wrap letter">
        <figure class="portrait">
          <div class="frame">
            <img v-if="site.founder_photo && !photoBroken" :src="site.founder_photo" :alt="site.founder_name" loading="lazy" @error="photoBroken = true" />
            <span v-else aria-hidden="true">{{ initials }}</span>
          </div>
          <figcaption>
            <strong>{{ site.founder_name }}</strong>
            <span>{{ site.founder_title }} · {{ site.name }}</span>
          </figcaption>
        </figure>

        <div>
          <p class="kicker">Altitude 30 m · a note from the founder</p>
          <h2 id="mission-title" class="sr-only">A note from {{ site.founder_name }}, {{ site.founder_title }}</h2>
          <blockquote class="quote" :style="{ '--n': words.length }">
            <span v-for="(w, i) in words" :key="i" :style="{ '--i': i }">{{ w + ' ' }}</span>
          </blockquote>
          <div class="message">
            <p v-for="p in paragraphs" :key="p">{{ p }}</p>
          </div>
          <p class="sign">
            <span class="name">{{ site.founder_name }}</span>
            <span class="title">{{ site.founder_title }}</span>
          </p>
        </div>
      </div>

      <div class="wrap">
        <h3 class="kicker held">What we hold ourselves to</h3>
        <ol class="values">
          <li v-for="(v, i) in values" :key="v.title" class="value">
            <span class="num">{{ String(i + 1).padStart(2, '0') }}</span>
            <h4>{{ v.title }}</h4>
            <p>{{ v.text }}</p>
          </li>
        </ol>
      </div>
    </section>

    <section id="hiring" class="band daylight" aria-labelledby="hiring-title">
      <div class="wrap">
        <header class="head">
          <div>
            <p class="kicker">Altitude 2 m · eye level</p>
            <h2 id="hiring-title">Walk with us.</h2>
          </div>
          <p>We look for people who see maps as tools for meaningful impact, and want to shape how Nepal works with its own data.</p>
        </header>
        <ul v-if="jobs.length" class="roles">
          <li v-for="(j, i) in jobs" :key="j.id">
            <RouterLink :to="`/apply/${j.id}`">
              <span class="num">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="role-main">
                <span class="role-title">{{ j.title }}</span>
                <span class="role-text">{{ j.description }}</span>
              </span>
              <span class="role-type">{{ j.employment_type }}</span>
              <span class="role-go">Apply <span aria-hidden="true">→</span></span>
            </RouterLink>
          </li>
        </ul>
        <p v-else-if="jobsLoaded" class="quiet">
          No open roles right now. Introduce yourself at <a :href="`mailto:${site.email}`">{{ site.email }}</a>; we keep good people on file.
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.band {
  padding-block: clamp(72px, 11vw, 150px);
}
.num {
  font: 400 12px/1 var(--font-mono);
  letter-spacing: 0.12em;
  color: var(--signal);
}

/* Founder's note */
.letter {
  display: grid;
  grid-template-columns: minmax(0, 0.72fr) minmax(0, 1.6fr);
  align-items: start;
  gap: clamp(28px, 6vw, 110px);
}
.portrait {
  margin: 0;
}
.frame {
  position: relative;
  display: grid;
  aspect-ratio: 4 / 5;
  place-items: center;
  overflow: hidden;
  background:
    repeating-linear-gradient(0deg, transparent 0 39px, var(--line) 39px 40px),
    repeating-linear-gradient(90deg, transparent 0 39px, var(--line) 39px 40px),
    color-mix(in oklab, var(--fg) 6%, var(--bg));
  font-size: clamp(64px, 9vw, 150px);
  font-weight: 500;
  letter-spacing: -0.06em;
  color: var(--fg);
}
/* survey corner marks */
.frame::before,
.frame::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid var(--signal);
}
.frame::before {
  top: 12px;
  left: 12px;
  border-right: 0;
  border-bottom: 0;
}
.frame::after {
  right: 12px;
  bottom: 12px;
  border-top: 0;
  border-left: 0;
}
.frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(1) contrast(1.05);
  transition: filter 0.5s ease;
}
.portrait:hover img {
  filter: none;
}
figcaption {
  display: grid;
  gap: 2px;
  margin-top: 14px;
}
figcaption strong {
  font-size: 18px;
  font-weight: 500;
  letter-spacing: -0.02em;
}
figcaption span,
.sign .title {
  font: 400 11px/1.5 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--dim);
}

.quote {
  --ink: 1;
  margin: 22px 0 0;
  font-size: clamp(32px, 4.7vw, 78px);
  font-weight: 500;
  line-height: 1.04;
  letter-spacing: -0.045em;
  text-wrap: balance;
}
.quote::before {
  content: '“';
  display: block;
  height: 0.5em;
  font-size: 1.6em;
  line-height: 1;
  color: var(--signal);
}
/* word i is fully inked once --ink has passed it; four words are mid-way at any time */
.quote span {
  opacity: calc(0.14 + 0.86 * clamp(0, (var(--ink) * (var(--n) + 4) - var(--i)) / 4, 1));
}
.message {
  max-width: 62ch;
  margin-top: clamp(24px, 3vw, 44px);
}
.message p {
  margin: 0 0 1em;
  font-size: clamp(17px, 1.4vw, 21px);
  line-height: 1.65;
  color: var(--dim);
  white-space: pre-line;
}
.sign {
  display: grid;
  gap: 4px;
  width: fit-content;
  margin: clamp(20px, 2.4vw, 36px) 0 0;
  padding-top: 16px;
  border-top: 2px solid var(--signal);
}
.sign .name {
  font-size: clamp(22px, 2.2vw, 32px);
  font-style: italic;
  font-weight: 500;
  letter-spacing: -0.03em;
}

.held {
  margin-top: clamp(64px, 9vw, 130px);
}
.values {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 clamp(20px, 3vw, 48px);
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
}
.value {
  padding-block: 22px 26px;
  border-top: 1px solid var(--line);
}
.value h4 {
  margin: 14px 0 8px;
  font-size: clamp(22px, 2vw, 30px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.035em;
}
.value p {
  margin: 0;
  font-size: 15.5px;
  line-height: 1.6;
  color: var(--dim);
}

/* Open roles */
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
.roles {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid var(--line);
  list-style: none;
}
.roles a {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto auto;
  align-items: baseline;
  gap: 8px 32px;
  padding: clamp(18px, 2.2vw, 30px) 0;
  border-top: 1px solid var(--line);
  color: var(--fg);
  text-decoration: none;
  transition: padding 0.3s ease, background-color 0.3s ease;
}
.roles a:hover {
  padding-inline: 16px;
  background: color-mix(in oklab, var(--fg) 5%, var(--bg));
}
.role-main {
  display: grid;
  gap: 8px;
}
.role-title {
  font-size: clamp(24px, 3vw, 46px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.04em;
  transition: color 0.3s ease;
}
.roles a:hover .role-title {
  color: var(--signal);
}
.role-text {
  max-width: 60ch;
  font-size: 15.5px;
  line-height: 1.55;
  color: var(--dim);
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

/* Values and roles load or sit below the fold, so their entrance is pure CSS (no measuring). */
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .value,
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

@media (max-width: 860px) {
  .letter,
  .head {
    grid-template-columns: minmax(0, 1fr);
  }
  .portrait {
    max-width: 240px;
  }
  .values {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .roles a {
    grid-template-columns: 32px minmax(0, 1fr) auto;
  }
  .role-type {
    grid-column: 2;
    grid-row: 2;
  }
}
@media (max-width: 520px) {
  .values {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
