<script setup lang="ts">
import { computed } from "vue";
import ItemRow from "./ItemRow.vue";
import EmptyState from "../ui/EmptyState.vue";
import { addDays, fmtDate, itemKey, weekdayOf, type FeedItem } from "./calendar";

const props = defineProps<{ from: string; days: number; items: Map<string, FeedItem[]>; weekend: number[]; today: string }>();
const emit = defineEmits<{ edit: [item: FeedItem]; delete: [item: FeedItem] }>();

const groups = computed(() => {
  const out: { date: string; items: FeedItem[] }[] = [];
  for (let i = 0; i < props.days; i++) {
    const date = addDays(props.from, i);
    const items = props.items.get(date);
    if (items?.length) out.push({ date, items });
  }
  return out;
});
</script>

<template>
  <EmptyState v-if="!groups.length" title="A clear horizon" hint="Nothing scheduled in the next 30 days." />
  <ol v-else class="divide-y divide-dashed divide-ink/15">
    <li v-for="g in groups" :key="g.date" class="grid grid-cols-[64px_minmax(0,1fr)] gap-3 px-4 py-2 sm:grid-cols-[96px_minmax(0,1fr)] sm:px-5">
      <div class="pt-3">
        <p class="font-display text-[28px] leading-none" :class="g.date === today ? 'text-flag' : 'text-ink'">
          {{ Number(g.date.slice(8)) }}
        </p>
        <p class="ledger-label mt-1" :class="weekend.includes(weekdayOf(g.date)) ? '!text-rust/70' : ''">
          {{ fmtDate(g.date, { weekday: "short", month: "short" }) }}
        </p>
        <p v-if="g.date === today" class="mt-1 font-mono text-[9.5px] tracking-[0.12em] text-flag uppercase">Today</p>
      </div>
      <div class="divide-y divide-dashed divide-ink/10">
        <ItemRow v-for="it in g.items" :key="itemKey(it)" :item="it" @edit="emit('edit', $event)" @delete="emit('delete', $event)" />
      </div>
    </li>
  </ol>
</template>
