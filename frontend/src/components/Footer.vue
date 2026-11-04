<script setup lang="ts">
defineOptions({ name: 'SiteFooter' })

import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const landingPath = computed(() => (route.path === '/new' ? '/new' : '/'))

const sitemap = [
  { label: 'Home', href: '#home' },
  { label: 'About Us', href: '#about' },
  { label: 'Mission', href: '#mission' },
  { label: 'Services', href: '#services' },
  { label: 'Projects', href: '#projects' },
  { label: 'Hiring', href: '#hiring' },
  { label: 'Contact', href: '#contact' },
]

const social = [
  { label: 'LinkedIn', href: 'https://www.linkedin.com/company/thimitech' },
  { label: 'Instagram', href: 'https://www.instagram.com/thimitech/' },
  { label: 'Facebook', href: 'https://www.facebook.com/profile.php?id=61585729408478' },
]

const year = new Date().getFullYear()

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <footer class="site-footer studio-invert">
    <div class="studio-wrap">
      <div class="footer-grid">
        <div class="footer-brand">
          <a :href="landingPath + '#home'" class="footer-wordmark" aria-label="Thimi Tech home"
            >thimitech<span>.</span></a
          >
          <p>
            A Nepal-based software studio delivering intelligent digital solutions — geospatial
            systems, AI and modern web platforms for businesses and governments.
          </p>
          <p class="footer-tagline">Reality, into Vision.</p>
        </div>

        <nav class="footer-nav" aria-label="Sitemap">
          <p class="footer-heading">Sitemap</p>
          <ul>
            <li v-for="link in sitemap" :key="link.href">
              <a :href="landingPath + link.href">{{ link.label }}</a>
            </li>
          </ul>
        </nav>

        <nav class="footer-nav" aria-label="Social links">
          <p class="footer-heading">Social</p>
          <ul>
            <li v-for="item in social" :key="item.href">
              <a :href="item.href" target="_blank" rel="noopener noreferrer">
                {{ item.label }} <span aria-hidden="true">↗</span>
              </a>
            </li>
          </ul>
        </nav>

        <div class="footer-nav">
          <p class="footer-heading">Contact</p>
          <ul>
            <li><a href="mailto:info@thimitech.com">info@thimitech.com</a></li>
            <li>Thimi, Bhaktapur, Nepal</li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <p>© {{ year }} Thimi Tech · Nepal</p>
        <button type="button" class="footer-top-link" @click="scrollToTop">
          Back to top <span aria-hidden="true">↑</span>
        </button>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  padding-block: clamp(48px, 6vw, 76px) 28px;
}

.footer-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) repeat(3, minmax(0, 1fr));
  gap: clamp(28px, 4vw, 56px);
  padding-bottom: 44px;
  border-bottom: 1px solid var(--line);
}

.footer-brand {
  display: grid;
  gap: 16px;
  align-content: start;
}

.footer-wordmark {
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.055em;
  color: var(--ink);
  text-decoration: none;
}

.footer-wordmark span {
  font-weight: 300;
}

.footer-brand p {
  max-width: 42ch;
  font-size: 17px;
  line-height: 1.68;
  color: var(--muted);
}

.footer-tagline {
  font-family: var(--font-display);
  font-size: 19px;
  font-style: italic;
  color: var(--ink);
}

.footer-nav ul {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 17px;
  color: var(--muted);
}

.footer-heading {
  margin-bottom: 16px;
  font: 500 12px/1.5 var(--font-mono);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.footer-nav a {
  color: inherit;
  text-decoration: none;
  transition: color 0.15s ease;
}

.footer-nav a:hover {
  color: var(--ink);
}

.footer-bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-top: 22px;
  font: 400 13.5px/1.6 var(--font-mono);
  letter-spacing: 0.06em;
  color: var(--muted);
}

.footer-top-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: none;
  font: inherit;
  color: var(--ink);
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.footer-top-link:hover {
  background: var(--ink);
  color: var(--paper);
}

@media (max-width: 900px) {
  .footer-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .footer-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
