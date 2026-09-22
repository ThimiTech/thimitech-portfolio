<script setup lang="ts">
import NavBar from "@/components/layout/NavBar.vue";
import Footer from "@/components/layout/Footer.vue";
</script>

<template>
  <div class="main_layout">
    <!-- Fixed navbar lives at root level (outside any isolated/stacking
      context) so it always paints above page sections. -->
    <NavBar />
    <main class="content">
      <router-view />
    </main>
    <Footer />
  </div>
</template>
