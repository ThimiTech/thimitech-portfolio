<script setup lang="ts">
import NepalMap from "./NepalMap.vue";

const places = [
  { name: "Kathmandu", note: "Capital — HQ office", lat: 27.7172, lng: 85.324 },
  { name: "Pokhara", note: "Field survey base", lat: 28.2096, lng: 83.9856 },
  { name: "Lumbini", note: "Pure Nepal pilot region", lat: 27.4833, lng: 83.2761 },
  { name: "Chitwan", note: "Plan My Nepal trail data", lat: 27.5291, lng: 84.3542 },
];
</script>


<template>
  <section id="home" class="bg-paper">
    <div class="grid min-h-[600px] lg:grid-cols-2">

      <!-- Left side: Text -->
      <div class="flex flex-col justify-center px-8 py-12 lg:px-12 xl:px-16">
        <h1 class="max-w-2xl font-body text-5xl font-medium leading-tight text-ink lg:text-6xl">
          Turning Geographic Data into Digital Solutions.
        </h1>

        <p class="mt-8 max-w-2xl text-lg leading-relaxed text-ink/70">
          Thimi Tech designs and develops modern web GIS platforms that turn complex spatial data
          into simple, interactive experiences. Our platforms combine GIS, web mapping, and
          software technologies to make geographic information more accessible and useful. We help
          organisations visualise, manage, and analyse their location-based data efficiently. With
          a focus on practical design and reliable technology, we create scalable solutions
          tailored to each organisation. Our goal is to connect people, places, and data through
          innovative geospatial technology.
        </p>

        <div class="mt-8 flex flex-wrap gap-3">
          <a
            href="#projects"
            class="rounded-full bg-ink px-6 py-3 font-medium text-paper transition-colors hover:bg-river"
          >
            See our work
          </a>

          <a
            href="#contact"
            class="rounded-full border border-ink px-6 py-3 font-medium text-ink transition-colors hover:bg-ink hover:text-paper"
          >
            Talk to us
          </a>
        </div>
      </div>

      <!-- Right side: Full-height map -->
      <div class="relative isolate min-h-[400px] overflow-hidden rounded-2xl border border-ink/15 m-6 lg:my-6 lg:mr-6 lg:ml-0 lg:min-h-[600px]">
        <NepalMap :places="places" />

        <div
          class="pointer-events-none absolute bottom-4 left-4 z-[1000] rounded-md bg-ink/85 px-3 py-2 text-paper backdrop-blur-sm"
        >
          <p class="text-sm font-medium">Kathmandu, Nepal</p>
          <p class="mt-1 font-mono text-xs text-paper/70">
            27.7172° N · 85.3240° E
          </p>
        </div>
      </div>

    </div>
  </section>
</template>
