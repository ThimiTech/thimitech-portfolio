<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";
import { ME } from "../components/app/nav";

// Personal pages (profile, pay, assets) share this strip of links instead of three sidebar entries.
const route = useRoute();
const active = (to: string) => route.path === to || route.path.startsWith(to + "/");
</script>

<template>
  <div>
    <nav aria-label="My pages" class="mb-6 flex gap-1 overflow-x-auto border-b border-ink/15">
      <RouterLink
        v-for="m in ME"
        :key="m.to"
        :to="m.to"
        class="-mb-px shrink-0 border-b-2 px-3 py-2.5 text-sm whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
        :class="active(m.to) ? 'border-flag font-medium text-ink' : 'border-transparent text-ink/55 hover:text-ink'"
        :aria-current="active(m.to) ? 'page' : undefined"
      >
        {{ m.label }}
      </RouterLink>
    </nav>
    <RouterView />
  </div>
</template>
