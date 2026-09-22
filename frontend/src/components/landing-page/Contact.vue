<script setup lang="ts">
const companyEmail = 'info@thimitech.com'
const companyPhone = '+977 1-4123456'
</script>

<template>
  <section id="contact" class="bg-ink py-24 text-paper">
    <div class="px-6">
      <div class="max-w-lg">
        <h2 class="font-display text-3xl font-semibold lg:text-4xl">Have a map in mind?</h2>
        <p class="mt-4 text-paper/70">
          Tell us what your team needs to see and decide. We reply within two working days.
        </p>
      </div>

      <div class="mt-12 grid gap-8 border-t border-paper/15 pt-10 sm:grid-cols-3">
        <div>
          <p class="text-xs uppercase tracking-wide text-paper/50">Email</p>
          <a :href="'mailto:' + companyEmail" class="mt-2 block font-mono text-lg text-paper hover:text-flag">{{ companyEmail }}</a>
        </div>
        <div>
          <p class="text-xs uppercase tracking-wide text-paper/50">Phone</p>
          <a :href="'tel:' + companyPhone" class="mt-2 block font-mono text-lg text-paper hover:text-flag">{{ companyPhone }}</a>
        </div>
        <div>
          <p class="text-xs uppercase tracking-wide text-paper/50">Location</p>
          <p class="mt-2 text-lg text-paper">Kathmandu, Nepal</p>
        </div>
      </div>

      
        <a :href="'mailto:' + companyEmail"
        class="mt-10 inline-block rounded-full bg-flag px-7 py-3 font-medium text-paper transition-colors hover:bg-paper hover:text-ink"
      >
        Send us an email
      </a>
    </div>
  </section>
</template>