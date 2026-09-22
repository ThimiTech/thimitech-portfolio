<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'

const { revealRoot } = useReveal<HTMLElement>()
</script>

<template>
  <section id="cta" ref="revealRoot" aria-labelledby="cta-heading" class="py-24 lg:py-32">
    <div
      data-reveal
      class="relative overflow-hidden rounded-3xl bg-ink px-8 py-14 text-paper md:px-12 lg:px-16 lg:py-20"
    >
      <div class="grid items-end gap-10 lg:grid-cols-12">
        <div class="lg:col-span-8">
          <p
            data-reveal
            class="font-mono text-xs uppercase tracking-[0.32em] text-paper/60"
          >
            Start a project
          </p>
          <h2
            id="cta-heading"
            data-reveal
            data-reveal-delay="90"
            class="mt-6 text-balance font-display text-5xl font-semibold leading-[0.95] tracking-tight md:text-6xl lg:text-7xl"
          >
            Have an idea?
            <span class="font-serif font-light italic text-paper/90">Let's map it.</span>
          </h2>
          <p
            data-reveal
            data-reveal-delay="160"
            class="mt-6 max-w-md text-base leading-relaxed text-paper/70"
          >
            Tell us what your team needs to see and decide — we reply within two working days.
          </p>
        </div>

        <div
          data-reveal
          data-reveal-delay="220"
          class="flex flex-col gap-4 sm:flex-row sm:items-center lg:col-span-4 lg:justify-end"
        >
          <a
            href="#contact"
            class="group inline-flex items-center justify-center gap-2 rounded-full bg-flag px-7 py-3.5 text-base font-medium text-paper transition-colors duration-200 ease-in-out hover:bg-paper hover:text-ink motion-reduce:transition-none"
          >
            Start a project
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4 transition-transform duration-200 ease-in-out group-hover:translate-x-1 motion-reduce:transform-none motion-reduce:transition-none"
              aria-hidden="true"
            >
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
          <a
            href="#projects"
            class="inline-flex items-center justify-center rounded-full border border-paper/25 px-7 py-3.5 text-base font-medium text-paper transition-colors duration-200 ease-in-out hover:border-paper hover:bg-paper/10 motion-reduce:transition-none"
          >
            See our work
          </a>
        </div>
      </div>
    </div>
  </section>
</template>
