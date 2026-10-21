<script setup lang="ts">
defineOptions({ name: 'SiteNavigation' })
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Login from './Login.vue'
import { useAuth } from '../stores/auth'
const { isLoggedIn, userEmail, user, loginOpen, openLogin, closeLogin, logout, fetchMe, hasRole } =
  useAuth()
const open = ref(false)
const route = useRoute()
const landingPath = computed(() => route.path === '/new' ? '/new' : '/')
const router = useRouter()
const denied = computed(() => route.query.denied === '1')
const links = [
  { label: 'Studio', href: '#about' },
  { label: 'Expertise', href: '#services' },
  { label: 'Work', href: '#projects' },
  { label: 'People', href: '#team' },
]
onMounted(() => {
  if (isLoggedIn.value && !user.value) fetchMe()
})
function dismissDenied() {
  const query = { ...route.query }
  delete query.denied
  router.replace({ query })
}
function login() {
  open.value = false
  openLogin()
}
</script>
<template>
  <header class="site-header" @keydown.esc="open = false">
    <div class="studio-wrap site-nav">
      <a :href="landingPath + '#home'" class="site-brand" aria-label="Thimi Tech home"
        ><svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 2C8 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3-7-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5Z"
          /></svg
        ><span
          >thimi<span class="brand-light">tech</span><span class="brand-period">.</span></span
        ></a
      >
      <nav class="desktop-nav" aria-label="Main navigation">
        <a v-for="link in links" :key="link.href" :href="landingPath + link.href">{{ link.label }}</a>
      </nav>
      <div class="nav-actions">
        <a :href="landingPath + '#contact'" class="nav-contact">Let’s talk <span aria-hidden="true">↗</span></a
        ><RouterLink v-if="isLoggedIn && hasRole('employee')" to="/app" class="nav-workspace"
          >Workspace</RouterLink
        ><button v-else-if="!isLoggedIn" class="nav-workspace" @click="login">Staff login</button
        ><button v-if="isLoggedIn" class="nav-signout" @click="logout">Sign out</button
        ><button
          class="mobile-menu"
          :aria-expanded="open"
          aria-controls="mobile-navigation"
          @click="open = !open"
        >
          {{ open ? 'Close' : 'Menu' }}
        </button>
      </div>
    </div>
    <nav
      v-if="open"
      id="mobile-navigation"
      class="studio-wrap mobile-navigation"
      aria-label="Mobile navigation"
    >
      <a v-for="link in links" :key="link.href" :href="landingPath + link.href" @click="open = false">{{
        link.label
      }}</a
      ><a :href="landingPath + '#contact'" @click="open = false">Contact</a
      ><a :href="landingPath + '#hiring'" @click="open = false">Careers</a
      ><RouterLink v-if="isLoggedIn && hasRole('employee')" to="/app" @click="open = false"
        >Workspace</RouterLink
      ><button v-else-if="!isLoggedIn" @click="login">Staff login</button>
    </nav>
  </header>
  <div
    v-if="denied"
    role="alert"
    class="flex items-center justify-between gap-4 border-b border-flag/30 bg-sheet px-6 py-3 text-sm"
  >
    <p>
      The workspace is for staff. Your account ({{ userEmail || 'guest' }}) doesn’t have access yet.
      Ask HR if you were recently hired.
    </p>
    <button aria-label="Dismiss" @click="dismissDenied">Close</button>
  </div>
  <Login :open="loginOpen" @close="closeLogin" />
</template>
