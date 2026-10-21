<script setup lang="ts">
import { nextTick } from "vue";

// WAI-ARIA tabs: roving tabindex, ←/→/Home/End move and activate.
// Pair each panel with `role="tabpanel" :id="`${idPrefix}-panel-${id}`" :aria-labelledby="`${idPrefix}-tab-${id}`"`.
const props = defineProps<{ tabs: { id: string; label: string; count?: number }[]; label: string; idPrefix: string }>();
const model = defineModel<string>({ required: true });

async function onKey(e: KeyboardEvent, i: number) {
  const n = props.tabs.length;
  const next = ({ ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 } as Record<string, number>)[e.key];
  if (next === undefined) return;
  e.preventDefault();
  model.value = props.tabs[next]!.id;
  await nextTick();
  document.getElementById(`${props.idPrefix}-tab-${model.value}`)?.focus();
}
</script>

<template>
  <div role="tablist" :aria-label="label" class="flex gap-1 overflow-x-auto border-b border-ink/15">
    <button
      v-for="(t, i) in tabs"
      :id="`${idPrefix}-tab-${t.id}`"
      :key="t.id"
      type="button"
      role="tab"
      :aria-selected="model === t.id"
      :aria-controls="`${idPrefix}-panel-${t.id}`"
      :tabindex="model === t.id ? 0 : -1"
      class="-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
      :class="model === t.id ? 'border-flag font-medium text-ink' : 'border-transparent text-ink/55 hover:text-ink'"
      @click="model = t.id"
      @keydown="onKey($event, i)"
    >
      {{ t.label }}
      <span v-if="t.count" class="readout rounded-full bg-flag px-1.5 text-[10.5px] leading-[18px] text-on-accent">{{ t.count }}</span>
    </button>
  </div>
</template>
