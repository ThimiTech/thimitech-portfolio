<script setup lang="ts">
import { ref } from "vue";
import Login from "./Login.vue";

const open = ref(false);
const loginOpen = ref(false);

const links = [
  { label: "Home", href: "#home" },
  { label: "About Us", href: "#about" },
  { label: "Mission", href: "#mission" },
  { label: "Services", href: "#services" },
  { label: "Projects", href: "#projects" },
  { label: "Team", href: "#team" },
  { label: "Hiring", href: "#hiring" },
  { label: "Contact", href: "#contact" },
  { label: "Footer", href: "#Footer" },
];
</script>

<template>
  <header class="sticky top-0 z-[9999] border-b border-ink/10 bg-paper shadow-sm">
    <div class="mx-auto flex h-16 w-full items-center justify-between px-6">
      <a href="#home" class="flex items-center gap-2 font-display text-lg font-semibold text-ink">
        <svg viewBox="0 0 24 24" class="h-6 w-6 text-flag">
          <path
            fill="currentColor"
            d="M12 2C8 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3-7-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5Z"
          />
        </svg>
        Thimitech
      </a>

      <nav class="hidden items-center gap-6 lg:flex">
        <a
          v-for="l in links"
          :key="l.href"
          :href="l.href"
          class="text-sm font-medium text-ink/70 hover:text-ink"
          >{{ l.label }}</a
        >

        <button
          aria-label="Log in"
          class="flex h-9 w-9 items-center justify-center rounded-full border border-ink/15 text-ink/70 transition-colors hover:border-ink hover:text-ink"
          @click="loginOpen = true"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-4.5 w-4.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M20 21a8 8 0 10-16 0" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </button>

        <a
          href="#contact"
          class="rounded-full bg-ink px-5 py-2 text-sm font-medium text-paper transition-colors hover:bg-river"
          >Start a project</a
        >
      </nav>

      <button class="lg:hidden" aria-label="Menu" @click="open = !open">
        <span class="mb-1.5 block h-0.5 w-6 bg-ink"></span>
        <span class="mb-1.5 block h-0.5 w-6 bg-ink"></span>
        <span class="block h-0.5 w-6 bg-ink"></span>
      </button>
    </div>

    <div
      v-if="open"
      class="flex flex-col gap-1 border-t border-ink/10 bg-paper px-6 py-4 lg:hidden"
    >
      <a
        v-for="l in links"
        :key="l.href"
        :href="l.href"
        class="py-2 text-ink/80"
        @click="open = false"
        >{{ l.label }}</a
      >
      <button
        class="flex items-center gap-2 py-2 text-left text-ink/80"
        @click="
          open = false;
          loginOpen = true;
        "
      >
        <svg
          viewBox="0 0 24 24"
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M20 21a8 8 0 10-16 0" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        Log in
      </button>
      <a
        href="#contact"
        class="mt-2 rounded-full bg-ink px-5 py-2 text-center text-paper"
        @click="open = false"
        >Start a project</a
      >
    </div>
  </header>

  <Login :open="loginOpen" @close="loginOpen = false" />
</template>
