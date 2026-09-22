<script setup lang="ts">
import NavBar from '../components/NavBar.vue'
import HeroSection from '../components/HeroSection.vue'
import About from '../components/About.vue'
import Mission from '../components/Mission.vue'
import Services from '../components/Services.vue'
import Projects from '../components/Projects.vue'
import TechStack from '../components/TechStack.vue'
import Team from '../components/Team.vue'
import Hiring from '../components/Hiring.vue'
import Contact from '../components/Contact.vue'
import Footer from '../components/Footer.vue'
</script>

<template>
  <div class="bg-paper font-body text-ink">
    <NavBar />
    <HeroSection />
    <About />
    <Mission />
    <Services />
    <Projects />
    <TechStack />
    <Team />
    <Hiring />
    <Contact />
    <Footer />
  </div>
</template>