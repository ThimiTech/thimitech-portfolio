<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import api from "@/api/api";
import StatusPill from "../ui/StatusPill.vue";
import { errMsg, fmtDay, fmtElapsed, fmtMinutes, fmtTime, type AttendanceRecord, type TodayResponse, type WorkMode } from "./attendance";

const emit = defineEmits<{ changed: [] }>();

const today = ref<TodayResponse | null>(null);
const loading = ref(true);
const loadError = ref("");
const busy = ref(false);
const actionError = ref("");
const mode = ref<WorkMode>("office");
const note = ref("");

// Live clock, corrected by the server's clock so the "late" hint matches the backend.
const skew = ref(0);
const now = ref(Date.now());
let timer: number | undefined;
onMounted(() => {
  timer = window.setInterval(() => (now.value = Date.now() + skew.value), 1000);
  load();
});
onBeforeUnmount(() => clearInterval(timer));

async function load() {
  loading.value = !today.value;
  loadError.value = "";
  try {
    const { data } = await api.get<TodayResponse>("attendance/today/");
    today.value = data;
    skew.value = new Date(data.server_time).getTime() - Date.now();
    now.value = Date.now() + skew.value;
    if (data.record) mode.value = data.record.work_mode;
  } catch (e) {
    loadError.value = errMsg(e, "Couldn't load today's attendance.");
  } finally {
    loading.value = false;
  }
}

const rec = computed(() => today.value?.record ?? null);
const clock = computed(() => fmtTime(new Date(now.value).toISOString(), true));

type State = "leave" | "ready" | "working" | "done" | "closed";
const state = computed<State>(() => {
  const t = today.value;
  if (!t) return "closed";
  if (t.on_leave || rec.value?.status === "on_leave") return "leave";
  if (rec.value?.check_in && !rec.value.check_out) return "working";
  if (rec.value?.check_out) return "done";
  return t.can_check_in ? "ready" : "closed";
});

const elapsed = computed(() => {
  const r = rec.value;
  if (!r?.check_in) return 0;
  return now.value - new Date(r.check_in).getTime();
});

const lateHint = computed(
  // Second precision, like the backend: 10:15:01 is already late when late_after is 10:15.
  () => state.value === "ready" && !!today.value?.is_working_day && clock.value > `${today.value.policy.late_after}:00`,
);

const dayNote = computed(() => {
  const t = today.value;
  if (!t || t.is_working_day) return "";
  return t.day_kind === "holiday" ? `${t.holiday_name ?? "Holiday"} · public holiday` : "Weekend";
});

async function punch(kind: "check-in" | "check-out") {
  busy.value = true;
  actionError.value = "";
  try {
    const body = kind === "check-in" ? { work_mode: mode.value, note: note.value.trim() } : { note: note.value.trim() };
    const { data } = await api.post<AttendanceRecord>(`attendance/${kind}/`, body);
    // Show the returned record immediately, then reconcile flags from /today/.
    if (today.value) today.value = { ...today.value, record: data, can_check_in: false, can_check_out: kind === "check-in" };
    note.value = "";
    emit("changed");
    load();
  } catch (e) {
    actionError.value = errMsg(e);
    load();
  } finally {
    busy.value = false;
  }
}

const darkLabel = "font-mono text-[10px] uppercase tracking-[0.14em] text-paper/45";
</script>

<template>
  <section class="rise panel overflow-hidden" aria-labelledby="punch-title">
    <!-- Loading -->
    <div v-if="loading" class="grid md:grid-cols-[1.15fr_1fr]" aria-busy="true" aria-label="Loading today's attendance">
      <div class="keep-ink space-y-3 bg-ink p-6 sm:p-8">
        <div class="h-3 w-32 animate-pulse rounded bg-paper/10" />
        <div class="h-16 w-64 max-w-full animate-pulse rounded bg-paper/10" />
        <div class="h-3 w-44 animate-pulse rounded bg-paper/10" />
      </div>
      <div class="space-y-3 p-6 sm:p-8">
        <div class="h-3 w-24 animate-pulse rounded bg-panel" />
        <div class="h-24 animate-pulse rounded-lg border border-dashed border-ink/15" />
        <div class="h-11 animate-pulse rounded-full bg-panel" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="flex flex-col items-start gap-3 p-6 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div>
        <p class="font-display text-lg">Couldn't read today's punch card</p>
        <p class="mt-1 text-sm text-ink/60">{{ loadError }}</p>
      </div>
      <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>

    <div v-else-if="today" class="grid md:grid-cols-[1.15fr_1fr]">
      <!-- Left: the clock face -->
      <div class="keep-ink contour-bg min-w-0 bg-ink p-6 text-paper sm:p-8">
        <p class="font-mono text-[10.5px] uppercase tracking-[0.14em] text-paper/50">
          <span id="punch-title">Punch card</span> · {{ fmtDay(today.date, { weekday: "long", day: "2-digit", month: "short", year: "numeric" }) }}
        </p>
        <p class="mt-4 font-display text-[52px] leading-none font-medium tracking-tight tabular-nums sm:text-[72px]">
          {{ clock }}
        </p>
        <p class="mt-2 font-mono text-[11px] tracking-wider text-paper/45">NPT · UTC+05:45</p>

        <dl class="mt-7 grid max-w-sm grid-cols-3 gap-4 border-t border-dashed border-paper/15 pt-4">
          <div>
            <dt :class="darkLabel">Shift</dt>
            <dd class="readout mt-1 text-sm">{{ today.policy.work_start }}–{{ today.policy.work_end }}</dd>
          </div>
          <div>
            <dt :class="darkLabel">Late after</dt>
            <dd class="readout mt-1 text-sm">{{ today.policy.late_after }}</dd>
          </div>
          <div>
            <dt :class="darkLabel">Day</dt>
            <dd class="mt-1 text-sm capitalize">{{ today.day_kind }}</dd>
          </div>
        </dl>
        <p v-if="dayNote" class="mt-5 inline-flex items-center gap-2 rounded-full border border-dashed border-paper/25 px-3 py-1 text-xs text-paper/75">
          <span class="h-1.5 w-1.5 rounded-full bg-sky" aria-hidden="true" />{{ dayNote }}
        </p>
      </div>

      <!-- Right: status + one action -->
      <div class="p-6 sm:p-8" aria-live="polite">
        <div class="flex items-center justify-between gap-3">
          <p class="ledger-label">Today's entry</p>
          <StatusPill v-if="rec" :status="rec.status" />
          <StatusPill v-else-if="state === 'leave'" status="on_leave" />
          <StatusPill v-else status="not_checked_in" label="Not in yet" />
        </div>

        <!-- On leave -->
        <div v-if="state === 'leave'" class="mt-5">
          <p class="font-display text-2xl">You're on leave today.</p>
          <p v-if="today.leave" class="mt-2 text-sm text-ink/65">
            {{ today.leave.leave_type }} · {{ fmtDay(today.leave.start_date) }} → {{ fmtDay(today.leave.end_date) }}
          </p>
          <p class="mt-1 text-sm text-ink/50">No check-in needed. Enjoy the time off.</p>
        </div>

        <!-- Ready to check in -->
        <form v-else-if="state === 'ready'" class="mt-5 space-y-4" @submit.prevent="punch('check-in')">
          <fieldset>
            <legend class="ledger-label">Working from</legend>
            <div class="mt-2 inline-flex rounded-full border border-ink/15 bg-paper p-0.5">
              <label
                v-for="m in (['office', 'remote'] as const)"
                :key="m"
                class="cursor-pointer rounded-full px-4 py-1.5 text-sm capitalize transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-flag/40"
                :class="mode === m ? 'bg-ink text-paper' : 'text-ink/60 hover:text-ink'"
              >
                <input v-model="mode" type="radio" name="work_mode" :value="m" class="sr-only" />{{ m }}
              </label>
            </div>
          </fieldset>
          <div class="field">
            <label for="punch-note" class="ledger-label">Note <span class="normal-case tracking-normal">(optional)</span></label>
            <input id="punch-note" v-model="note" maxlength="255" class="input" placeholder="e.g. site visit in Bhaktapur" />
          </div>
          <p v-if="lateHint" class="text-xs text-contour-ink">It's past {{ today.policy.late_after }}, so this check-in will be marked late.</p>
          <p v-else-if="!today.is_working_day" class="text-xs text-ink/55">Not a working day. Checking in logs it as extra time.</p>
          <button type="submit" class="btn-primary w-full !py-3 text-base" :disabled="busy">
            {{ busy ? "Checking in…" : "Check in" }}
          </button>
        </form>

        <!-- On the clock -->
        <div v-else-if="state === 'working' && rec" class="mt-5 space-y-4">
          <div>
            <p class="ledger-label">On the clock</p>
            <p class="readout mt-1 font-display text-4xl text-ink" role="timer" aria-label="Time worked so far">{{ fmtElapsed(elapsed) }}</p>
            <p class="mt-1 text-sm text-ink/60">
              In at <span class="readout text-ink">{{ fmtTime(rec.check_in) }}</span> · <span class="capitalize">{{ rec.work_mode }}</span>
            </p>
          </div>
          <form class="space-y-3" @submit.prevent="punch('check-out')">
            <div class="field">
              <label for="out-note" class="ledger-label">Note <span class="normal-case tracking-normal">(optional)</span></label>
              <input id="out-note" v-model="note" maxlength="255" class="input" :placeholder="rec.note || 'What did you get done today?'" />
            </div>
            <button type="submit" class="btn-ink w-full !py-3 text-base" :disabled="busy">
              {{ busy ? "Checking out…" : "Check out" }}
            </button>
          </form>
        </div>

        <!-- Shift closed -->
        <div v-else-if="state === 'done' && rec" class="mt-5">
          <p class="font-display text-2xl">Shift closed.</p>
          <dl class="mt-4 grid grid-cols-3 gap-3 border-t border-dashed border-ink/15 pt-4">
            <div><dt class="ledger-label">In</dt><dd class="readout mt-1">{{ fmtTime(rec.check_in) }}</dd></div>
            <div><dt class="ledger-label">Out</dt><dd class="readout mt-1">{{ fmtTime(rec.check_out) }}</dd></div>
            <div><dt class="ledger-label">Worked</dt><dd class="readout mt-1">{{ fmtMinutes(rec.worked_minutes) }}</dd></div>
          </dl>
          <p v-if="rec.note" class="mt-3 text-sm text-ink/60">“{{ rec.note }}”</p>
          <p class="mt-3 text-xs text-ink/45">See you tomorrow.</p>
        </div>

        <!-- Nothing to punch (e.g. HR recorded the day) -->
        <div v-else class="mt-5">
          <p class="font-display text-xl">No punch available.</p>
          <p class="mt-1 text-sm text-ink/55">Today's entry is managed by HR. Ask them if it looks wrong.</p>
        </div>

        <p v-if="actionError" class="mt-3 rounded-md border border-rust/30 bg-rust/10 px-3 py-2 text-sm text-rust" role="alert">{{ actionError }}</p>
      </div>
    </div>
  </section>
</template>
