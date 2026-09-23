<script setup lang="ts">
const team = [
  { name: "Ravi Prajapati", role: "FOUNDER", initials: "RP", color: "from-river to-emerald-500" },
  {
    name: "Kshitiz Chaudhary",
    role: "FULL-STACK DEVELOPER",
    initials: "KC",
    color: "from-ink to-river",
  },
  {
    name: "Suresh Rokaya",
    role: "FULL-STACK DEVELOPER",
    initials: "SR",
    color: "from-contour to-flag",
  },
];
</script>

<template>
  <section id="team" class="border-t border-ink/10 bg-paper py-24">
    <div class="mx-auto w-full px-6">
      <div class="max-w-xl">
        <h2 class="font-display text-3xl font-semibold text-ink lg:text-4xl">The team</h2>
        <p class="mt-4 text-ink/65">
          A collective of engineers and innovators,driven by precision and purpose,building geospatial solutions that inspire progress.
        </p>
      </div>

      <div class="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="m in team"
          :key="m.name"
          class="rounded-2xl border border-ink/10 p-6 text-center"
        >
          <div
            :class="m.color"
            class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br font-display text-lg font-semibold text-paper"
          >
            {{ m.initials }}
          </div>
          <h3 class="mt-4 font-display text-base font-medium text-ink">{{ m.name }}</h3>
          <p class="mt-1 font-mono text-xs text-ink/60">{{ m.role }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
