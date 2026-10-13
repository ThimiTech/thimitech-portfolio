<script setup lang="ts">
const companyEmail = 'info@thimitech.com'
const companyPhone = '+977 1-4123456'

const channels = [
  {
    label: 'Email',
    value: companyEmail,
    href: 'mailto:' + companyEmail,
    icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    accent: 'text-river border-river/30 bg-river/10',
  },
  {
    label: 'Phone',
    value: companyPhone,
    href: 'tel:' + companyPhone.replace(/\s|-/g, ''),
    icon: 'M3 5a2 2 0 012-2h2.28a1 1 0 01.98.804l1.2 6A1 1 0 018.72 11l-1.64 1.64a12.05 12.05 0 006.28 6.28L14.99 17.28a1 1 0 011.196-.732l6 1.2a1 1 0 01.804.98V21a2 2 0 01-2 2h-1C9.163 23 1 14.837 1 4V3a2 2 0 012-2',
    accent: 'text-contour border-contour/30 bg-contour/10',
  },
  {
    label: 'Location',
    value: 'Kathmandu, Nepal',
    href: null,
    icon: 'M12 21c-4.5-4.5-7-8.25-7-11.5A7 7 0 0112 2a7 7 0 017 7.5c0 3.25-2.5 7-7 11.5zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z',
    accent: 'text-flag border-flag/30 bg-flag/10',
  },
]
</script>

<template>
  <section id="contact" class="bg-ink py-32 text-paper">
    <div class="mx-auto max-w-none px-8">
      <div class="grid gap-14 lg:grid-cols-[1fr_1.1fr] lg:items-center">

        <div>
          <p class="font-mono text-xs uppercase tracking-wide text-river">Contact</p>
          <h2 class="mt-3 font-display text-4xl font-semibold lg:text-5xl">
            Have a map in mind?
          </h2>
          <p class="mt-5 max-w-sm text-paper/60">
            Tell us what your team needs to see and decide. We reply within two
            working days.
          </p>

          <a
            :href="'mailto:' + companyEmail"
            class="mt-8 inline-flex items-center gap-2 rounded-full bg-flag px-7 py-3 font-medium text-paper transition-colors hover:bg-paper hover:text-ink"
          >
            Send us an email →
          </a>
        </div>

        <div class="grid gap-5 sm:grid-cols-2">
          <div
            v-for="c in channels"
            :key="c.label"
            class="rounded-2xl border border-paper/10 bg-paper/5 p-6"
            :class="c.label === 'Location' ? 'sm:col-span-2' : ''"
          >
            <div :class="c.accent" class="flex h-10 w-10 items-center justify-center rounded-lg border">
              <svg
                viewBox="0 0 24 24"
                class="h-4.5 w-4.5"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path :d="c.icon" />
              </svg>
            </div>
            <p class="mt-4 font-mono text-xs uppercase tracking-wide text-paper/45">{{ c.label }}</p>
            <a
              v-if="c.href"
              :href="c.href"
              class="mt-1 block font-mono text-lg text-paper hover:text-flag"
            >
              {{ c.value }}
            </a>
            <p v-else class="mt-1 font-mono text-lg text-paper">{{ c.value }}</p>
          </div>
        </div>

      </div>
    </div>
  </section>
</template>