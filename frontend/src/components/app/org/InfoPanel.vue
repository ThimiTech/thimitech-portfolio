<script setup lang="ts">
import { RouterLink } from "vue-router";
import type { InfoRow } from "./org";

defineProps<{ title: string; refCode?: string; rows?: InfoRow[] }>();
</script>

<template>
  <section class="panel">
    <div class="panel-head">
      <h2 class="font-display text-base font-medium text-ink">{{ title }}</h2>
      <span v-if="refCode" class="readout text-[11px] text-ink/40">{{ refCode }}</span>
    </div>
    <div class="panel-body">
      <dl v-if="rows" class="grid gap-x-6 gap-y-3.5">
        <div v-for="r in rows" :key="r.label" class="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)] items-baseline gap-3">
          <dt class="ledger-label">{{ r.label }}</dt>
          <dd class="min-w-0 text-sm break-words text-ink" :class="r.mono ? 'readout' : ''">
            <template v-if="r.value">
              <RouterLink v-if="r.to" :to="r.to" class="underline decoration-ink/25 underline-offset-4 hover:decoration-flag">{{ r.value }}</RouterLink>
              <a v-else-if="r.href" :href="r.href" class="underline decoration-ink/25 underline-offset-4 hover:decoration-flag">{{ r.value }}</a>
              <template v-else>{{ r.value }}</template>
              <span v-if="r.note" class="readout ml-2 text-xs text-ink/45">{{ r.note }}</span>
            </template>
            <span v-else class="text-ink/35">Not recorded</span>
          </dd>
        </div>
      </dl>
      <slot />
    </div>
  </section>
</template>
