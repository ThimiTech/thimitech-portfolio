<script setup lang="ts">
import type { ProjectHealth } from './oversight'
import { label } from './oversight'
defineProps<{ projects: ProjectHealth[] }>()
</script>
<template>
  <p v-if="!projects.length" class="py-8 text-sm text-ink/65">
    No active projects. Delivery health will appear when projects are created.
  </p>
  <div v-else class="overflow-x-auto">
    <table class="ledger-table">
      <caption class="sr-only">
        Active project health
      </caption>
      <thead>
        <tr>
          <th>Project</th>
          <th>Health</th>
          <th>Completion</th>
          <th>Overdue tasks</th>
          <th>Due date</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in projects" :key="p.id">
          <td>
            <RouterLink
              :to="`/app/projects/${p.id}`"
              class="font-medium underline decoration-ink/25 underline-offset-4 hover:decoration-flag"
              >{{ p.name }}</RouterLink
            ><span class="mt-1 block font-mono text-[10px] text-ink/60">{{ p.key }}</span>
          </td>
          <td>
            <span
              class="whitespace-nowrap border px-2 py-1 font-mono text-[10px] uppercase"
              :class="
                p.health === 'at_risk'
                  ? 'border-rust/25 bg-rust/5 text-rust'
                  : 'border-ink/15 text-ink/70'
              "
              >{{ label(p.health) }}</span
            >
          </td>
          <td class="min-w-36">
            <div class="h-1 bg-ink/10" aria-hidden="true">
              <div class="h-full bg-ink/70" :style="{ width: `${p.percent}%` }" />
            </div>
            <p class="mt-2 text-xs text-ink/65">
              {{ p.done }}/{{ p.total }} tasks · {{ p.percent }}%
            </p>
          </td>
          <td>{{ p.overdue }}</td>
          <td class="whitespace-nowrap">{{ p.due_date || 'Unscheduled' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
