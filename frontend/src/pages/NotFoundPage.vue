<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

// Rendered inside AppLayout for /app/* misses, standalone for everything else.
const route = useRoute();
const inApp = computed(() => route.path.startsWith("/app"));
</script>

<template>
  <div :class="inApp ? 'py-10' : 'grid min-h-dvh place-items-center bg-paper px-5 font-body text-ink'">
    <div class="mx-auto max-w-md text-center">
      <svg viewBox="0 0 120 80" class="mx-auto h-20 w-28 text-contour/70" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">
        <path d="M60 10c22 0 44 10 46 28s-14 32-40 34-50-8-52-26S38 10 60 10z" />
        <path d="M60 22c14 0 28 6 29 17s-9 21-26 22-31-5-32-16 15-23 29-23z" />
        <path d="M61 33c6 0 12 3 12 7s-4 9-11 9-13-2-13-7 6-9 12-9z" />
        <path d="M54 34l14 12M68 34 54 46" stroke="var(--color-flag)" stroke-width="2" stroke-linecap="round" />
      </svg>
      <p class="mt-4 font-mono text-[11px] tracking-[0.16em] text-ink/45 uppercase">Error 404 · off the map</p>
      <h1 class="mt-2 font-display text-3xl font-medium tracking-tight">We couldn't find that page</h1>
      <p class="mt-3 text-[15px] text-ink/60">
        <span class="readout break-all text-ink/75">{{ route.fullPath }}</span> doesn't exist, or it has moved.
      </p>
      <div class="mt-7 flex flex-wrap justify-center gap-3">
        <RouterLink :to="inApp ? '/app' : '/'" class="btn-ink">{{ inApp ? "Back to dashboard" : "Go to homepage" }}</RouterLink>
        <button type="button" class="btn-ghost" @click="$router.back()">Go back</button>
      </div>
    </div>
  </div>
</template>
