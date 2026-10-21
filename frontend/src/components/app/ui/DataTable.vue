<script setup lang="ts" generic="T">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import EmptyState from "./EmptyState.vue";

/**
 * Table with search, sortable headers (aria-sort) and pagination.
 * Client mode (default): filters/sorts/pages `rows` itself.
 * Server mode (pass `total`): `rows` is the current page; bind v-model:page / v-model:search /
 * v-model:ordering ("field" or "-field", using each column's `orderBy`) and fetch on change
 * (see useServerTable in serverTable.ts). Search is debounced in server mode.
 * Cells render `row[key]` unless a `#cell-<key>="{ row }"` slot is given.
 */
export interface Column<R> {
  key: string;
  label: string;
  sortable?: boolean;
  /** Value used for client-side sorting; defaults to row[key]. */
  sortValue?: (row: R) => string | number | null | undefined;
  /** Server mode: the API ordering field for this column (defaults to key). */
  orderBy?: string;
  class?: string;
  /** Visually hide the header text (still read by screen readers). */
  srOnly?: boolean;
}

const props = withDefaults(
  defineProps<{
    rows: T[];
    columns: Column<T>[];
    rowKey: (row: T) => string | number;
    caption: string;
    /** Client mode: text searched by the search box; omit to hide the box. */
    searchText?: (row: T) => string;
    searchPlaceholder?: string;
    pageSize?: number;
    emptyTitle?: string;
    emptyHint?: string;
    /** Server mode: total matching rows across all pages. */
    total?: number;
    loading?: boolean;
  }>(),
  {
    searchText: undefined,
    searchPlaceholder: "Search…",
    pageSize: 10,
    emptyTitle: "Nothing here yet",
    emptyHint: "",
    total: undefined,
    loading: false,
  },
);

const page = defineModel<number>("page", { default: 1 });
const query = defineModel<string>("search", { default: "" });
const ordering = defineModel<string>("ordering", { default: "" });

const server = computed(() => props.total !== undefined);
const field = (c: Column<T>) => c.orderBy ?? c.key;
const sortKey = computed(() => ordering.value.replace(/^-/, "") || null);
const sortDir = computed<"asc" | "desc">(() => (ordering.value.startsWith("-") ? "desc" : "asc"));

// What the user typed: pushed to `query` at once (client mode) or after a pause (server mode).
const typed = ref(query.value);
let debounce: ReturnType<typeof setTimeout> | undefined;
watch(typed, (v) => {
  clearTimeout(debounce);
  if (!server.value) query.value = v;
  else debounce = setTimeout(() => (query.value = v), 300);
});
watch(query, (v) => {
  typed.value = v;
  page.value = 1;
});
onBeforeUnmount(() => clearTimeout(debounce));
function clearSearch() {
  clearTimeout(debounce);
  typed.value = query.value = "";
}

const cell = (row: T, key: string) => (row as Record<string, unknown>)[key];

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (server.value || !q || !props.searchText) return props.rows;
  return props.rows.filter((r) => props.searchText!(r).toLowerCase().includes(q));
});

const sorted = computed(() => {
  const col = props.columns.find((c) => field(c) === sortKey.value);
  if (server.value || !col) return filtered.value;
  const get = col.sortValue ?? ((r: T) => cell(r, col.key) as string | number | null);
  const dir = sortDir.value === "asc" ? 1 : -1;
  return [...filtered.value].sort((a, b) => {
    const x = get(a);
    const y = get(b);
    if (x == null || x === "") return 1; // blanks always last
    if (y == null || y === "") return -1;
    return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true })) * dir;
  });
});

const count = computed(() => (server.value ? props.total! : sorted.value.length));
const pages = computed(() => Math.max(1, Math.ceil(count.value / props.pageSize)));
const visible = computed(() =>
  server.value ? props.rows : sorted.value.slice((page.value - 1) * props.pageSize, page.value * props.pageSize),
);
watch(
  () => props.rows,
  () => {
    if (!server.value) page.value = 1;
  },
);
watch(pages, (n) => {
  if (page.value > n) page.value = n;
});

function toggleSort(c: Column<T>) {
  const f = field(c);
  ordering.value = sortKey.value === f && sortDir.value === "asc" ? `-${f}` : f;
  page.value = 1;
}
const ariaSort = (c: Column<T>) =>
  sortKey.value === field(c) ? (sortDir.value === "asc" ? "ascending" : "descending") : undefined;
const from = computed(() => (count.value ? (page.value - 1) * props.pageSize + 1 : 0));
const to = computed(() => Math.min(page.value * props.pageSize, count.value));
const showSearch = computed(() => !!props.searchText || server.value);
</script>

<template>
  <div>
    <div v-if="showSearch || $slots.toolbar" class="mb-4 flex flex-wrap items-center gap-3">
      <label v-if="showSearch" class="relative min-w-0 flex-1 sm:max-w-xs">
        <span class="sr-only">Search {{ caption }}</span>
        <svg viewBox="0 0 24 24" class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink/40" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input v-model="typed" type="search" class="input pl-9" :placeholder="searchPlaceholder" />
      </label>
      <slot name="toolbar" />
    </div>

    <div v-if="!visible.length" class="panel" :aria-busy="loading">
      <slot name="empty">
        <EmptyState :title="query ? 'No matches' : emptyTitle" :hint="query ? `Nothing matches “${query}”.` : emptyHint">
          <button v-if="query" type="button" class="btn-ghost btn-sm" @click="clearSearch">Clear search</button>
        </EmptyState>
      </slot>
    </div>

    <div v-else class="panel overflow-x-auto transition-opacity" :class="loading ? 'opacity-60' : ''" :aria-busy="loading">
      <table class="ledger-table">
        <caption class="sr-only">{{ caption }}</caption>
        <thead>
          <tr>
            <th v-for="c in columns" :key="c.key" scope="col" :class="c.class" :aria-sort="c.sortable ? (ariaSort(c) ?? 'none') : undefined">
              <button
                v-if="c.sortable"
                type="button"
                class="ledger-label inline-flex items-center gap-1 rounded hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
                @click="toggleSort(c)"
              >
                {{ c.label }}
                <svg viewBox="0 0 24 24" class="h-3 w-3" :class="sortKey === field(c) ? 'text-flag' : 'text-ink/30'" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
                  <path v-if="sortKey !== field(c)" d="m8 9 4-4 4 4M8 15l4 4 4-4" />
                  <path v-else-if="sortDir === 'asc'" d="m8 14 4-4 4 4" />
                  <path v-else d="m8 10 4 4 4-4" />
                </svg>
              </button>
              <span v-else :class="c.srOnly ? 'sr-only' : ''">{{ c.label }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in visible" :key="rowKey(row)">
            <td v-for="c in columns" :key="c.key" :class="c.class">
              <slot :name="`cell-${c.key}`" :row="row">{{ cell(row, c.key) ?? "—" }}</slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <nav v-if="pages > 1" class="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm" :aria-label="`${caption} pages`">
      <p class="readout text-xs text-ink/55">{{ from }}–{{ to }} of {{ count }}</p>
      <div class="flex items-center gap-2">
        <button type="button" class="btn-ghost btn-sm" :disabled="page === 1 || loading" @click="page--">← Prev</button>
        <span class="readout text-xs text-ink/60" aria-live="polite">Page {{ page }} / {{ pages }}</span>
        <button type="button" class="btn-ghost btn-sm" :disabled="page === pages || loading" @click="page++">Next →</button>
      </div>
    </nav>
  </div>
</template>
