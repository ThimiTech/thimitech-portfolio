<script setup lang="ts">
defineOptions({ name: 'StudioContact' })

const details = [
  { label: 'Studio', value: 'Kathmandu, Nepal' },
  { label: 'Time zone', value: 'GMT +5:45 · Asia/Kathmandu' },
  { label: 'Availability', value: 'Open for new projects — remote and on-site' },
  { label: 'Working with us', value: 'Discovery call · scoped proposal · two-week delivery cycles' },
]
</script>

<template>
  <section id="contact" class="contact studio-invert" aria-labelledby="contact-title">
    <div class="studio-wrap studio-section">
      <div class="contact-grid">
        <div>
          <p class="studio-kicker">Contact</p>
          <h2 id="contact-title">Let’s put it on the map.</h2>
          <p class="section-intro">
            Tell us what you are working on and what data you already have. We will suggest where to
            start, what it takes, and whether we are the right team for it — no obligation, no
            jargon.
          </p>
        </div>

        <div class="contact-side">
          <a href="mailto:info@thimitech.com" class="contact-email">
            info@thimitech.com <span aria-hidden="true">↗</span>
          </a>

          <dl class="contact-details">
            <div v-for="detail in details" :key="detail.label">
              <dt>{{ detail.label }}</dt>
              <dd>{{ detail.value }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.contact {
  border-top: 1px solid rgb(10 10 10 / 0.13);
}

.contact-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: clamp(28px, 6vw, 88px);
  align-items: start;
}

.contact-grid h2 {
  margin-top: 14px;
  max-width: 16ch;
  color: var(--ink);
}

.contact-side {
  display: grid;
  gap: 26px;
}

.contact-email {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line-strong);
  font-family: var(--font-display);
  font-size: clamp(24px, 2.6vw, 38px);
  font-weight: 500;
  letter-spacing: -0.035em;
  color: var(--ink);
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.contact-email:hover {
  opacity: 0.7;
}

.contact-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
  padding-top: 24px;
  border-top: 1px solid var(--line);
}

.contact-details dt {
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.contact-details dd {
  margin-top: 8px;
  font-size: 18px;
  line-height: 1.6;
  color: var(--ink);
}

@media (max-width: 900px) {
  .contact-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 32px;
  }
}

@media (max-width: 560px) {
  .contact-details {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
