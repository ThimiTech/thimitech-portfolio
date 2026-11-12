<script setup lang="ts">
import { reactive, ref } from 'vue'
import { isAxiosError } from 'axios'
import api from '../../api/api'

// `website` is a honeypot: people never see it, bots fill it, the API quietly drops those.
const form = reactive({ name: '', email: '', company: '', phone: '', message: '', website: '' })
const sending = ref(false)
const sent = ref(false)
const error = ref('')

async function send() {
  error.value = ''
  sending.value = true
  try {
    await api.post('inquiries/', form)
    sent.value = true
  } catch (e) {
    const res = isAxiosError(e) ? e.response : undefined
    const first = res?.data && typeof res.data === 'object' ? Object.entries(res.data as Record<string, unknown>)[0] : undefined
    const detail = Array.isArray(first?.[1]) ? String(first[1][0]) : ''
    error.value =
      res?.status === 429
        ? 'That is a lot of messages in a short time. Please try again in a while, or email us.'
        : res?.status === 400 && first
          ? `${first[0]}: ${detail}`
          : 'We could not send that. Please try again, or email info@thimitech.com.'
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <section id="contact" class="contact daylight" aria-labelledby="contact-title">
    <div class="wrap grid">
      <div>
        <p class="kicker">Altitude 0 m · you have landed</p>
        <h2 id="contact-title">Let’s put it<br />on the map.</h2>
        <p class="intro">
          Tell us what you are working on and what data you already have. We will suggest where to
          start, what it takes, and whether we are the right team for it.
        </p>
        <dl class="details">
          <div><dt>Write</dt><dd><a href="mailto:info@thimitech.com">info@thimitech.com</a></dd></div>
          <div><dt>Studio</dt><dd>Kathmandu, Nepal · GMT +5:45</dd></div>
          <div><dt>How it goes</dt><dd>Discovery call, scoped proposal, two-week delivery cycles</dd></div>
        </dl>
      </div>

      <div v-if="sent" class="done" role="status">
        <p class="kicker">Message received</p>
        <p class="done-title">Thank you, {{ form.name.split(' ')[0] }}.</p>
        <p>Someone from the team will reply to {{ form.email }} within two working days.</p>
      </div>
      <form v-else @submit.prevent="send">
        <label class="f">
          <span>Your name</span>
          <input v-model.trim="form.name" required maxlength="120" autocomplete="name" />
        </label>
        <label class="f">
          <span>Email</span>
          <input v-model.trim="form.email" type="email" required autocomplete="email" />
        </label>
        <label class="f">
          <span>Organisation <i>optional</i></span>
          <input v-model.trim="form.company" maxlength="160" autocomplete="organization" />
        </label>
        <label class="f">
          <span>Phone <i>optional</i></span>
          <input v-model.trim="form.phone" type="tel" maxlength="30" autocomplete="tel" />
        </label>
        <label class="f wide">
          <span>What are you working on?</span>
          <textarea v-model.trim="form.message" rows="4" required minlength="10" maxlength="5000" />
        </label>
        <label class="trap" aria-hidden="true">
          Website
          <input v-model="form.website" tabindex="-1" autocomplete="off" />
        </label>
        <p v-if="error" class="err wide" role="alert">{{ error }}</p>
        <button type="submit" class="btn btn-solid wide" :disabled="sending">
          {{ sending ? 'Sending…' : 'Send message' }} <span aria-hidden="true">→</span>
        </button>
      </form>
    </div>
  </section>
</template>

<style scoped>
.contact {
  padding-block: clamp(80px, 12vw, 170px);
  border-top: 1px solid var(--line);
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: clamp(36px, 6vw, 110px);
}
h2 {
  margin: 16px 0 22px;
}
.intro {
  max-width: 44ch;
  margin: 0;
  font-size: clamp(16px, 1.3vw, 19px);
  line-height: 1.6;
  color: var(--dim);
}
.details {
  display: grid;
  gap: 16px;
  margin: 36px 0 0;
  padding-top: 24px;
  border-top: 1px solid var(--line);
}
.details dt,
.f span {
  font: 400 10.5px/1.6 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--dim);
}
.details dd {
  margin: 2px 0 0;
  font-size: 18px;
}
.details a {
  color: var(--fg);
}

form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 26px 24px;
}
.wide {
  grid-column: 1 / -1;
}
.f {
  display: grid;
  gap: 6px;
}
.f i {
  font-style: normal;
  opacity: 0.6;
}
.f input,
.f textarea {
  width: 100%;
  padding: 8px 0 10px;
  border: 0;
  border-bottom: 1px solid var(--line-strong);
  border-radius: 0;
  background: none;
  font: inherit;
  font-size: 19px;
  color: var(--fg);
  outline: none;
  resize: vertical;
  transition: border-color 0.2s ease;
}
.f input:focus,
.f textarea:focus {
  border-bottom-color: var(--signal);
  box-shadow: 0 1px 0 var(--signal);
}
.trap {
  position: absolute;
  left: -9999px;
}
.err {
  margin: 0;
  color: #b3261e;
}
button.wide {
  justify-self: start;
}

.done {
  align-self: center;
  padding: clamp(24px, 3vw, 44px);
  border: 1px solid var(--line-strong);
}
.done p {
  margin: 0;
  font-size: 18px;
  line-height: 1.55;
  color: var(--dim);
}
.done .done-title {
  margin: 14px 0 10px;
  font-size: clamp(30px, 3.4vw, 52px);
  font-weight: 500;
  letter-spacing: -0.04em;
  color: var(--fg);
}

@media (max-width: 860px) {
  .grid,
  form {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
