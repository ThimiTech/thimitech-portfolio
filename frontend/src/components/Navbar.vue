<script setup lang="ts">
defineOptions({ name: 'SiteNavigation' })

import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Login from './Login.vue'
import LogoMark from './LogoMark.vue'
import { useAuth } from '../stores/auth'

const { isLoggedIn, userEmail, user, loginOpen, openLogin, closeLogin, logout, fetchMe, hasRole } =
  useAuth()

const route = useRoute()
const router = useRouter()
const open = ref(false)
const scrolled = ref(false)

const landingPath = computed(() => (route.path === '/new' ? '/new' : '/'))
const denied = computed(() => route.query.denied === '1')

const links = [
  { label: 'Home', href: '#home' },
  { label: 'About Us', href: '#about' },
  { label: 'Mission', href: '#mission' },
  { label: 'Services', href: '#services' },
  { label: 'Projects', href: '#projects' },
  { label: 'Team', href: '#team' },
  { label: 'Hiring', href: '#hiring' },
  { label: 'Contact', href: '#contact' },
]

/** On /new every anchor stays inside the new design; on / it stays a bare hash. */
function sectionHref(hash: string) {
  return landingPath.value === '/new' ? `/new${hash}` : hash
}

function onScroll() {
  scrolled.value = window.scrollY > 24
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  if (isLoggedIn.value && !user.value) fetchMe()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
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

function signOut() {
  open.value = false
  logout()
}
</script>

<template>
  <header
    class="public-nav"
    :class="{ 'is-scrolled': scrolled, 'is-open': open }"
    @keydown.esc="open = false"
  >
    <div class="public-nav__inner">
      <a :href="sectionHref('#home')" class="brand" aria-label="Thimi Tech home">
        <LogoMark :size="46" />
        <span class="brand__word"
          >thimi<span class="brand__light">tech</span><span class="brand__dot">.</span></span
        >
      </a>

      <nav class="desktop-nav" aria-label="Main navigation">
        <a
          v-for="link in links"
          :key="link.href"
          :href="sectionHref(link.href)"
          class="desktop-nav__link"
        >
          <span class="desktop-nav__label">{{ link.label }}</span>
        </a>
      </nav>

      <div class="nav-actions">
        <a :href="sectionHref('#contact')" class="nav-cta">
          <span>Start a project</span>
          <span aria-hidden="true">↗</span>
        </a>

        <RouterLink v-if="isLoggedIn && hasRole('employee')" to="/app" class="nav-staff"
          >Workspace</RouterLink
        >
        <button v-else-if="!isLoggedIn" class="nav-staff" @click="login">Staff login</button>
        <button v-if="isLoggedIn" class="nav-signout" @click="signOut">Logout</button>

        <button
          class="menu-toggle"
          type="button"
          :aria-expanded="open"
          aria-controls="mobile-navigation"
          :aria-label="open ? 'Close menu' : 'Open menu'"
          @click="open = !open"
        >
          <span class="menu-toggle__line"></span>
          <span class="menu-toggle__line"></span>
        </button>
      </div>
    </div>

    <Transition name="mobile-menu">
      <nav
        v-if="open"
        id="mobile-navigation"
        class="mobile-nav"
        aria-label="Mobile navigation"
        @click="open = false"
      >
        <div class="mobile-nav__inner">
          <a
            v-for="link in links"
            :key="link.href"
            :href="sectionHref(link.href)"
            class="mobile-nav__link"
          >
            <span>{{ link.label }}</span>
            <span class="mobile-nav__arrow" aria-hidden="true">↗</span>
          </a>

          <div class="mobile-nav__actions">
            <a :href="sectionHref('#contact')" class="mobile-nav__cta">
              Start a project <span aria-hidden="true">↗</span>
            </a>
            <RouterLink v-if="isLoggedIn && hasRole('employee')" to="/app" class="mobile-nav__staff"
              >Workspace</RouterLink
            >
            <button v-else-if="!isLoggedIn" class="mobile-nav__staff" @click="login">
              Staff login
            </button>
            <button v-if="isLoggedIn" class="mobile-nav__staff" @click="signOut">Logout</button>
          </div>
        </div>
      </nav>
    </Transition>
  </header>

  <Transition name="denied">
    <div v-if="denied" role="alert" class="denied-banner">
      <p>
        The workspace is for staff. Your account ({{ userEmail || 'guest' }}) doesn’t have access
        yet. Ask HR if you were recently hired.
      </p>
      <button type="button" aria-label="Dismiss" @click="dismissDenied">Close</button>
    </div>
  </Transition>

  <Login :open="loginOpen" @close="closeLogin" />
</template>

<style scoped>
.public-nav {
  --nav-paper: #ffffff;
  --nav-ink: #0a0a0a;
  --nav-muted: rgb(10 10 10 / 0.76);
  --nav-line: rgb(10 10 10 / 0.12);

  position: sticky;
  top: 0;
  z-index: 1000;
  color: var(--nav-ink);
  background: rgb(255 255 255 / 0.94);
  border-bottom: 1px solid var(--nav-line);
  backdrop-filter: blur(18px) saturate(1.1);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
  transition:
    box-shadow 0.3s ease,
    background 0.3s ease;
}

.public-nav.is-scrolled {
  background: rgb(255 255 255 / 0.99);
  box-shadow: 0 14px 40px rgb(10 10 10 / 0.08);
}

.public-nav__inner {
  display: flex;
  align-items: center;
  gap: 22px;
  width: min(100% - 56px, 1400px);
  min-height: 94px;
  margin-inline: auto;
}

.brand {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.brand__word {
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.055em;
}

.brand__light {
  font-weight: 300;
}

.brand__dot {
  color: var(--nav-ink);
}

.desktop-nav {
  display: flex;
  align-items: center;
  gap: clamp(16px, 1.7vw, 30px);
  margin-inline: auto;
}

.desktop-nav__link {
  position: relative;
  padding-block: 8px;
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.005em;
  color: var(--nav-muted);
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s ease;
}

.desktop-nav__label {
  position: relative;
}

.desktop-nav__label::after {
  content: '';
  position: absolute;
  right: 0;
  bottom: -6px;
  left: 0;
  height: 2px;
  background: var(--nav-ink);
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.25s ease;
}

.desktop-nav__link:hover {
  color: var(--nav-ink);
}

.desktop-nav__link:hover .desktop-nav__label::after {
  transform: scaleX(1);
  transform-origin: left;
}

.nav-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 18px;
}

.nav-cta {
  display: inline-flex;
  align-items: center;
  gap: 18px;
  padding: 13px 18px;
  border: 1px solid var(--nav-ink);
  border-radius: 2px;
  background: var(--nav-ink);
  color: #ffffff;
  font: 500 12px/1.2 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
  white-space: nowrap;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.nav-cta:hover {
  background: transparent;
  color: var(--nav-ink);
}

.nav-staff,
.nav-signout {
  padding: 4px 0;
  border: 0;
  background: none;
  font: 400 12.5px/1.4 var(--font-mono);
  letter-spacing: 0.06em;
  color: var(--nav-muted);
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.2s ease;
}

.nav-staff:hover,
.nav-signout:hover {
  color: var(--nav-ink);
}

.menu-toggle {
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 44px;
  height: 44px;
  margin-right: -8px;
  border: 0;
  background: none;
  color: inherit;
  cursor: pointer;
}

.menu-toggle__line {
  display: block;
  width: 26px;
  height: 2px;
  background: currentColor;
  transition: transform 0.25s ease;
}

.is-open .menu-toggle__line:first-child {
  transform: translateY(4px) rotate(45deg);
}

.is-open .menu-toggle__line:last-child {
  transform: translateY(-4px) rotate(-45deg);
}

.mobile-nav {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  max-height: calc(100dvh - 94px);
  overflow-y: auto;
  background: rgb(255 255 255 / 0.99);
  border-bottom: 1px solid var(--nav-line);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.mobile-nav__inner {
  display: flex;
  flex-direction: column;
  width: min(100% - 40px, 1400px);
  margin-inline: auto;
  padding-block: 14px 28px;
}

.mobile-nav__link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-block: 16px;
  border-bottom: 1px solid var(--nav-line);
  font-family: var(--font-display);
  font-size: clamp(24px, 6.2vw, 32px);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: currentColor;
  text-decoration: none;
}

.mobile-nav__arrow {
  color: var(--nav-muted);
  font-size: 18px;
}

.mobile-nav__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
  padding-top: 24px;
}

.mobile-nav__cta {
  display: inline-flex;
  align-items: center;
  gap: 24px;
  padding: 14px 18px;
  border-radius: 2px;
  background: var(--nav-ink);
  color: #ffffff;
  font: 500 12px/1.2 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
}

.mobile-nav__staff {
  padding: 4px 0;
  border: 0;
  background: none;
  font: 400 12.5px/1.4 var(--font-mono);
  color: var(--nav-muted);
  text-decoration: none;
  cursor: pointer;
}

.denied-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--nav-line);
  background: #ffffff;
  color: #0a0a0a;
  font-size: 14px;
  line-height: 1.6;
}

.denied-banner button {
  flex: 0 0 auto;
  padding: 4px 0;
  border: 0;
  border-bottom: 1px solid #0a0a0a;
  background: none;
  font: 500 11px/1.2 var(--font-mono);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #0a0a0a;
  cursor: pointer;
}

.mobile-menu-enter-active,
.mobile-menu-leave-active,
.denied-enter-active,
.denied-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.mobile-menu-enter-from,
.mobile-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.denied-enter-from,
.denied-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.public-nav :is(a, button):focus-visible {
  outline: 2px solid #0a0a0a;
  outline-offset: 4px;
}

@media (max-width: 1279px) {
  .desktop-nav {
    gap: 16px;
  }

  .desktop-nav__link {
    font-size: 16px;
  }

  .brand__word {
    font-size: 27px;
  }
}

@media (max-width: 1119px) {
  .desktop-nav,
  .nav-cta,
  .nav-staff,
  .nav-signout {
    display: none;
  }

  .menu-toggle {
    display: flex;
  }

  .public-nav__inner {
    justify-content: space-between;
    min-height: 80px;
  }

  .mobile-nav {
    max-height: calc(100dvh - 80px);
  }
}

@media (max-width: 767px) {
  .public-nav__inner {
    width: calc(100% - 32px);
  }

  .brand {
    gap: 10px;
  }

  .brand__word {
    font-size: 25px;
  }

  .denied-banner {
    align-items: flex-start;
    padding: 12px 16px;
    font-size: 13px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .public-nav,
  .desktop-nav__link,
  .desktop-nav__label::after,
  .nav-cta,
  .nav-staff,
  .nav-signout,
  .menu-toggle__line,
  .mobile-menu-enter-active,
  .mobile-menu-leave-active,
  .denied-enter-active,
  .denied-leave-active {
    transition: none;
  }
}
</style>
