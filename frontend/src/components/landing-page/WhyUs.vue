<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'

// Why Choose Us — minimalist editorial. Static HTML + Tailwind only.
// Entrance motion: staggered scroll-reveal via [data-reveal]; hovers stay
// on Tailwind transitions so they remain snappy after the reveal.
const { revealRoot } = useReveal<HTMLElement>()
</script>

<template>
  <section
    id="why-us"
    ref="revealRoot"
    aria-labelledby="why-us-heading"
    class="relative ml-[calc(50%-50vw)] mr-[calc(50%-50vw)] flex min-h-[100vh] w-[100vw] max-w-[100vw] flex-col justify-center overflow-x-clip bg-paper py-24 text-ink lg:py-32"
  >
    <div class="w-full max-w-none px-8 lg:px-[6vw]">
      <!-- Header — two columns: heading left, intro right -->
      <div class="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:gap-6">
        <div class="text-left">
          <p data-reveal class="font-mono text-xs uppercase tracking-[0.32em] text-ink/60">
            Why Choose
          </p>
          <h2
            id="why-us-heading"
            data-reveal
            data-reveal-delay="90"
            class="mt-6 text-balance text-6xl leading-[0.9] tracking-tight md:text-8xl lg:text-[7rem]"
          >
            <span class="block font-display font-semibold">Thimi Tech</span>
          </h2>
        </div>
        <div
          data-reveal
          data-reveal-delay="180"
          class="flex flex-col items-end justify-end text-right lg:pb-3"
        >
          <p class="max-w-sm text-base leading-relaxed text-ink/70">
            We combine intelligent technology, thoughtful design, and deep technical expertise to
            turn complex challenges into meaningful digital solutions.
          </p>
        </div>
      </div>

      <!-- Divider -->
      <div
        data-reveal="line"
        aria-hidden="true"
        class="mt-12 border-t border-ink/10 md:mt-16"
      ></div>

      <!-- Asymmetric grid: 12-col desktop / 2-col tablet / 1-col mobile -->
      <div class="mt-10 grid grid-cols-1 gap-4 md:mt-12 md:grid-cols-2 lg:grid-cols-12">
        <!-- 01 — large dark card -->
        <article
          data-reveal
          class="group flex min-h-[20rem] flex-col justify-between rounded-3xl border border-ink bg-ink p-8 text-paper transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-2 lg:col-span-7 lg:p-10"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-paper/60">01</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-paper/20 text-paper/80 transition-colors duration-200 ease-in-out group-hover:border-paper/60 group-hover:text-paper motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547Z" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-3xl font-medium tracking-tight lg:text-4xl">Smart Thinking</h3>
            <p class="mt-3 max-w-md text-base leading-relaxed text-paper/70">
              Turning complex challenges into clear, intelligent solutions.
            </p>
          </div>
        </article>

        <!-- 02 — tall accent card -->
        <article
          data-reveal
          data-reveal-delay="80"
          class="group flex min-h-[20rem] flex-col justify-between rounded-3xl border border-flag bg-flag p-8 text-paper transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-1 lg:col-span-5 lg:row-span-2 lg:p-10"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-paper/80">02</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-paper/40 text-paper transition-colors duration-200 ease-in-out group-hover:bg-paper group-hover:text-flag motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25Zm.75-12h9v9h-9v-9Z" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-3xl font-medium leading-[1.02] tracking-tight lg:text-4xl">
              Modern Technology
            </h3>
            <p class="mt-4 max-w-xs text-base leading-relaxed text-paper/85">
              AI, geospatial systems, data, and modern web technologies built for real-world needs.
            </p>
          </div>
        </article>

        <!-- 03 -->
        <article
          data-reveal
          data-reveal-delay="140"
          class="group flex min-h-[14rem] flex-col justify-between rounded-3xl border border-ink/10 bg-white p-8 transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-1 lg:col-span-3"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-ink/50">03</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-ink/15 text-ink/70 transition-colors duration-200 ease-in-out group-hover:border-ink group-hover:bg-ink group-hover:text-paper motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-2xl font-medium tracking-tight">Built to Scale</h3>
            <p class="mt-3 text-base leading-relaxed text-ink/70">
              Flexible and maintainable systems designed to evolve with your organization.
            </p>
          </div>
        </article>

        <!-- 04 -->
        <article
          data-reveal
          data-reveal-delay="200"
          class="group flex min-h-[14rem] flex-col justify-between rounded-3xl border border-ink/10 bg-white p-8 transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-1 lg:col-span-4"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-ink/50">04</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-ink/15 text-ink/70 transition-colors duration-200 ease-in-out group-hover:border-ink group-hover:bg-ink group-hover:text-paper motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <circle cx="12" cy="12" r="5" />
                <circle cx="12" cy="12" r="1.25" fill="currentColor" stroke="none" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-2xl font-medium tracking-tight">Real Impact</h3>
            <p class="mt-3 text-base leading-relaxed text-ink/70">
              Technology focused on measurable outcomes and meaningful results.
            </p>
          </div>
        </article>

        <!-- 05 -->
        <article
          data-reveal
          data-reveal-delay="260"
          class="group flex min-h-[15rem] flex-col justify-between rounded-3xl border border-ink/10 bg-white p-8 transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-1 lg:col-span-5 lg:p-10"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-ink/50">05</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-ink/15 text-ink/70 transition-colors duration-200 ease-in-out group-hover:border-ink group-hover:bg-ink group-hover:text-paper motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-2xl font-medium tracking-tight">Human + Technology</h3>
            <p class="mt-3 max-w-sm text-base leading-relaxed text-ink/70">
              Combining thoughtful design with powerful engineering.
            </p>
          </div>
        </article>

        <!-- 06 — wide bottom dark card -->
        <article
          data-reveal
          data-reveal-delay="320"
          class="group flex min-h-[15rem] flex-col justify-between rounded-3xl border border-ink bg-ink p-8 text-paper transition-transform duration-200 ease-in-out hover:-translate-y-1 motion-reduce:transform-none motion-reduce:transition-none md:col-span-2 lg:col-span-7 lg:p-10"
        >
          <div class="flex items-start justify-between gap-4">
            <p class="font-mono text-xs tracking-[0.24em] text-paper/60">06</p>
            <span
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-paper/20 text-paper/80 transition-colors duration-200 ease-in-out group-hover:border-paper/60 group-hover:text-paper motion-reduce:transition-none"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
              </svg>
            </span>
          </div>
          <div>
            <h3 class="font-display text-3xl font-medium tracking-tight lg:text-4xl">Future Ready</h3>
            <p class="mt-3 max-w-md text-base leading-relaxed text-paper/70">
              Building digital systems prepared for what comes next.
            </p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
