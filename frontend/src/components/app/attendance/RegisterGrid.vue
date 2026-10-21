<script setup lang="ts">
import { computed, ref, watch } from "vue";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import EmptyState from "../ui/EmptyState.vue";
import MonthPicker from "./MonthPicker.vue";
import StatusLegend from "./StatusLegend.vue";
import RecordEditor from "./RecordEditor.vue";
import {
  STATUS_META, errMsg, fmtDay, fmtMinutes, thisMonth, todayNPT,
  type AttendanceRecord, type CellStatus, type Department, type RegisterDay, type RegisterResponse, type StaffRef,
} from "./attendance";

const props = defineProps<{ departments: Department[]; canEdit: boolean }>();
const { user: me, hasRole } = useAuth();
// Mirrors the API: nobody but super_admin corrects their own attendance.
const canEditRow = (id: number) => props.canEdit && (id !== me.value?.id || hasRole("super_admin"));

const month = ref(thisMonth());
const department = ref<number | "">("");
const data = ref<RegisterResponse | null>(null);
const records = ref(new Map<string, AttendanceRecord>());
const loading = ref(true);
const error = ref("");
const exporting = ref(false);
const exportError = ref("");

const params = () => ({ month: month.value, ...(department.value ? { department: department.value } : {}) });

async function load() {
  loading.value = true;
  error.value = "";
  try {
    // HR needs record ids to correct cells; the register itself only carries statuses.
    const [reg, recs] = await Promise.all([
      api.get<RegisterResponse>("attendance/register/", { params: params() }),
      props.canEdit ? api.get<AttendanceRecord[]>("attendance/records/", { params: params() }) : null,
    ]);
    data.value = reg.data;
    records.value = new Map((recs?.data ?? []).map((r) => [`${r.user}|${r.date}`, r]));
  } catch (e) {
    error.value = errMsg(e, "Couldn't load the register.");
  } finally {
    loading.value = false;
  }
}
watch([month, department], load, { immediate: true });

async function exportCsv() {
  exporting.value = true;
  exportError.value = "";
  try {
    const { data: blob } = await api.get<Blob>("attendance/register/", { params: { ...params(), format: "csv" }, responseType: "blob" });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), { href: url, download: `attendance-register-${month.value}.csv` });
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    exportError.value = errMsg(e, "Couldn't export the CSV.");
  } finally {
    exporting.value = false;
  }
}

const today = todayNPT();
const WD = ["M", "T", "W", "T", "F", "S", "S"];

const editing = ref<{ user: StaffRef; date: string; record: AttendanceRecord | null } | null>(null);
function openCell(user: StaffRef, day: RegisterDay) {
  if (!canEditRow(user.id) || day.date > today) return;
  editing.value = { user, date: day.date, record: records.value.get(`${user.id}|${day.date}`) ?? null };
}
function onSaved() {
  editing.value = null;
  load();
}

const cellLabel = (user: StaffRef, day: RegisterDay, s: CellStatus | null) =>
  `${user.full_name}, ${fmtDay(day.date, { weekday: "short", day: "numeric", month: "short" })}: ${s ? STATUS_META[s].label : "no entry"}${day.holiday_name ? ` (${day.holiday_name})` : ""}`;

const rowCount = computed(() => data.value?.rows.length ?? 0);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div class="flex flex-wrap items-end gap-3">
        <MonthPicker v-model="month" />
        <div v-if="departments.length > 1" class="field">
          <label for="reg-dept" class="ledger-label">Department</label>
          <select id="reg-dept" v-model="department" class="input !w-auto !py-1.5">
            <option value="">All</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
      </div>
      <button type="button" class="btn-ghost btn-sm" :disabled="exporting || !rowCount" @click="exportCsv">
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 3v12m0 0-4-4m4 4 4-4M4 21h16" /></svg>
        {{ exporting ? "Exporting…" : "Export CSV" }}
      </button>
    </div>
    <p v-if="exportError" class="text-sm text-rust" role="alert">{{ exportError }}</p>

    <div v-if="error" class="panel flex flex-col items-start gap-3 border-rust/25 p-5 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div>
        <p class="font-display text-base">Couldn't read the register</p>
        <p class="mt-0.5 text-sm text-ink/60">{{ error }}</p>
      </div>
      <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>

    <section v-else class="panel" aria-labelledby="reg-title" :aria-busy="loading">
      <div class="panel-head flex-wrap">
        <div>
          <h2 id="reg-title" class="font-display text-base">Monthly register</h2>
          <p v-if="canEdit" class="mt-0.5 text-xs text-ink/50">Select a cell to correct or add a record.</p>
        </div>
        <StatusLegend />
      </div>

      <div v-if="loading && !data" class="space-y-2 p-5">
        <div v-for="i in 6" :key="i" class="h-8 animate-pulse rounded border border-dashed border-ink/10 bg-panel/30" />
      </div>
      <EmptyState v-else-if="!data || !rowCount" title="No staff on this register" hint="Nobody in your scope was employed during this month." />
      <div v-else class="overflow-x-auto" :class="loading ? 'opacity-60' : ''">
        <table class="w-max min-w-full border-collapse text-xs">
          <caption class="sr-only">Attendance register for {{ data.month }}: one row per person, one column per day</caption>
          <thead>
            <tr>
              <th scope="col" class="ledger-label sticky left-0 z-20 min-w-[11rem] border-b border-ink/15 bg-sheet px-3 py-2 text-left">Employee</th>
              <th
                v-for="d in data.days"
                :key="d.date"
                scope="col"
                class="border-b border-ink/15 px-0.5 py-1.5 text-center font-mono font-normal"
                :class="[d.kind !== 'working' ? 'bg-panel/50 text-ink/40' : 'text-ink/60', d.date === today ? '!text-flag' : '']"
                :title="d.holiday_name ?? undefined"
              >
                <span class="block text-[9px]">{{ WD[d.weekday] }}</span>
                <span class="block text-[10.5px]">{{ d.date.slice(8) }}</span>
              </th>
              <th v-for="h in ['P', 'L', 'A', 'LV']" :key="h" scope="col" class="ledger-label border-b border-l border-ink/15 px-2 py-2 text-center">{{ h }}</th>
              <th scope="col" class="ledger-label border-b border-ink/15 px-3 py-2 text-right">Hours</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.rows" :key="row.user.id" class="group">
              <th scope="row" class="sticky left-0 z-10 border-b border-dashed border-ink/10 bg-sheet px-3 py-1.5 text-left font-normal group-hover:bg-panel">
                <span class="block max-w-[11rem] truncate text-[13px] font-medium text-ink">{{ row.user.full_name }}</span>
                <span class="block max-w-[11rem] truncate text-[11px] text-ink/45">{{ row.user.department?.name ?? row.user.designation }}</span>
              </th>
              <td v-for="(c, i) in row.cells" :key="data.days[i]!.date" class="border-b border-dashed border-ink/10 p-0.5 text-center group-hover:bg-panel/40">
                <button
                  v-if="canEditRow(row.user.id) && data.days[i]!.date <= today"
                  type="button"
                  class="inline-flex h-7 w-7 items-center justify-center rounded font-mono text-[9.5px] font-medium hover:ring-2 hover:ring-flag/60 focus-visible:ring-2 focus-visible:ring-flag focus-visible:outline-none"
                  :class="c ? STATUS_META[c].cell : 'border border-ink/10 text-ink/30'"
                  :aria-label="`Edit: ${cellLabel(row.user, data.days[i]!, c)}`"
                  @click="openCell(row.user, data.days[i]!)"
                >{{ c ? STATUS_META[c].letter : "" }}</button>
                <span
                  v-else
                  class="inline-flex h-7 w-7 items-center justify-center rounded font-mono text-[9.5px] font-medium"
                  :class="c ? STATUS_META[c].cell : 'text-ink/20'"
                  :title="cellLabel(row.user, data.days[i]!, c)"
                  role="img"
                  :aria-label="cellLabel(row.user, data.days[i]!, c)"
                >{{ c ? STATUS_META[c].letter : "·" }}</span>
              </td>
              <td class="readout border-b border-l border-dashed border-ink/10 px-2 text-center text-moss">{{ row.totals.present }}</td>
              <td class="readout border-b border-dashed border-ink/10 px-2 text-center text-contour-ink">{{ row.totals.late }}</td>
              <td class="readout border-b border-dashed border-ink/10 px-2 text-center text-rust">{{ row.totals.absent }}</td>
              <td class="readout border-b border-dashed border-ink/10 px-2 text-center text-sky">{{ row.totals.on_leave }}</td>
              <td class="readout border-b border-dashed border-ink/10 px-3 text-right whitespace-nowrap">{{ fmtMinutes(row.totals.worked_minutes) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <RecordEditor
      v-if="canEdit"
      :open="!!editing"
      :user="editing?.user ?? null"
      :date="editing?.date ?? today"
      :record="editing?.record ?? null"
      @close="editing = null"
      @saved="onSaved"
    />
  </div>
</template>
