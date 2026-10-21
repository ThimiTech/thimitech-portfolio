<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
const TerrainScene = defineAsyncComponent(() => import('./terrain/TerrainScene.vue'))
</script>
<template>
  <section id="home" class="studio-hero">
    <div class="studio-wrap hero-layout">
      <div class="hero-copy">
        <p class="studio-kicker">Geospatial thinking. Real-world software.</p>
        <h1>From place <br />to <span>possibility.</span></h1>
        <p class="hero-description">
          We turn complex data into maps, platforms, and tools that move people forward.
        </p>
        <a href="#projects" class="studio-button"
          >Explore our work <span aria-hidden="true">↗</span></a
        >
      </div>
      <figure class="hero-terrain">
        <div class="terrain-frame"><TerrainScene /></div>
        <figcaption>
          <span>Terrain / data / possibility</span
          ><span class="hidden sm:inline">An abstract landscape study</span>
        </figcaption>
      </figure>
    </div>
    <div class="studio-wrap hero-footnote">
      <span>Rooted in Nepal. Building beyond borders.</span
      ><a href="#services">Discover what we do <span aria-hidden="true">↗</span></a>
    </div>
  </section>
</template>
