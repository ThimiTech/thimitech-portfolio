<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import Modal from "../../components/app/ui/Modal.vue";
import MonthGrid from "../../components/app/calendar/MonthGrid.vue";
import AgendaList from "../../components/app/calendar/AgendaList.vue";
import DayPanel from "../../components/app/calendar/DayPanel.vue";
import EventModal from "../../components/app/calendar/EventModal.vue";
import HolidaysPanel from "../../components/app/calendar/HolidaysPanel.vue";
import {
  KIND, addDays, byDay, fmtDate, monthGrid, parseError, pyToJsWeekday, todayNPT, weekdayOf,
  type Feed, type FeedItem, type FeedKind,
} from "../../components/app/calendar/calendar";

const { hasRole } = useAuth();
const isHR = computed(() => hasRole("hr_admin"));
const canCreate = computed(() => hasRole("employee"));

type View = "month" | "agenda" | "holidays";
const AGENDA_DAYS = 30;

// ── Viewport: agenda by default on phones; side panel vs bottom sheet ──
const mqDesktop = window.matchMedia("(min-width: 1024px)");
const isDesktop = ref(mqDesktop.matches);
const onMq = (e: MediaQueryListEvent) => (isDesktop.value = e.matches);
onMounted(() => mqDesktop.addEventListener("change", onMq));
onBeforeUnmount(() => mqDesktop.removeEventListener("change", onMq));

const view = ref<View>(window.matchMedia("(max-width: 639px)").matches ? "agenda" : "month");
const today = ref(todayNPT());
const cursor = ref({ year: Number(today.value.slice(0, 4)), month: Number(today.value.slice(5, 7)) - 1 });
const selected = ref<string | null>(today.value);
const sheetOpen = ref(false);

const gridDays = computed(() => monthGrid(cursor.value.year, cursor.value.month));
const range = computed(() =>
  view.value === "agenda"
    ? { start: today.value, end: addDays(today.value, AGENDA_DAYS - 1) }
    : { start: gridDays.value[0]!, end: gridDays.value[gridDays.value.length - 1]! },
);
const monthTitle = computed(() =>
  fmtDate(`${cursor.value.year}-${String(cursor.value.month + 1).padStart(2, "0")}-01`, { month: "long", year: "numeric" }),
);

// ── Feed ──
const items = ref<FeedItem[]>([]);
const weekend = ref<number[]>([pyToJsWeekday(5)]);
const loading = ref(true);
const error = ref("");
let seq = 0;

async function load() {
  if (view.value === "holidays") return;
  const mine = ++seq;
  const { start, end } = range.value;
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.get<Feed>("calendar/feed/", { params: { start, end } });
    if (mine !== seq) return;
    items.value = data.items;
    weekend.value = data.weekend_days.map(pyToJsWeekday);
  } catch (e) {
    if (mine === seq) error.value = parseError(e).detail;
  } finally {
    if (mine === seq) loading.value = false;
  }
}
watch(() => [view.value, range.value.start, range.value.end], load, { immediate: true });

const days = computed(() => byDay(items.value, range.value.start, range.value.end));
const selectedItems = computed(() => (selected.value ? days.value.get(selected.value) ?? [] : []));

// ── Navigation ──
function shift(n: number) {
  const m = cursor.value.month + n;
  const year = cursor.value.year + Math.floor(m / 12);
  const month = ((m % 12) + 12) % 12;
  cursor.value = { year, month };
  // Keep the day panel inside the new month: same day-of-month, clamped to its length.
  const day = Math.min(Number(selected.value?.slice(8, 10) ?? 1), new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
  selected.value = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}
function goToday() {
  today.value = todayNPT();
  cursor.value = { year: Number(today.value.slice(0, 4)), month: Number(today.value.slice(5, 7)) - 1 };
  selected.value = today.value;
}
function onSelect(date: string) {
  selected.value = date;
  const m = Number(date.slice(5, 7)) - 1;
  if (m !== cursor.value.month) cursor.value = { year: Number(date.slice(0, 4)), month: m };
  if (!isDesktop.value) sheetOpen.value = true;
}

// ── Event create / edit / delete ──
const editor = ref({ open: false, id: null as number | null, date: today.value });
function openCreate(date?: string) {
  sheetOpen.value = false;
  editor.value = { open: true, id: null, date: date ?? selected.value ?? today.value };
}
function openEdit(item: FeedItem) {
  sheetOpen.value = false;
  editor.value = { open: true, id: item.id, date: today.value };
}
function onSaved() {
  editor.value.open = false;
  load();
}

const pendingDelete = ref<FeedItem | null>(null);
const deleting = ref(false);
const deleteError = ref("");
function askDelete(item: FeedItem) {
  sheetOpen.value = false;
  deleteError.value = "";
  pendingDelete.value = item;
}
async function confirmDelete() {
  const item = pendingDelete.value;
  if (!item) return;
  deleting.value = true;
  const before = items.value;
  items.value = items.value.filter((i) => !(i.kind === "event" && i.id === item.id)); // optimistic
  try {
    await api.delete(`calendar/events/${item.id}/`);
    pendingDelete.value = null;
  } catch (e) {
    items.value = before;
    deleteError.value = parseError(e).detail;
  } finally {
    deleting.value = false;
  }
}

const VIEWS = computed(() => [
  { id: "month" as const, label: "Month" },
  { id: "agenda" as const, label: "Agenda" },
  ...(isHR.value ? [{ id: "holidays" as const, label: "Holidays" }] : []),
]);
const LEGEND = Object.entries(KIND) as [FeedKind, (typeof KIND)[FeedKind]][];
</script>

<template>
  <div class="rise">
    <PageHeader eyebrow="A4 · Calendar" title="Calendar" description="Holidays, team events, approved leave and milestones — in Nepal time.">
      <template #actions>
        <button v-if="canCreate && view !== 'holidays'" type="button" class="btn-primary" @click="openCreate()">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          New event
        </button>
      </template>
    </PageHeader>

    <!-- Toolbar -->
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div role="group" aria-label="Calendar view" class="inline-flex rounded-full border border-ink/15 bg-sheet p-0.5">
        <button
          v-for="v in VIEWS"
          :key="v.id"
          type="button"

          :aria-pressed="view === v.id"
          class="rounded-full px-3.5 py-1.5 font-mono text-[11px] tracking-[0.1em] uppercase transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          :class="view === v.id ? 'bg-ink text-paper' : 'text-ink/60 hover:text-ink'"
          @click="view = v.id"
        >
          {{ v.label }}
        </button>
      </div>

      <div v-if="view === 'month'" class="flex items-center gap-2">
        <button type="button" class="btn-ghost btn-sm !px-2.5" aria-label="Previous month" @click="shift(-1)">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <h2 class="min-w-[9.5rem] text-center font-display text-xl font-medium" aria-live="polite">{{ monthTitle }}</h2>
        <button type="button" class="btn-ghost btn-sm !px-2.5" aria-label="Next month" @click="shift(1)">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
        </button>
        <button type="button" class="btn-ghost btn-sm" @click="goToday">Today</button>
      </div>
      <p v-else-if="view === 'agenda'" class="readout text-[11px] text-ink/50">
        {{ range.start }} → {{ range.end }} · next {{ AGENDA_DAYS }} days
      </p>
    </div>

    <HolidaysPanel v-if="view === 'holidays'" @changed="load" />

    <template v-else>
      <div v-if="error" class="panel panel-body flex flex-wrap items-center justify-between gap-3" role="alert">
        <p class="text-sm text-rust">Couldn't load the calendar: {{ error }}</p>
        <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
      </div>

      <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]" :class="view === 'agenda' ? 'lg:!grid-cols-1' : ''">
        <section class="panel min-w-0 overflow-hidden" :aria-busy="loading">
          <!-- Month -->
          <template v-if="view === 'month'">
            <div v-if="loading && !items.length" aria-label="Loading month" class="grid grid-cols-7">
              <div v-for="n in 35" :key="n" class="h-16 animate-pulse border-b border-r border-dashed border-ink/10 bg-panel/30 sm:h-28" />
            </div>
            <MonthGrid
              v-else
              :class="loading ? 'opacity-60 transition-opacity' : ''"
              :days="gridDays"
              :month="cursor.month"
              :items="days"
              :weekend="weekend"
              :today="today"
              :selected="selected"
              @select="onSelect"
            />
            <!-- Legend: colour plus text prefix -->
            <ul class="flex flex-wrap gap-x-4 gap-y-2 border-t border-dashed border-ink/15 px-4 py-3" aria-label="Legend">
              <li v-for="[kind, k] in LEGEND" :key="kind" class="flex items-center gap-1.5 text-xs text-ink/60">
                <span class="rounded border px-1 font-mono text-[9px] tracking-wider" :class="k.chip">{{ k.prefix }}</span>{{ k.label }}
              </li>
              <li class="flex items-center gap-1.5 text-xs text-ink/60"><span class="h-3 w-4 rounded-sm border border-ink/10 bg-panel/70" aria-hidden="true" />Weekend</li>
              <li class="flex items-center gap-1.5 text-xs text-ink/60"><span class="h-3.5 w-3.5 rounded-full ring-2 ring-flag" aria-hidden="true" />Today</li>
            </ul>
          </template>

          <!-- Agenda -->
          <template v-else>
            <div v-if="loading" class="space-y-3 p-5" aria-label="Loading agenda">
              <div v-for="n in 5" :key="n" class="h-16 animate-pulse rounded-lg border border-dashed border-ink/10 bg-panel/30" />
            </div>
            <AgendaList v-else :from="range.start" :days="AGENDA_DAYS" :items="days" :weekend="weekend" :today="today" @edit="openEdit" @delete="askDelete" />
          </template>
        </section>

        <!-- Desktop day panel -->
        <aside v-if="view === 'month' && isDesktop" class="panel panel-body h-fit lg:sticky lg:top-20">
          <DayPanel
            v-if="selected"
            :date="selected"
            :items="selectedItems"
            :weekend="weekend.includes(weekdayOf(selected))"
            :today="today"
            :can-create="canCreate"
            @create="openCreate"
            @edit="openEdit"
            @delete="askDelete"
          />
        </aside>
      </div>
    </template>

    <!-- Mobile day sheet (Modal renders as a bottom sheet below sm) -->
    <Modal :open="sheetOpen && !isDesktop && !!selected" title="Day ledger" @close="sheetOpen = false">
      <DayPanel
        v-if="selected"
        :date="selected"
        :items="selectedItems"
        :weekend="weekend.includes(weekdayOf(selected))"
        :today="today"
        :can-create="canCreate"
        @create="openCreate"
        @edit="openEdit"
        @delete="askDelete"
      />
    </Modal>

    <EventModal :open="editor.open" :event-id="editor.id" :default-date="editor.date" @close="editor.open = false" @saved="onSaved" />

    <Modal :open="!!pendingDelete" title="Delete event" width="max-w-md" @close="pendingDelete = null">
      <p class="text-sm">Delete <strong class="font-medium">{{ pendingDelete?.title }}</strong>? Attendees will no longer see it.</p>
      <p v-if="deleteError" class="mt-3 text-sm text-rust" role="alert">{{ deleteError }}</p>
      <template #footer>
        <button type="button" class="btn-ghost" @click="pendingDelete = null">Keep</button>
        <button type="button" class="btn-danger" :disabled="deleting" @click="confirmDelete">{{ deleting ? "Deleting…" : "Delete event" }}</button>
      </template>
    </Modal>
  </div>
</template>
