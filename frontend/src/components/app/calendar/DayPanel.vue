<script setup lang="ts">
import { computed } from "vue";
import ItemRow from "./ItemRow.vue";
import StatusPill from "../ui/StatusPill.vue";
import { fmtDate, itemKey, type FeedItem } from "./calendar";

const props = defineProps<{ date: string; items: FeedItem[]; weekend: boolean; today: string; canCreate: boolean }>();
const emit = defineEmits<{ create: [date: string]; edit: [item: FeedItem]; delete: [item: FeedItem] }>();

const holiday = computed(() => props.items.find((i) => i.kind === "holiday" && !i.meta.is_optional));
</script>

<template>
  <section :aria-label="`Items on ${fmtDate(date, { day: 'numeric', month: 'long', year: 'numeric' })}`">
    <p class="ledger-label">{{ fmtDate(date, { weekday: "long" }) }}</p>
    <div class="mt-1 flex items-baseline gap-2">
      <h2 class="font-display text-[26px] leading-none font-medium">{{ fmtDate(date, { day: "numeric", month: "long" }) }}</h2>
      <span class="readout text-[11px] text-ink/45">{{ date }}</span>
    </div>
    <div class="mt-2 flex flex-wrap gap-1.5">
      <StatusPill v-if="date === today" status="info" label="Today" />
      <StatusPill v-if="holiday" status="absent" label="Public holiday" />
      <StatusPill v-if="weekend" status="neutral" label="Weekend" />
    </div>

    <div class="mt-3 border-t border-dashed border-ink/15">
      <div v-if="items.length" class="divide-y divide-dashed divide-ink/10">
        <ItemRow v-for="it in items" :key="itemKey(it)" :item="it" @edit="emit('edit', $event)" @delete="emit('delete', $event)" />
      </div>
      <p v-else class="py-6 text-center text-sm text-ink/50">Nothing logged for this day.</p>
    </div>

    <button v-if="canCreate" type="button" class="btn-ghost btn-sm mt-3 w-full" @click="emit('create', date)">
      <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
      Add event on this day
    </button>
  </section>
</template>
