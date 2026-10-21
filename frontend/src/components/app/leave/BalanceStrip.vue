<script setup lang="ts">
import { type Balance, fmtDays } from "./leave";

defineProps<{ balances: Balance[]; loading: boolean; error: string; year: number }>();
defineEmits<{ retry: [] }>();

/** Share of the quota used (solid) and pending (hatched), as percentages. */
function bar(b: Balance) {
  if (!b.quota) return { used: 0, pending: 0 };
  const used = Math.min(100, (b.used / b.quota) * 100);
  return { used, pending: Math.min(100 - used, (b.pending / b.quota) * 100) };
}
</script>

<template>
  <section aria-labelledby="balance-heading">
    <h2 id="balance-heading" class="ledger-label mb-3">Balances · {{ year }}</h2>

    <div v-if="loading" class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" aria-busy="true" aria-label="Loading balances">
      <div v-for="i in 5" :key="i" class="h-[138px] rounded-xl border border-dashed border-ink/15 bg-sheet/60 motion-safe:animate-pulse" />
    </div>

    <div v-else-if="error" class="panel flex flex-wrap items-center justify-between gap-3 px-5 py-4" role="alert">
      <p class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ghost btn-sm" @click="$emit('retry')">Retry</button>
    </div>

    <p v-else-if="!balances.length" class="panel px-5 py-4 text-sm text-ink/55">No leave types are active yet.</p>

    <ul v-else class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      <li v-for="(b, i) in balances" :key="b.leave_type.id" class="panel rise flex flex-col p-4" :style="{ animationDelay: `${i * 40}ms` }">
        <p class="flex items-center gap-2 text-sm font-medium text-ink">
          <span class="h-2.5 w-2.5 shrink-0 rounded-full border border-ink/10" :style="{ background: b.leave_type.color || '#7a6a52' }" aria-hidden="true" />
          <span class="truncate">{{ b.leave_type.name }}</span>
        </p>

        <p class="mt-3 font-display text-[34px] leading-none font-medium text-ink">
          <template v-if="b.remaining !== null">{{ fmtDays(b.remaining) }}</template>
          <template v-else>∞</template>
          <span class="ml-1 font-body text-xs font-normal text-ink/45">
            {{ b.remaining !== null ? "days left" : "no fixed quota" }}
          </span>
        </p>

        <div
          v-if="b.quota"
          class="mt-3 flex h-1 overflow-hidden rounded-full bg-panel"
          role="img"
          :aria-label="`${fmtDays(b.used)} of ${fmtDays(b.quota)} days used, ${fmtDays(b.pending)} pending`"
        >
          <span class="h-full bg-river" :style="{ width: `${bar(b).used}%` }" />
          <span class="h-full bg-contour/60" :style="{ width: `${bar(b).pending}%` }" />
        </div>
        <div v-else class="mt-3 h-1 border-t border-dashed border-ink/20" aria-hidden="true" />

        <dl class="readout mt-3 grid grid-cols-3 gap-1 text-[11px] text-ink/55">
          <div><dt class="ledger-label text-[9.5px]">Quota</dt><dd>{{ b.quota ? fmtDays(b.quota) : "—" }}</dd></div>
          <div><dt class="ledger-label text-[9.5px]">Used</dt><dd>{{ fmtDays(b.used) }}</dd></div>
          <div><dt class="ledger-label text-[9.5px]">Pending</dt><dd>{{ fmtDays(b.pending) }}</dd></div>
        </dl>
        <p v-if="!b.leave_type.is_paid" class="ledger-label mt-2 text-[9.5px]">Unpaid</p>
      </li>
    </ul>
  </section>
</template>
