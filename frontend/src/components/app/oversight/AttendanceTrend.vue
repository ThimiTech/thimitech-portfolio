<script setup lang="ts">
import { computed } from 'vue'
import type { AttendanceDay } from './oversight'
const props = defineProps<{ days: AttendanceDay[] }>()
const series = [
  { key: 'present', name: 'Present', color: '#385e4b' },
  { key: 'late', name: 'Late', color: '#9c7129' },
  { key: 'absent', name: 'Absent', color: '#b04d38' },
  { key: 'on_leave', name: 'On leave', color: '#6b7280' },
  { key: 'not_checked_in', name: 'Not checked in', color: '#d7d4cc' },
] as const
const max = computed(() =>
  Math.max(1, ...props.days.map((d) => series.reduce((sum, s) => sum + d[s.key], 0))),
)
const bars = computed(() =>
  props.days.map((d) => {
    let top = 156
    return {
      date: d.date,
      segments: series.map((s) => {
        const height = (d[s.key] / max.value) * 132
        top -= height
        return { ...s, height, y: top }
      }),
    }
  }),
)
</script>
<template>
  <figure>
    <figcaption class="sr-only">
      Daily attendance counts. Exact values are available in the daily register below.
    </figcaption>
    <svg
      viewBox="0 0 760 185"
      role="img"
      aria-label="Stacked daily attendance chart"
      class="mt-5 w-full"
    >
      <g stroke="currentColor" class="text-ink/10"><path d="M16 24H744M16 90H744M16 156H744" /></g>
      <g v-for="(bar, i) in bars" :key="bar.date">
        <title>
          {{ bar.date }}: {{ days[i]?.present }} present, {{ days[i]?.late }} late,
          {{ days[i]?.absent }} absent, {{ days[i]?.on_leave }} on leave,
          {{ days[i]?.not_checked_in }} not checked in
        </title>
        <rect
          v-for="s in bar.segments"
          :key="s.key"
          :x="16 + (i * 728) / bars.length"
          :y="s.y"
          :width="Math.max(1, 728 / bars.length - 3)"
          :height="s.height"
          :fill="s.color"
        />
      </g>
      <g fill="currentColor" class="font-mono text-[11px] text-ink/65">
        <text x="16" y="179">{{ days[0]?.date }}</text>
        <text x="744" y="179" text-anchor="end">{{ days[days.length - 1]?.date }}</text>
      </g>
    </svg>
    <ul class="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink/70" aria-label="Chart legend">
      <li v-for="s in series" :key="s.key" class="flex items-center gap-2">
        <span class="h-2 w-2" :style="{ background: s.color }" aria-hidden="true" />{{ s.name }}
      </li>
    </ul>
  </figure>
  <details class="mt-5 border-t border-ink/10 pt-4">
    <summary class="cursor-pointer text-sm underline underline-offset-4">
      Daily register · {{ days.length }} days
    </summary>
    <div class="mt-4 overflow-x-auto">
      <table class="ledger-table">
        <caption class="sr-only">
          Daily attendance counts
        </caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>Day</th>
            <th v-for="s in series" :key="s.key">{{ s.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in days" :key="d.date">
            <th scope="row" class="whitespace-nowrap text-left font-normal">{{ d.date }}</th>
            <td>{{ d.kind }}</td>
            <td v-for="s in series" :key="s.key">{{ d[s.key] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
</template>
