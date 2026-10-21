<script setup lang="ts">
defineOptions({ name: 'StudioFooter' })
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const landingPath = computed(() => route.path === '/new' ? '/new' : '/')
const social = [
  { label: 'LinkedIn', href: 'https://www.linkedin.com/company/thimitech' },
  { label: 'Instagram', href: 'https://www.instagram.com/thimitech/' },
  { label: 'Facebook', href: 'https://www.facebook.com/profile.php?id=61585729408478' },
]
const year = new Date().getFullYear()
</script>
<template>
  <footer class="studio-footer">
    <div class="studio-wrap">
      <div class="footer-top">
        <a :href="landingPath + '#home'" class="footer-wordmark" aria-label="Thimi Tech home"
          >thimitech<span>.</span></a
        >
        <p>A little perspective<br />changes everything.</p>
      </div>
      <div class="footer-bottom">
        <p>© {{ year }} Thimi Tech · Nepal</p>
        <nav aria-label="Social links">
          <a
            v-for="s in social"
            :key="s.label"
            :href="s.href"
            target="_blank"
            rel="noopener noreferrer"
            >{{ s.label }} ↗</a
          >
        </nav>
        <a :href="landingPath + '#hiring'">Careers ↗</a>
      </div>
    </div>
  </footer>
</template>
