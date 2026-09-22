<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

const SCROLL_TINT_THRESHOLD = 24;
const NAV_HEIGHT = 64;

const open = ref(false);
const scrolled = ref(false);
const pastHero = ref(false);
const links = [
  { label: "Home", href: "#home" },
  { label: "About Us", href: "#about" },
  { label: "Mission", href: "#mission" },
  { label: "Services", href: "#services" },
  { label: "Projects", href: "#projects" },
  { label: "Team", href: "#team" },
  { label: "Hiring", href: "#hiring" },
  { label: "Contact", href: "#contact" },
];

let scrollRaf = 0;
let heroObserver: IntersectionObserver | null = null;

function readScrolled(): void {
  scrolled.value = window.scrollY > SCROLL_TINT_THRESHOLD;
}

function onScroll(): void {
  if (scrollRaf !== 0) return;
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0;
    readScrolled();
  });
}

onMounted(() => {
  readScrolled();
  window.addEventListener("scroll", onScroll, { passive: true });

  const hero = document.getElementById("home");
  if (hero) {
    heroObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        pastHero.value = entry ? !entry.isIntersecting : false;
      },
      { rootMargin: `-${NAV_HEIGHT}px 0px 0px 0px`, threshold: 0 },
    );
    heroObserver.observe(hero);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("scroll", onScroll);
  heroObserver?.disconnect();
  heroObserver = null;
  if (scrollRaf !== 0) {
    cancelAnimationFrame(scrollRaf);
    scrollRaf = 0;
  }
});
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-nav border-b text-paper transition duration-200 ease-in-out"
    :class="
      pastHero
        ? 'border-white/10 bg-[#081422]/92 backdrop-blur-md'
        : scrolled
          ? 'border-white/10 bg-[#16304a]/45 backdrop-blur-md'
          : 'border-transparent bg-transparent'
    "
  >
    <div class="flex min-h-16 items-center justify-between gap-6 px-6 py-3 lg:px-16 lg:py-4">
      <a
        href="#home"
        aria-label="Thimitech home"
        class="flex items-center pl-1 font-display text-xl font-semibold tracking-tight"
      >
        <span>thimi</span>
        <span
          class="ml-0.5 rounded-md border border-white/10 bg-black px-1.5 py-0.5 text-[0.92em] leading-none"
          >Tech</span
        >
      </a>

      <nav class="hidden items-center gap-7 lg:flex">
        <a
          v-for="l in links"
          :key="l.href"
          :href="l.href"
          class="text-base font-medium text-paper/70 transition-colors duration-200 hover:text-paper"
          >{{ l.label }}</a
        >
      </nav>

      <div class="flex items-center gap-4">
        <a
          href="#contact"
          class="hidden rounded-full bg-paper px-5 py-2 text-base font-medium text-ink transition-opacity duration-200 hover:opacity-90 lg:inline-block"
          >Join Us</a
        >
        <button class="lg:hidden" aria-label="Menu" :aria-expanded="open" @click="open = !open">
          <span class="mb-1.5 block h-0.5 w-6 bg-paper"></span>
          <span class="mb-1.5 block h-0.5 w-6 bg-paper"></span>
          <span class="block h-0.5 w-6 bg-paper"></span>
        </button>
      </div>
    </div>

    <div
      v-if="open"
      class="mx-6 flex flex-col gap-1 rounded-2xl bg-[#16304a]/95 px-5 py-4 backdrop-blur-md lg:hidden"
    >
      <a
        v-for="l in links"
        :key="l.href"
        :href="l.href"
        class="py-2 text-base text-paper/80 hover:text-paper"
        @click="open = false"
        >{{ l.label }}</a
      >
      <a
        href="#contact"
        class="mt-2 rounded-full bg-paper px-5 py-2 text-center text-base font-medium text-ink"
        @click="open = false"
        >Join Us</a
      >
    </div>
  </header>
</template>

<style scoped>
a:focus-visible,
button:focus-visible {
  outline: 2px solid var(--hero-accent, #ffd9a0);
  outline-offset: 3px;
}
</style>
