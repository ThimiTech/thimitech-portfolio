<script setup lang="ts">
defineOptions({ name: 'StudioContact' })

const details = [
  { label: 'Studio', value: 'Thimi, Bhaktapur, Nepal' },
  { label: 'Time zone', value: 'GMT +5:45 · Asia/Kathmandu' },
  { label: 'Availability', value: 'Open for new projects — remote and on-site' },
]

const steps = [
  { index: '01', title: 'Discovery call', text: 'We talk through the decision you need to make and the data you already have.' },
  { index: '02', title: 'Scoped proposal', text: 'Deliverables, timeline and cost in writing — before any code is written.' },
  { index: '03', title: 'Two-week cycles', text: 'Working software every fortnight, with your team testing alongside ours.' },
]
</script>

<template>
  <section id="contact" class="contact studio-wrap studio-section" aria-labelledby="contact-title">
    <header class="section-head">
      <p class="studio-kicker">Contact</p>
      <h2 id="contact-title">Let’s put it on the map.</h2>
      <p class="section-intro">
        Tell us what you are working on and what data you already have. We will suggest where to
        start, what it takes, and whether we are the right team for it — no obligation, no jargon.
      </p>
    </header>

    <div class="contact-panel">
      <div class="panel-top">
        <div class="panel-primary">
          <p class="panel-label">Email us</p>
          <a class="panel-email" href="mailto:info@thimitech.com">
            info@thimitech.com <span aria-hidden="true">↗</span>
          </a>
        </div>

        <dl class="panel-facts">
          <div v-for="detail in details" :key="detail.label">
            <dt>{{ detail.label }}</dt>
            <dd>{{ detail.value }}</dd>
          </div>
        </dl>
      </div>

      <div class="panel-steps">
        <p class="panel-label">How an engagement starts</p>
        <ol>
          <li v-for="step in steps" :key="step.index">
            <span class="step-index" aria-hidden="true">{{ step.index }}</span>
            <span class="step-copy">
              <span class="step-title">{{ step.title }}</span>
              <span class="step-text">{{ step.text }}</span>
            </span>
          </li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
.contact {
  border-top: 1px solid rgb(10 10 10 / 0.13);
}

/* White sheet: structure comes from spacing and type hierarchy, not from rules. */
.contact-panel {
  display: grid;
  gap: clamp(30px, 3.4vw, 48px);
  padding: clamp(26px, 3vw, 44px);
  border: 1px solid rgb(10 10 10 / 0.13);
  border-radius: 20px;
  background: #ffffff;
}

.panel-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.45fr);
  gap: clamp(28px, 4vw, 64px);
  align-items: start;
}

.panel-primary {
  display: grid;
  gap: 12px;
  align-content: start;
}

.panel-label {
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #000000;
}

.panel-email {
  justify-self: start;
  font-family: var(--font-display);
  font-size: clamp(21px, 2vw, 30px);
  font-weight: 500;
  letter-spacing: -0.03em;
  color: #000000;
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.panel-email:hover {
  opacity: 0.6;
}

.panel-email span {
  margin-left: 8px;
}

.panel-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(20px, 2.6vw, 40px);
  margin: 0;
}

.panel-facts dt {
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #000000;
}

.panel-facts dd {
  margin-top: 9px;
  font-size: 17px;
  line-height: 1.55;
  color: #000000;
}

.panel-steps {
  display: grid;
  gap: clamp(16px, 1.8vw, 22px);
}

.panel-steps ol {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(24px, 3.4vw, 48px);
  margin: 0;
  padding: 0;
  list-style: none;
}

.panel-steps li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.step-index {
  font: 500 12px/1.6 var(--font-mono);
  letter-spacing: 0.08em;
  color: #000000;
}

.step-copy {
  display: grid;
  gap: 6px;
}

.step-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #000000;
}

.step-text {
  font-size: 15.5px;
  line-height: 1.6;
  color: #000000;
}

@media (max-width: 1023px) {
  .panel-top {
    grid-template-columns: minmax(0, 1fr);
    gap: 30px;
  }

  .panel-steps ol {
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
  }
}

@media (max-width: 700px) {
  .panel-facts {
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
  }
}
</style>
