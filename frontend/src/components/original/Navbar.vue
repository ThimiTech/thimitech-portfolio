<script setup lang="ts">
defineOptions({ name: 'OriginalNavbar' })

// The root page keeps its historical import path, but there is now one nav.
import Navbar from '../Navbar.vue'
</script>

<template>
  <Navbar />
</template>
