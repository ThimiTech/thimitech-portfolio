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
  <section id="home" class="bg-paper pb-20 pt-10">
    <div class="mx-auto max-w-[1280px] px-6">
      <div class="flex items-start justify-between border-b border-ink/10 pb-8">
        <h1 class="max-w-xl font-body text-6xl font-medium leading-[1.05] text-ink">
          Turning Geographic Data into Digital Solutions. <em class="italic"></em>
        </h1>
        <a
          href="#contact"
          class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-flag text-paper transition-transform hover:-translate-y-0.5 hover:-rotate-45"
        >
          <svg
            viewBox="0 0 24 24"
            class="h-6 w-6"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M7 17L17 7M17 7H7M17 7v10" />
          </svg>
        </a>
      </div>

      <div class="mt-10 grid gap-10 lg:grid-cols-[0.9fr_1.3fr] lg:items-end">
        <div>
          <p class="mt-6 max-w-2xl text-base leading-relaxed text-ink/60">
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
              >See our work</a
            >
            <a
              href="#contact"
              class="rounded-full border border-ink px-6 py-3 font-medium text-ink transition-colors hover:bg-ink hover:text-paper"
              >Talk to us</a
            >
          </div>
        </div>

        <div class="relative isolate h-[380px] overflow-hidden rounded-2xl border border-ink/15">
          <NepalMap :places="places" />
          <div
            class="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded-md bg-ink/85 px-3 py-2 text-paper backdrop-blur-sm"
          >
            <p class="text-xs font-medium">Kathmandu, Nepal</p>
            <p class="mt-0.5 font-mono text-[11px] text-paper/70">27.7172° N · 85.3240° E</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
