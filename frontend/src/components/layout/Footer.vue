<script setup lang="ts">
const sitemap = [
  { label: 'Home', href: '#home' },
  { label: 'About Us', href: '#about' },
  { label: 'Mission', href: '#mission' },
  { label: 'Services', href: '#services' },
  { label: 'Projects', href: '#projects' },
  { label: 'Team', href: '#team' },
  { label: 'Hiring', href: '#hiring' },
]

const social = [
  { label: 'LinkedIn', href: 'https://www.linkedin.com/company/thimitech' },
  { label: 'Instagram', href: 'https://www.instagram.com/thimitech/' },
  { label: 'Facebook', href: 'https://www.facebook.com/profile.php?id=61585729408478' },
]
</script>

<template>
  <footer class="border-t border-paper/10 bg-ink text-paper/70">
    <div class="px-8 py-14 lg:px-[6vw]">
      <div class="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div class="flex items-center gap-2 font-display text-lg font-semibold text-paper">
            <svg viewBox="0 0 32 32" fill="none" class="h-7 w-7 text-flag" xmlns="http://www.w3.org/2000/svg">
              <path fill-rule="evenodd" clip-rule="evenodd" d="M22 9.35967V6.58928L10 1.94141V4.66132L12.6723 5.62468L14.6384 6.33113L19.0418 7.93131V7.96592L14.6384 9.51481L12.6723 10.2204L10 11.1504V13.9554L22 9.35967Z" fill="currentColor" />
              <path fill-rule="evenodd" clip-rule="evenodd" d="M10 22.4633L22 18.1602V21.1595L13.5629 24.1209V24.1583L22 27.1563V30.1742L10 25.76L10 22.4633Z" fill="currentColor" />
            </svg>
            Thimi Tech
          </div>
          <p class="mt-4 max-w-xs text-sm">
            A Nepal-based software studio delivering intelligent digital solutions —
            geospatial systems, AI, modern web — for businesses, governments, and the
            communities they serve.
          </p>
        </div>

        <div>
          <p class="text-xs uppercase tracking-wide text-paper/40">Sitemap</p>
          <ul class="mt-3 space-y-2 text-sm">
            <li v-for="l in sitemap" :key="l.href"><a :href="l.href" class="hover:text-paper">{{ l.label }}</a></li>
          </ul>
        </div>

        <div>
          <p class="text-xs uppercase tracking-wide text-paper/40">Social</p>
          <ul class="mt-3 space-y-2 text-sm">
            <li v-for="s in social" :key="s.href">
              <a :href="s.href" target="_blank" rel="noopener" class="hover:text-paper">{{ s.label }} ↗</a>
            </li>
          </ul>
        </div>

        <div>
          <p class="text-xs uppercase tracking-wide text-paper/40">Contact</p>
          <ul class="mt-3 space-y-2 text-sm">
            <li><a href="mailto:info@thimitech.com" class="hover:text-paper">info@thimitech.com</a></li>
            <li>Kathmandu, NP</li>
          </ul>
        </div>
      </div>

      <div class="mt-12 flex flex-col gap-2 border-t border-paper/10 pt-6 text-xs text-paper/40 sm:flex-row sm:items-center sm:justify-between">
        <span>© 2025 Thimi Tech</span>
        <span class="font-display text-paper/60">Reality, into Vision.</span>
        <span>Built with care · Kathmandu, NP</span>
      </div>
    </div>
  </footer>
</template>