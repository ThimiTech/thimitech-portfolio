<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import api from "@/api/api";
import { ICONS } from "../nav";

/** A palette entry: navigates (`to`) or runs (`run`). */
export interface Command {
  id: string;
  label: string;
  group: string;
  icon?: string;
  /** Second line: where the thing lives (a task's project, a person's title). */
  sub?: string;
  keywords?: string;
  to?: string;
  run?: () => void;
}

const props = defineProps<{ open: boolean; commands: Command[] }>();
const emit = defineEmits<{ close: []; select: [cmd: Command] }>();

const query = ref("");
const active = ref(0);
const input = ref<HTMLInputElement | null>(null);
const list = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;

// Things, not pages: people, projects, tasks, notes, documents and notices from /api/search/.
interface Hit { kind: keyof typeof KIND; label: string; sub: string; to: string }
const KIND = {
  person: { group: "Person", icon: ICONS.people },
  project: { group: "Project", icon: ICONS.projects },
  task: { group: "Task", icon: ICONS.audit },
  note: { group: "Note", icon: ICONS.audit },
  document: { group: "Document", icon: ICONS.drive },
  notice: { group: "Notice", icon: ICONS.notices },
} as const;
const found = ref<Command[]>([]);
const searching = ref(false);
let debounce: ReturnType<typeof setTimeout> | undefined;
let seq = 0;
watch(query, (q) => {
  clearTimeout(debounce);
  const id = ++seq;
  const text = q.trim();
  searching.value = text.length >= 2;
  if (!searching.value) return void (found.value = []);
  debounce = setTimeout(async () => {
    let hits: Hit[] = [];
    try {
      hits = (await api.get<Hit[]>("search/", { params: { q: text } }))?.data ?? [];
    } catch {
      /* pages and actions still work without it */
    }
    if (id !== seq) return; // a newer keystroke owns the list now
    found.value = hits.map((h, i) => ({ id: `hit-${i}-${h.to}`, label: h.label, sub: h.sub, group: KIND[h.kind].group, icon: KIND[h.kind].icon, to: h.to }));
    searching.value = false;
  }, 220);
});
onBeforeUnmount(() => clearTimeout(debounce));

const matches = computed(() => {
  const terms = query.value.toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return props.commands;
  return props.commands
    .map((c) => {
      const hay = `${c.label} ${c.group} ${c.keywords ?? ""}`.toLowerCase();
      if (!terms.every((t) => hay.includes(t))) return null;
      const label = c.label.toLowerCase();
      return { c, score: label.startsWith(terms[0]!) ? 0 : label.includes(terms[0]!) ? 1 : 2 };
    })
    .filter((x): x is { c: Command; score: number } => !!x)
    .sort((a, b) => a.score - b.score)
    .map((x) => x.c);
});
// a recent project is also a search hit: list it once
const results = computed(() => [...matches.value, ...found.value.filter((f) => !matches.value.some((m) => m.to === f.to))]);

watch(query, () => (active.value = 0));
watch(
  () => props.open,
  async (o) => {
    if (o) {
      previousFocus = document.activeElement as HTMLElement | null;
      query.value = "";
      active.value = 0;
      await nextTick();
      input.value?.focus();
    } else previousFocus?.focus?.();
  },
);

async function move(delta: number) {
  const n = results.value.length;
  if (!n) return;
  active.value = (active.value + delta + n) % n;
  await nextTick();
  list.value?.querySelector(`#cmd-opt-${active.value}`)?.scrollIntoView({ block: "nearest" });
}

function onKey(e: KeyboardEvent) {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    move(e.key === "ArrowDown" ? 1 : -1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    const c = results.value[active.value];
    if (c) emit("select", c);
  } else if (e.key === "Escape") emit("close");
  else if (e.key === "Tab") e.preventDefault(); // focus stays in the palette
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[10000] flex items-start justify-center bg-scrim/60 px-4 pt-[12vh] backdrop-blur-[2px]" @click.self="emit('close')">
      <div role="dialog" aria-modal="true" aria-label="Command palette" class="rise w-full max-w-xl overflow-hidden rounded-xl border border-ink/10 bg-sheet shadow-2xl">
        <div class="flex items-center gap-3 border-b border-dashed border-ink/15 px-4">
          <svg viewBox="0 0 24 24" class="h-4 w-4 shrink-0 text-ink/45" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input
            ref="input"
            v-model="query"
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls="cmd-list"
            aria-autocomplete="list"
            :aria-activedescendant="results.length ? `cmd-opt-${active}` : undefined"
            aria-label="Search the workspace"
            placeholder="Search people, projects, tasks, or jump to a page…"
            class="h-12 w-full bg-transparent text-[15px] text-ink outline-none! placeholder:text-ink/40"
            @keydown="onKey"
          />
          <kbd class="hidden rounded border border-ink/15 px-1.5 py-0.5 font-mono text-[10px] text-ink/45 sm:block">Esc</kbd>
        </div>
        <ul id="cmd-list" ref="list" role="listbox" aria-label="Results" class="max-h-[50vh] overflow-y-auto p-2">
          <li v-if="!results.length" class="px-3 py-8 text-center text-sm text-ink/55" role="presentation">{{ searching ? "Searching…" : `Nothing matches “${query}”.` }}</li>
          <li
            v-for="(c, i) in results"
            :id="`cmd-opt-${i}`"
            :key="c.id"
            role="option"
            :aria-selected="i === active"
            class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm"
            :class="i === active ? 'bg-panel text-ink' : 'text-ink/75'"
            @mousemove="active = i"
            @click="emit('select', c)"
          >
            <svg v-if="c.icon" viewBox="0 0 24 24" class="h-4 w-4 shrink-0" :class="i === active ? 'text-flag' : 'text-ink/45'" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="c.icon" /></svg>
            <span class="min-w-0 flex-1">
              <span class="block truncate">{{ c.label }}</span>
              <span v-if="c.sub" class="block truncate text-xs text-ink/50">{{ c.sub }}</span>
            </span>
            <span class="font-mono text-[10px] tracking-[0.12em] text-ink/40 uppercase">{{ c.group }}</span>
          </li>
        </ul>
        <p class="flex gap-4 border-t border-dashed border-ink/15 px-4 py-2 font-mono text-[10px] text-ink/45">
          <span>↑↓ move</span><span>↵ open</span><span>esc close</span>
        </p>
      </div>
    </div>
  </Teleport>
</template>
