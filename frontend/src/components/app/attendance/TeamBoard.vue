<script setup lang="ts">
import { computed, ref, watch } from "vue";
import api from "@/api/api";
import Avatar from "../ui/Avatar.vue";
import StatusPill from "../ui/StatusPill.vue";
import EmptyState from "../ui/EmptyState.vue";
import { STATUS_META, errMsg, fmtDay, fmtMinutes, fmtTime, shiftDate, todayNPT, type CellStatus, type Department, type TeamResponse } from "./attendance";

defineProps<{ departments: Department[] }>();

const date = ref(todayNPT());
const department = ref<number | "">("");
const data = ref<TeamResponse | null>(null);
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params: Record<string, string | number> = { date: date.value };
    if (department.value) params.department = department.value;
    data.value = (await api.get<TeamResponse>("attendance/team/", { params })).data;
  } catch (e) {
    error.value = errMsg(e, "Couldn't load the team board.");
  } finally {
    loading.value = false;
  }
}
watch(
  [date, department],
  () => {
    // A cleared native date input yields "": snap back to today (re-triggers this watch) instead of breaking.
    if (!date.value) date.value = todayNPT();
    else load();
  },
  { immediate: true },
);

const ORDER: CellStatus[] = ["present", "late", "not_checked_in", "absent", "on_leave", "holiday", "weekend"];
const counts = computed(() => ORDER.map((s) => ({ s, n: data.value?.counts[s] ?? 0 })).filter((c) => c.n > 0));
const members = computed(() =>
  [...(data.value?.members ?? [])].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || a.user.full_name.localeCompare(b.user.full_name)),
);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-end gap-3">
      <div class="field">
        <label for="team-date" class="ledger-label">Date</label>
        <div class="flex items-center gap-1">
          <button type="button" class="btn-ghost btn-sm !px-2" aria-label="Previous day" @click="date = shiftDate(date, -1)">
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <input id="team-date" v-model="date" type="date" class="input !w-auto font-mono" required />
          <button type="button" class="btn-ghost btn-sm !px-2" aria-label="Next day" @click="date = shiftDate(date, 1)">
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
          </button>
          <button v-if="date !== todayNPT()" type="button" class="btn-ghost btn-sm" @click="date = todayNPT()">Today</button>
        </div>
      </div>
      <div v-if="departments.length > 1" class="field">
        <label for="team-dept" class="ledger-label">Department</label>
        <select id="team-dept" v-model="department" class="input !w-auto">
          <option value="">All</option>
          <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="panel flex flex-col items-start gap-3 border-rust/25 p-5 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div>
        <p class="font-display text-base">Couldn't read the team board</p>
        <p class="mt-0.5 text-sm text-ink/60">{{ error }}</p>
      </div>
      <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>

    <section v-else class="panel" aria-labelledby="team-title" :aria-busy="loading">
      <div class="panel-head flex-wrap">
        <div>
          <h2 id="team-title" class="font-display text-base">{{ fmtDay(date, { weekday: "long", day: "numeric", month: "long" }) }}</h2>
          <p v-if="data && data.day_kind !== 'working'" class="mt-0.5 text-xs text-sky">
            {{ data.day_kind === "holiday" ? data.holiday_name ?? "Holiday" : "Weekend" }}
          </p>
        </div>
        <ul v-if="counts.length" class="flex flex-wrap gap-2" aria-label="Status counts">
          <li v-for="c in counts" :key="c.s" class="flex items-center gap-1.5 rounded-full border border-ink/10 bg-paper px-2.5 py-1 text-xs">
            <span class="inline-flex h-4 min-w-4 items-center justify-center rounded px-0.5 font-mono text-[8.5px]" :class="STATUS_META[c.s].cell" aria-hidden="true">{{ STATUS_META[c.s].letter }}</span>
            <span class="readout font-medium">{{ c.n }}</span>
            <span class="text-ink/55">{{ STATUS_META[c.s].label }}</span>
          </li>
        </ul>
      </div>

      <div v-if="loading && !data" class="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-3">
        <div v-for="i in 6" :key="i" class="h-[92px] animate-pulse rounded-lg border border-dashed border-ink/15 bg-panel/30" />
      </div>
      <EmptyState v-else-if="!members.length" title="No one on this sheet" hint="There are no team members to show for this date or department." />
      <ul v-else class="grid gap-3 p-4 sm:grid-cols-2 sm:p-5 xl:grid-cols-3" :class="loading ? 'opacity-60' : ''">
        <li v-for="m in members" :key="m.user.id" class="rounded-lg border border-ink/10 bg-paper/50 p-4">
          <div class="flex items-start gap-3">
            <Avatar :name="m.user.full_name" :photo="m.user.photo" :size="38" />
            <div class="min-w-0 flex-1">
              <RouterLink :to="{ name: 'app-person', params: { id: m.user.id } }" class="block truncate font-medium text-ink hover:text-flag focus-visible:text-flag focus-visible:outline-none">
                {{ m.user.full_name }}
              </RouterLink>
              <p class="truncate text-xs text-ink/50">{{ m.user.designation || m.user.department?.name || m.user.email }}</p>
            </div>
            <StatusPill :status="m.status" :label="STATUS_META[m.status]?.label" />
          </div>
          <dl class="mt-3 grid grid-cols-4 gap-2 border-t border-dashed border-ink/10 pt-3 text-xs">
            <div><dt class="ledger-label !text-[9px]">In</dt><dd class="readout mt-0.5">{{ fmtTime(m.record?.check_in) }}</dd></div>
            <div><dt class="ledger-label !text-[9px]">Out</dt><dd class="readout mt-0.5">{{ fmtTime(m.record?.check_out) }}</dd></div>
            <div><dt class="ledger-label !text-[9px]">Worked</dt><dd class="readout mt-0.5">{{ fmtMinutes(m.record?.worked_minutes) }}</dd></div>
            <div><dt class="ledger-label !text-[9px]">Mode</dt><dd class="mt-0.5 capitalize">{{ m.record?.work_mode ?? "—" }}</dd></div>
          </dl>
        </li>
      </ul>
    </section>
  </div>
</template>
