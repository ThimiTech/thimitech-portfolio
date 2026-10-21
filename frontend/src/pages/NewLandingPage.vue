<script setup lang="ts">
import NavBar from '../components/Navbar.vue'
import HeroSection from '../components/HeroSection.vue'
import About from '../components/About.vue'
import Services from '../components/Services.vue'
import Projects from '../components/Projects.vue'
import TechStack from '../components/TechStack.vue'
import Team from '../components/Team.vue'
import Hiring from '../components/Hiring.vue'
import Contact from '../components/Contact.vue'
import Footer from '../components/Footer.vue'
import '../assets/studio.css'
</script>

<template>
  <div class="studio bg-paper font-body text-ink">
    <a href="#main-content" class="skip-link">Skip to content</a>
    <NavBar />
    <main id="main-content">
      <HeroSection />
      <About />
      <Services />
      <Projects />

      <TechStack />
      <Team />
      <Hiring />
      <Contact />
    </main>
    <Footer />
  </div>
</template>
