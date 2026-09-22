<script setup lang="ts">
import HeroSection from "@/components/landing-page/HeroSection.vue";
import WhyUs from "@/components/landing-page/WhyUs.vue";
import About from "@/components/landing-page/About.vue";
import Mission from "@/components/landing-page/Mission.vue";
import Services from "@/components/landing-page/Services.vue";
import Projects from "@/components/landing-page/Projects.vue";
import CtaSection from "@/components/landing-page/CtaSection.vue";
import TechStack from "@/components/landing-page/TechStack.vue";
import Team from "@/components/landing-page/Team.vue";
import Hiring from "@/components/landing-page/Hiring.vue";
import Contact from "@/components/landing-page/Contact.vue";
</script>

<template>
  <div>
    <HeroSection />
    <main class="main_layout bg-paper px-8 font-body text-ink lg:px-[6vw]">
      <WhyUs />
      <TechStack />
      <!-- <About /> -->
      <Projects />
      <CtaSection />
      <!-- <Mission />
      <Services />
      <Team /> -->
      <!-- <Hiring /> -->
      <!-- <Contact /> -->
    </main>
  </div>
</template>
