<script setup lang="ts">
defineOptions({ name: 'OriginalHeroSection' })

// The root page keeps its historical import path; the design is shared.
import HeroSection from '../HeroSection.vue'
</script>

<template>
  <HeroSection variant="root" />
</template>
