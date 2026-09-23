<script setup lang="ts">
import NepalMap from './NepalMap.vue'

const places = [
  { name: 'Kathmandu', note: 'Capital — HQ office', lat: 27.7172, lng: 85.324 },
  { name: 'Pokhara', note: 'Field survey base', lat: 28.2096, lng: 83.9856 },
  { name: 'Lumbini', note: 'Pure Nepal pilot region', lat: 27.4833, lng: 83.2761 },
  { name: 'Chitwan', note: 'Plan My Nepal trail data', lat: 27.5291, lng: 84.3542 },
]
</script>

<template>
  <section id="home" class="bg-paper pb-24 pt-16">
    <div class="mx-auto grid w-full gap-12 px-6 lg:grid-cols-[1fr_1.1fr] lg:items-center">
      <div>
        <h1 class="font-display text-5xl font-semibold leading-[1.05] text-ink lg:text-6xl">
          We turn Nepal's geography into working software.
        </h1>
        <p class="mt-6 max-w-md text-lg text-ink/70">
          Thimitech designs and builds web GIS platforms — from trekking maps to
          land records — for organisations across Nepal.
        </p>
        <div class="mt-8 flex flex-wrap gap-4">
          <a href="#projects" class="rounded-full bg-flag px-6 py-3 font-medium text-paper transition-colors hover:bg-ink">See our work</a>
          <a href="#contact" class="rounded-full border border-ink px-6 py-3 font-medium text-ink transition-colors hover:bg-ink hover:text-paper">Talk to us</a>
        </div>
      </div>

      <div class="relative isolate h-[420px] overflow-hidden rounded-2xl border border-ink/15 shadow-[6px_6px_0_#0e1b2a]">
        <NepalMap :places="places" />

        <div class="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-md bg-ink/85 px-3 py-2 text-paper backdrop-blur-sm">
          <p class="text-xs font-medium">Kathmandu, Nepal</p>
          <p class="mt-0.5 font-mono text-[11px] text-paper/70">27.7172° N · 85.3240° E</p>
        </div>
      </div>
    </div>
  </section>
</template>