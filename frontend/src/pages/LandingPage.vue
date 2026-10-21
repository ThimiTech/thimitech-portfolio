<script setup lang="ts">
import NavBar from '../components/original/Navbar.vue'
import HeroSection from '../components/original/HeroSection.vue'
import About from '../components/original/About.vue'
import Mission from '../components/original/Mission.vue'
import Services from '../components/original/Services.vue'
import Projects from '../components/original/Projects.vue'
import TechStack from '../components/original/TechStack.vue'
import Team from '../components/original/Team.vue'
import Hiring from '../components/original/Hiring.vue'
import Contact from '../components/original/Contact.vue'
import Footer from '../components/original/Footer.vue'

import '../assets/original.css'
</script>

<template>
  <div class="original-site bg-paper font-body text-ink">
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