<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import {
  type Balance, type BalancesResponse, type Holiday, type LeaveRequest,
  countWorkingDays, errorMessage, fieldErrors, fmtDays, plural,
} from "./leave";

/** `balances` are for `year` (the page's selected year); other years are fetched on demand. */
const props = defineProps<{ open: boolean; balances: Balance[]; year: number }>();
const emit = defineEmits<{ close: []; created: [req: LeaveRequest] }>();

const form = reactive({ leave_type: "" as number | "", start_date: "", end_date: "", half_day: false, reason: "" });
const errors = ref<Record<string, string>>({});
const saving = ref(false);

// Calendar facts for the client-side preview (server recomputes `days`).
const weekendDays = ref<number[]>([5]);
const holidays = ref(new Set<string>());
const loadedYears = new Set<number>();
let orgLoaded = false;

async function loadCalendar(years: number[]) {
  if (!orgLoaded) {
    orgLoaded = true;
    api.get<{ weekend_days: number[] }>("org/organization/")
      .then(({ data }) => { if (Array.isArray(data.weekend_days)) weekendDays.value = data.weekend_days; })
      .catch(() => { orgLoaded = false; });
  }
  for (const y of years) {
    if (loadedYears.has(y)) continue;
    loadedYears.add(y);
    api.get<Holiday[]>("calendar/holidays/", { params: { year: y } })
      .then(({ data }) => {
        const next = new Set(holidays.value);
        data.filter((h) => !h.is_optional).forEach((h) => next.add(h.date));
        holidays.value = next;
      })
      .catch(() => loadedYears.delete(y));
  }
}

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    Object.assign(form, { leave_type: props.balances[0]?.leave_type.id ?? "", start_date: "", end_date: "", half_day: false, reason: "" });
    errors.value = {};
  },
);

const singleDay = computed(() => !!form.start_date && form.start_date === form.end_date);
watch(singleDay, (one) => { if (!one) form.half_day = false; });

// Typing a start date first fills the end date so single-day leave is one field.
watch(() => form.start_date, (s, prev) => {
  if (s && (!form.end_date || form.end_date === prev || form.end_date < s)) form.end_date = s;
});

watch(() => [form.start_date, form.end_date], () => {
  const ys = [form.start_date, form.end_date].filter(Boolean).map((d) => Number(d.slice(0, 4)));
  if (ys.length) loadCalendar([...new Set(ys)]);
});

const rangeValid = computed(() => !!form.start_date && !!form.end_date && form.end_date >= form.start_date);

const preview = computed(() => {
  if (!rangeValid.value) return null;
  const n = countWorkingDays(form.start_date, form.end_date, weekendDays.value, holidays.value);
  return n && form.half_day ? 0.5 : n;
});

// Availability must match the year being requested (the server checks quota per calendar year).
const balanceYear = computed(() => (form.start_date ? Number(form.start_date.slice(0, 4)) : props.year));
const otherYears = reactive(new Map<number, Balance[] | null>()); // null = failed to load
watch(() => props.open, (open) => { if (open) otherYears.clear(); }); // fresh numbers each time
watch(balanceYear, (y) => {
  if (y === props.year || otherYears.has(y) || y < 1900 || y > 2200) return;
  api.get<BalancesResponse>("leave/balances/", { params: { year: y } })
    .then(({ data }) => otherYears.set(y, data.balances))
    .catch(() => otherYears.set(y, null));
});
const yearBalances = computed(() => (balanceYear.value === props.year ? props.balances : otherYears.get(balanceYear.value)));
const selected = computed(() => yearBalances.value?.find((b) => b.leave_type.id === form.leave_type));
/** Days still bookable: remaining minus what is already pending (server counts pending on create). */
const available = (b: Balance) => (b.remaining === null ? null : Math.max(0, b.remaining - b.pending));
const overBalance = computed(() => {
  const b = selected.value;
  const a = b && available(b);
  return b?.leave_type.is_paid && a !== null && a !== undefined && preview.value !== null && preview.value > a;
});

function optionLabel(b: Balance) {
  const yb = yearBalances.value?.find((x) => x.leave_type.id === b.leave_type.id);
  if (!yb) return b.leave_type.name;
  const a = available(yb);
  return `${b.leave_type.name} — ${a === null ? "no fixed quota" : `${fmtDays(a)} available`}`;
}

async function submit() {
  errors.value = {};
  if (form.end_date && form.start_date && form.end_date < form.start_date) {
    errors.value = { end_date: "End date can't be before the start date." };
    return;
  }
  saving.value = true;
  try {
    const { data } = await api.post<LeaveRequest>("leave/requests/", { ...form, reason: form.reason.trim() });
    emit("created", data);
  } catch (e) {
    const fe = fieldErrors(e);
    errors.value = fe.detail || !Object.keys(fe).length ? { non_field_errors: errorMessage(e) } : fe;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal :open="open" title="Apply for leave" width="max-w-lg" @close="emit('close')">
    <form id="apply-leave" class="grid gap-4" novalidate @submit.prevent="submit">
      <p v-if="errors.non_field_errors" class="rounded-lg border border-rust/30 bg-rust/5 px-3 py-2 text-sm text-rust" role="alert">
        {{ errors.non_field_errors }}
      </p>

      <div class="field">
        <label for="lv-type" class="ledger-label">Leave type</label>
        <select id="lv-type" v-model="form.leave_type" class="input" required :aria-invalid="!!errors.leave_type" aria-describedby="lv-type-hint lv-type-err">
          <option v-if="!balances.length" value="" disabled>No leave types available</option>
          <option v-for="b in balances" :key="b.leave_type.id" :value="b.leave_type.id">{{ optionLabel(b) }}</option>
        </select>
        <p v-if="selected" id="lv-type-hint" class="readout text-[11px] text-ink/50">
          <template v-if="selected.remaining !== null">
            {{ balanceYear }}: {{ fmtDays(selected.remaining) }} remaining · {{ fmtDays(selected.pending) }} pending · {{ fmtDays(selected.quota) }} / yr
          </template>
          <template v-else>No fixed allowance{{ selected.leave_type.is_paid ? "" : " · unpaid" }}</template>
        </p>
        <p v-else-if="form.leave_type !== '' && yearBalances === undefined" id="lv-type-hint" class="readout text-[11px] text-ink/50">Loading {{ balanceYear }} balance…</p>
        <p v-else-if="yearBalances === null" id="lv-type-hint" class="readout text-[11px] text-ink/50">Couldn't load the {{ balanceYear }} balance; it is checked on submit.</p>
        <p v-if="errors.leave_type" id="lv-type-err" class="text-xs text-rust">{{ errors.leave_type }}</p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="field">
          <label for="lv-start" class="ledger-label">From</label>
          <input id="lv-start" v-model="form.start_date" type="date" class="input readout" required :aria-invalid="!!errors.start_date" aria-describedby="lv-start-err" />
          <p v-if="errors.start_date" id="lv-start-err" class="text-xs text-rust">{{ errors.start_date }}</p>
        </div>
        <div class="field">
          <label for="lv-end" class="ledger-label">To (inclusive)</label>
          <input id="lv-end" v-model="form.end_date" type="date" class="input readout" required :min="form.start_date || undefined" :aria-invalid="!!errors.end_date" aria-describedby="lv-end-err" />
          <p v-if="errors.end_date" id="lv-end-err" class="text-xs text-rust">{{ errors.end_date }}</p>
        </div>
      </div>

      <div>
        <label class="flex items-center gap-2 text-sm" :class="singleDay ? 'text-ink' : 'text-ink/40'">
          <input v-model="form.half_day" type="checkbox" class="h-4 w-4 accent-flag" :disabled="!singleDay" aria-describedby="lv-half-hint" />
          Half day
        </label>
        <p id="lv-half-hint" class="mt-1 text-[11px] text-ink/45">{{ singleDay ? "Counts as 0.5 days." : "Available when From and To are the same day." }}</p>
        <p v-if="errors.half_day" class="mt-1 text-xs text-rust">{{ errors.half_day }}</p>
      </div>

      <div class="field">
        <label for="lv-reason" class="ledger-label">Reason</label>
        <textarea id="lv-reason" v-model="form.reason" rows="3" maxlength="2000" class="input" required :aria-invalid="!!errors.reason" placeholder="A line for your approver" />
        <p v-if="errors.reason" class="text-xs text-rust">{{ errors.reason }}</p>
      </div>

      <div class="flex items-baseline justify-between gap-3 rounded-lg border border-dashed border-ink/20 px-3 py-2.5" aria-live="polite">
        <span class="ledger-label">Working days (est.)</span>
        <span class="readout text-sm" :class="overBalance ? 'text-rust' : 'text-ink'">
          <template v-if="preview === null">—</template>
          <template v-else-if="preview === 0">No working days in range</template>
          <template v-else>{{ plural(preview, "day") }}<template v-if="overBalance"> · exceeds available</template></template>
        </span>
      </div>
      <p class="-mt-2 text-[11px] text-ink/45">Weekends and public holidays are skipped. The final count is confirmed on submit.</p>
    </form>

    <template #footer>
      <button type="button" class="btn-ghost btn-sm" @click="emit('close')">Cancel</button>
      <button type="submit" form="apply-leave" class="btn-primary btn-sm" :disabled="saving || !balances.length">
        {{ saving ? "Submitting…" : "Submit request" }}
      </button>
    </template>
  </Modal>
</template>
