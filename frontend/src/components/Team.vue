<script setup lang="ts">
defineOptions({ name: 'StudioTeam' })

import { ref } from 'vue'
import { useTeamDirectory } from '../composables/useTeamDirectory'

const { members, loading, error, reload } = useTeamDirectory()
const brokenPhotos = ref(new Set<number>())

function initialsFor(name: string, initials?: string) {
  if (initials && initials.trim()) return initials.trim().slice(0, 3).toUpperCase()
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
</script>

<template>
  <section id="team" class="team" aria-labelledby="team-title">
    <div class="studio-wrap studio-section">
      <header class="section-head">
        <div>
          <p class="studio-kicker">People</p>
          <h2 id="team-title">The team</h2>
        </div>
        <p class="section-intro">
          A collective of engineers and innovators, driven by precision and purpose — building
          geospatial solutions that hold up in the field.
        </p>
      </header>

      <div v-if="loading" class="card-grid" aria-busy="true" aria-label="Loading team">
        <div v-for="n in 3" :key="n" class="card skeleton" />
      </div>

      <p v-else-if="error" role="alert" class="state">
        Our team is temporarily unavailable.
        <button type="button" class="state-action" @click="reload">Try again</button>
      </p>

      <p v-else-if="!members.length" class="state">Meet the team here soon.</p>

      <div v-else class="card-grid">
        <article v-for="member in members" :key="member.id" class="card person-card">
          <span class="portrait">
            <img
              v-if="member.image && !brokenPhotos.has(member.id)"
              :src="member.image"
              :alt="member.name"
              loading="lazy"
              @error="brokenPhotos.add(member.id)"
            />
            <span v-else class="portrait-initials" aria-hidden="true">
              {{ initialsFor(member.name, member.initials) }}
            </span>
          </span>
          <h3>{{ member.name }}</h3>
          <p class="person-role">{{ member.role }}</p>
          <a v-if="member.email" class="card-link" :href="`mailto:${member.email}`">Email</a>
        </article>
      </div>

      <p class="section-note">
        <strong>A small studio by design.</strong> Everyone listed here works directly on client
        projects — no layers between the people who write the code and the people who use the map.
        We are growing: <a href="#hiring">see the open roles</a>.
      </p>
    </div>
  </section>
</template>

<style scoped>
.team {
  background: #f5f6f7;
  border-block: 1px solid rgb(10 10 10 / 0.1);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(18px, 2vw, 26px);
}

.person-card {
  align-items: center;
  gap: 12px;
  padding: clamp(28px, 3vw, 40px);
  text-align: center;
}

.portrait {
  display: grid;
  place-items: center;
  width: clamp(96px, 9vw, 128px);
  aspect-ratio: 1;
  overflow: hidden;
  border: 1px solid rgb(10 10 10 / 0.12);
  border-radius: 50%;
  background: linear-gradient(160deg, #e9ebee, #d5d8dc);
}

.portrait img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.portrait-initials {
  font-family: var(--font-display);
  font-size: clamp(28px, 3vw, 38px);
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #1c1f22;
}

.person-card h3 {
  margin-top: 8px;
}

.person-role {
  font: 500 13px/1.5 var(--font-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #000000 !important;
}

.person-card .card-link {
  /* pinned so every card's link sits on the same line */
  margin-top: auto;
  padding-top: 16px;
}

.skeleton {
  height: 300px;
  border-radius: 14px;
  background: linear-gradient(90deg, #eceef0, #e2e5e8 40%, #eceef0 80%);
  animation: shimmer 1.4s ease-in-out infinite;
}

.state {
  padding: 40px 0;
  font-size: 16px;
  color: #5b6169;
}

.state-action {
  margin-left: 8px;
  border: 0;
  border-bottom: 1px solid currentColor;
  background: none;
  font: inherit;
  color: #0a0a0a;
  cursor: pointer;
}

@keyframes shimmer {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
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

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>
