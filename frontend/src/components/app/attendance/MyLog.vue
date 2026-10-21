<script setup lang="ts">
import { computed, ref, watch } from "vue";
import api from "@/api/api";
import StatusPill from "../ui/StatusPill.vue";
import EmptyState from "../ui/EmptyState.vue";
import MonthPicker from "./MonthPicker.vue";
import StatusLegend from "./StatusLegend.vue";
import {
  STATUS_META, errMsg, fmtDay, fmtMinutes, fmtTime, pyWeekday, thisMonth, todayNPT,
  type AttendanceRecord, type CellStatus, type MeResponse,
} from "./attendance";

const props = withDefaults(defineProps<{ refreshKey?: number }>(), { refreshKey: 0 });

const month = ref(thisMonth());
const data = ref<MeResponse | null>(null);
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = (await api.get<MeResponse>("attendance/me/", { params: { month: month.value } })).data;
  } catch (e) {
    error.value = errMsg(e, "Couldn't load your attendance log.");
  } finally {
    loading.value = false;
  }
}
watch([month, () => props.refreshKey], load, { immediate: true });

interface Day { date: string; status: CellStatus | null; record: AttendanceRecord | null; holiday?: string }

// Statuses come from the server (leave, join date, weekend, holidays all applied there), joined to records.
const days = computed<Day[]>(() => {
  const byDate = new Map((data.value?.records ?? []).map((r) => [r.date, r]));
  return (data.value?.days ?? []).map((d) => ({
    date: d.date,
    status: d.status,
    record: byDate.get(d.date) ?? null,
    holiday: d.holiday_name ?? undefined,
  }));
});

// Sunday-first grid (Nepal week), so pad with blanks before the 1st.
const lead = computed(() => (data.value ? (pyWeekday(data.value.start) + 1) % 7 : 0));
const WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const rows = computed(() =>
  days.value.filter((d) => d.record || (d.status && d.status !== "weekend" && d.status !== "holiday")).reverse(),
);

const tiles = computed(() => {
  const s = data.value?.summary;
  if (!s) return [];
  return [
    { label: "Present", value: s.present, status: "present" as const },
    { label: "Late", value: s.late, status: "late" as const },
    { label: "Absent", value: s.absent, status: "absent" as const },
    { label: "On leave", value: s.on_leave, status: "on_leave" as const },
  ];
});

const dayLabel = (d: Day) =>
  `${fmtDay(d.date, { weekday: "long", day: "numeric", month: "long" })}: ${d.status ? STATUS_META[d.status].label : "upcoming"}${d.holiday ? ` (${d.holiday})` : ""}${d.record?.check_in ? `, in ${fmtTime(d.record.check_in)}` : ""}`;
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <MonthPicker v-model="month" />
      <p v-if="data" class="font-mono text-[11px] text-ink/50">
        {{ data.summary.working_days_elapsed }}/{{ data.summary.working_days_in_month }} working days elapsed
      </p>
    </div>

    <div v-if="error" class="panel flex flex-col items-start gap-3 border-rust/25 p-5 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div>
        <p class="font-display text-base">Couldn't read this month</p>
        <p class="mt-0.5 text-sm text-ink/60">{{ error }}</p>
      </div>
      <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>

    <template v-else>
      <!-- Summary tiles -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" :aria-busy="loading">
        <template v-if="loading && !data">
          <div v-for="i in 6" :key="i" class="panel h-[88px] animate-pulse border-dashed bg-panel/40" />
        </template>
        <template v-else-if="data">
          <div v-for="t in tiles" :key="t.label" class="panel p-4">
            <p class="ledger-label flex items-center gap-1.5">
              <span class="inline-flex h-4 min-w-4 items-center justify-center rounded px-0.5 text-[8.5px]" :class="STATUS_META[t.status].cell" aria-hidden="true">{{ STATUS_META[t.status].letter }}</span>
              {{ t.label }}
            </p>
            <p class="mt-2 font-display text-3xl tabular-nums">{{ t.value }}</p>
          </div>
          <div class="panel border-flag/30 p-4">
            <p class="ledger-label">Attendance rate</p>
            <p class="mt-2 font-display text-3xl tabular-nums text-flag">
              {{ data.summary.attendance_rate == null ? "—" : `${data.summary.attendance_rate}%` }}
            </p>
          </div>
          <div class="panel p-4">
            <p class="ledger-label">Total hours</p>
            <p class="readout mt-3 text-xl">{{ fmtMinutes(data.summary.worked_minutes_total) }}</p>
          </div>
        </template>
      </div>

      <!-- Month heatmap -->
      <section class="panel" aria-labelledby="heat-title">
        <div class="panel-head flex-wrap">
          <h2 id="heat-title" class="font-display text-base">Month at a glance</h2>
          <StatusLegend :items="['present', 'late', 'absent', 'on_leave', 'holiday', 'weekend']" />
        </div>
        <div class="panel-body">
          <div class="grid grid-cols-7 gap-1.5 sm:gap-2" :class="loading ? 'opacity-50' : ''">
            <span v-for="w in WEEK" :key="w" class="ledger-label pb-1 text-center !text-[9.5px]" aria-hidden="true">{{ w }}</span>
            <span v-for="i in lead" :key="`b${i}`" aria-hidden="true" />
            <div
              v-for="d in days"
              :key="d.date"
              class="relative flex aspect-square flex-col items-center justify-center rounded-md sm:aspect-[5/4]"
              :class="[d.status ? STATUS_META[d.status].cell : 'border border-ink/10 text-ink/30', d.date === todayNPT() ? 'ring-2 ring-flag ring-offset-2 ring-offset-sheet' : '']"
              :title="dayLabel(d)"
              :aria-label="dayLabel(d)"
              role="img"
            >
              <span class="absolute top-1 left-1.5 font-mono text-[9px] opacity-70">{{ Number(d.date.slice(8)) }}</span>
              <span class="font-mono text-[11px] font-medium sm:text-xs">{{ d.status ? STATUS_META[d.status].letter : "" }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Day ledger -->
      <section class="panel" aria-labelledby="log-title">
        <div class="panel-head">
          <h2 id="log-title" class="font-display text-base">Daily log</h2>
          <span class="ledger-label">{{ rows.length }} entries</span>
        </div>
        <div v-if="loading && !data" class="space-y-2 p-5">
          <div v-for="i in 5" :key="i" class="h-9 animate-pulse rounded border border-dashed border-ink/10 bg-panel/30" />
        </div>
        <EmptyState v-else-if="!rows.length" title="Nothing logged this month" hint="Check-ins you make will be recorded here, one line per day." />
        <div v-else class="overflow-x-auto">
          <table class="ledger-table min-w-[620px]">
            <caption class="sr-only">Your attendance for each day of the month</caption>
            <thead>
              <tr><th scope="col">Date</th><th scope="col">In</th><th scope="col">Out</th><th scope="col">Worked</th><th scope="col">Mode</th><th scope="col">Status</th></tr>
            </thead>
            <tbody>
              <tr v-for="d in rows" :key="d.date">
                <td class="whitespace-nowrap">
                  <span class="readout">{{ fmtDay(d.date) }}</span>
                  <span v-if="d.holiday" class="ml-2 text-xs text-sky">{{ d.holiday }}</span>
                </td>
                <td class="readout">{{ fmtTime(d.record?.check_in) }}</td>
                <td class="readout">{{ fmtTime(d.record?.check_out) }}</td>
                <td class="readout">{{ fmtMinutes(d.record?.worked_minutes) }}</td>
                <td class="capitalize text-ink/70">{{ d.record?.work_mode ?? "—" }}</td>
                <td>
                  <StatusPill v-if="d.status" :status="d.status" :label="STATUS_META[d.status].label" />
                  <span v-if="d.record?.note" class="mt-1 block max-w-[16rem] truncate text-xs text-ink/50" :title="d.record.note">{{ d.record.note }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>
