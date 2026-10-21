<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { KIND, fmtDate, itemKey, weekdayOf, type FeedItem } from "./calendar";

const props = defineProps<{
  days: string[];
  /** 0-based month being viewed; days outside it are dimmed. */
  month: number;
  items: Map<string, FeedItem[]>;
  /** JS weekdays (Sun=0) that are weekends. */
  weekend: number[];
  today: string;
  selected: string | null;
}>();
const emit = defineEmits<{ select: [date: string] }>();

type HolidayItem = Extract<FeedItem, { kind: "holiday" }>;
const HEAD =["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MAX_CHIPS = 2;

const cells = computed(() =>
  props.days.map((date) => {
    const all = props.items.get(date) ?? [];
    const holidays = all.filter((i): i is HolidayItem => i.kind === "holiday");
    const others = all.filter((i) => i.kind !== "holiday");
    const wd = weekdayOf(date);
    const weekend = props.weekend.includes(wd);
    const label = [
      fmtDate(date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }),
      date === props.today ? "today" : "",
      weekend ? "weekend" : "",
      ...holidays.map((h) => `holiday: ${h.title}`),
      others.length ? `${others.length} item${others.length > 1 ? "s" : ""}` : "",
    ]
      .filter(Boolean)
      .join(", ");
    return {
      date,
      day: Number(date.slice(8)),
      inMonth: Number(date.slice(5, 7)) - 1 === props.month,
      weekend,
      holidays,
      others,
      label,
    };
  }),
);

// Roving focus: arrow keys move between days, Home/End to week edges.
const grid = ref<HTMLElement | null>(null);
const focusDate = computed(() =>
  props.selected && props.days.includes(props.selected)
    ? props.selected
    : props.days.includes(props.today)
      ? props.today
      : props.days.find((d) => Number(d.slice(5, 7)) - 1 === props.month),
);

async function onKey(e: KeyboardEvent, index: number) {
  const step: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, Home: -(index % 7), End: 6 - (index % 7) };
  const delta = step[e.key];
  if (delta === undefined) return;
  e.preventDefault();
  const next = props.days[Math.min(props.days.length - 1, Math.max(0, index + delta))];
  if (!next) return;
  emit("select", next);
  await nextTick();
  grid.value?.querySelector<HTMLElement>(`[data-date="${next}"]`)?.focus();
}
</script>

<template>
  <div>
    <div class="grid grid-cols-7 border-b border-ink/15" aria-hidden="true">
      <div
        v-for="(h, i) in HEAD"
        :key="h"
        class="ledger-label px-1 py-2 text-center sm:px-2 sm:text-left"
        :class="weekend.includes(i) ? 'text-rust/70' : ''"
      >
        <span class="sm:hidden">{{ h[0] }}</span><span class="hidden sm:inline">{{ h }}</span>
      </div>
    </div>

    <div ref="grid" class="grid grid-cols-7" role="group" aria-label="Month days">
      <button
        v-for="(c, i) in cells"
        :key="c.date"
        type="button"
        :data-date="c.date"
        :tabindex="c.date === focusDate ? 0 : -1"
        :aria-label="c.label"
        :aria-pressed="c.date === selected"
        class="group relative flex min-h-[64px] min-w-0 flex-col items-stretch gap-1 border-b border-r border-dashed border-ink/10 p-1 text-left transition-colors outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-river/50 sm:min-h-[112px] sm:p-1.5 [&:nth-child(7n)]:border-r-0"
        :class="[
          c.weekend ? 'bg-panel/55' : 'bg-transparent',
          c.date === selected ? '!bg-flag/[0.07]' : 'hover:bg-panel/40',
          c.inMonth ? '' : 'text-ink/35',
        ]"
        @click="emit('select', c.date)"
        @keydown="onKey($event, i)"
      >
        <span class="flex items-center justify-between gap-1">
          <span
            class="readout inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-[12px]"
            :class="[
              c.date === today ? 'font-semibold text-flag ring-2 ring-flag ring-offset-1 ring-offset-sheet' : '',
              c.holidays.some((h) => !h.meta.is_optional) && c.date !== today ? 'text-rust' : '',
            ]"
          >
            {{ c.day }}
          </span>
          <span v-if="c.date === today" class="hidden font-mono text-[9px] tracking-[0.12em] text-flag uppercase lg:inline">
            Today
          </span>
        </span>

        <!-- Holidays: full-width stripes -->
        <span
          v-for="h in c.holidays"
          :key="itemKey(h)"
          class="-mx-1 block truncate border-l-2 px-1.5 py-0.5 text-[10.5px] leading-tight text-rust sm:-mx-1.5"
          :class="h.meta.is_optional ? 'border-dashed border-rust/60 bg-rust/[0.05]' : 'border-rust bg-rust/10'"
          :title="h.title"
        >
          <span class="font-mono text-[9px] tracking-wider">{{ h.meta.is_optional ? "OPT" : "HOL" }}</span>
          <span class="hidden sm:inline"> {{ h.title }}</span>
        </span>

        <!-- Other items: chips on ≥sm, dots on phones -->
        <span class="hidden flex-col gap-0.5 sm:flex">
          <span
            v-for="it in c.others.slice(0, MAX_CHIPS)"
            :key="itemKey(it)"
            class="block truncate rounded border px-1 py-px text-[10.5px] leading-tight"
            :class="KIND[it.kind].chip"
            :title="it.title"
          >
            <span class="font-mono text-[9px] tracking-wider opacity-80">{{ KIND[it.kind].prefix }}</span>
            {{ it.title }}
          </span>
          <span v-if="c.others.length > MAX_CHIPS" class="font-mono text-[10px] text-ink/50">
            +{{ c.others.length - MAX_CHIPS }} more
          </span>
        </span>
        <span v-if="c.others.length" class="mt-auto flex flex-wrap gap-0.5 sm:hidden" aria-hidden="true">
          <span v-for="it in c.others.slice(0, 4)" :key="itemKey(it)" class="h-1.5 w-1.5 rounded-full" :class="KIND[it.kind].dot" />
        </span>
      </button>
    </div>
  </div>
</template>
