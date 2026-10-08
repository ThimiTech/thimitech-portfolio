<script setup lang="ts">
import { ref } from "vue";
import Login from "./Login.vue";
import { useAuth } from "../stores/auth";

const { isLoggedIn, userEmail, loginOpen, openLogin, closeLogin, logout } = useAuth();

const open = ref(false);

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
</script>

<template>
  <header class="sticky top-0 z-[9999] border-b border-ink/10 bg-paper">
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

        <!-- Logged out -->
        <button
          v-if="!isLoggedIn"
          class="text-sm font-medium text-ink/70 hover:text-ink"
          @click="openLogin"
        >
          Login
        </button>

        <!-- Logged in -->
        <div v-else class="flex items-center gap-3">
          <span
            class="flex h-8 w-8 items-center justify-center rounded-full bg-river text-sm font-semibold uppercase text-paper"
            :title="userEmail ?? ''"
          >
            {{ userEmail?.[0] ?? "U" }}
          </span>
          <button class="text-sm font-medium text-ink/70 hover:text-ink" @click="logout">
            Logout
          </button>
        </div>
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
        v-if="!isLoggedIn"
        class="py-2 text-left text-ink/80"
        @click="
          open = false;
          openLogin();
        "
      >
        Login
      </button>

      <div v-else class="flex items-center justify-between py-2">
        <span class="flex items-center gap-2 text-ink/80">
          <span
            class="flex h-8 w-8 items-center justify-center rounded-full bg-river text-sm font-semibold uppercase text-paper"
          >
            {{ userEmail?.[0] ?? "U" }}
          </span>
          {{ userEmail }}
        </span>
        <button
          class="text-sm text-ink/60"
          @click="
            open = false;
            logout();
          "
        >
          Logout
        </button>
      </div>
    </div>
  </header>

  <Login :open="loginOpen" @close="closeLogin" />
</template>
