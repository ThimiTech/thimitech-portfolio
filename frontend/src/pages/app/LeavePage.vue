<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import EmptyState from "../../components/app/ui/EmptyState.vue";
import { toast } from "../../components/app/ui/toast";
import BalanceStrip from "../../components/app/leave/BalanceStrip.vue";
import ApplyLeaveModal from "../../components/app/leave/ApplyLeaveModal.vue";
import RequestsTable from "../../components/app/leave/RequestsTable.vue";
import ApprovalsPanel from "../../components/app/leave/ApprovalsPanel.vue";
import TeamRequests from "../../components/app/leave/TeamRequests.vue";
import LeaveTypesManager from "../../components/app/leave/LeaveTypesManager.vue";
import {
  type Balance, type BalancesResponse, type LeaveRequest,
  cancelRequest, currentYear, errorMessage, plural,
} from "../../components/app/leave/leave";

const { hasRole } = useAuth();
const route = useRoute();
const router = useRouter();

const year = ref(currentYear());
const years = [currentYear() + 1, currentYear(), currentYear() - 1, currentYear() - 2];

// ── Balances ───────────────────────────────────────────
const balances = ref<Balance[]>([]);
const balState = reactive({ loading: true, error: "" });
async function loadBalances() {
  balState.loading = !balances.value.length;
  balState.error = "";
  try {
    balances.value = (await api.get<BalancesResponse>("leave/balances/", { params: { year: year.value } })).data.balances;
  } catch (e) {
    balState.error = errorMessage(e, "Couldn't load your balances.");
  } finally {
    balState.loading = false;
  }
}

// ── My requests ────────────────────────────────────────
const mine = ref<LeaveRequest[]>([]);
const mineState = reactive({ loading: true, error: "", actionError: "", busyId: null as number | null });
async function loadMine() {
  mineState.loading = true;
  mineState.error = "";
  try {
    mine.value = (await api.get<LeaveRequest[]>("leave/requests/", { params: { scope: "mine", year: year.value } })).data;
  } catch (e) {
    mineState.error = errorMessage(e, "Couldn't load your requests.");
  } finally {
    mineState.loading = false;
  }
}
async function onCancelMine(r: LeaveRequest) {
  mineState.busyId = r.id;
  mineState.actionError = "";
  try {
    const updated = await cancelRequest(r, true);
    if (!updated) return;
    mine.value = mine.value.map((x) => (x.id === r.id ? updated : x));
    toast.success("Request cancelled.");
    loadBalances();
  } catch (e) {
    mineState.actionError = errorMessage(e);
  } finally {
    mineState.busyId = null;
  }
}

// ── Approvals ──────────────────────────────────────────
const approvals = ref<LeaveRequest[]>([]);
const apprState = reactive({ loading: true, error: "" });
async function loadApprovals() {
  apprState.loading = true;
  apprState.error = "";
  try {
    approvals.value = (await api.get<LeaveRequest[]>("leave/approvals/")).data;
  } catch (e) {
    apprState.error = errorMessage(e, "Couldn't load approvals.");
  } finally {
    apprState.loading = false;
  }
}

// ── Tabs ───────────────────────────────────────────────
type Tab = "mine" | "approvals" | "team" | "types";
const tabs = computed(() => {
  const t: { id: Tab; label: string; count?: number }[] = [{ id: "mine", label: "My leave" }];
  if (approvals.value.length || hasRole("manager")) t.push({ id: "approvals", label: "Approvals", count: approvals.value.length });
  if (hasRole("manager")) t.push({ id: "team", label: "Team" });
  if (hasRole("hr_admin")) t.push({ id: "types", label: "Leave types" });
  return t;
});
const active = ref<Tab>((route.query.tab as Tab) || "mine");
const visited = reactive(new Set<Tab>()); // panels mount on first visit, then stay (keeps filters)
watch(tabs, (list) => { if (!list.some((t) => t.id === active.value)) active.value = "mine"; }, { immediate: true });
watch(active, (t) => {
  visited.add(t);
  if ((route.query.tab ?? "mine") !== t) router.replace({ query: { ...route.query, tab: t === "mine" ? undefined : t } });
}, { immediate: true });
// Links like /app/leave?tab=approvals while already here (pages aren't remounted on query changes).
watch(() => route.query.tab, (q) => {
  const t = (q as Tab) || "mine";
  if (tabs.value.some((x) => x.id === t)) active.value = t;
});

async function onTabKey(e: KeyboardEvent, i: number) {
  const n = tabs.value.length;
  const next = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
  if (next === undefined) return;
  e.preventDefault();
  active.value = tabs.value[next]!.id;
  await nextTick();
  document.getElementById(`tab-${active.value}`)?.focus();
}

// ── Cross-panel refreshes ──────────────────────────────
const applyOpen = ref(false);
const team = ref<InstanceType<typeof TeamRequests> | null>(null);

function onCreated(r: LeaveRequest) {
  applyOpen.value = false;
  toast.success(`Request sent — ${plural(r.days, "working day")}, awaiting ${r.designated_approver?.full_name ?? "HR"}.`);
  active.value = "mine";
  if (r.start_date.slice(0, 4) === String(year.value) || r.end_date.slice(0, 4) === String(year.value)) mine.value = [r, ...mine.value];
  loadBalances();
}
function onDecided() {
  team.value?.load();
}
function onTeamChanged() {
  loadApprovals();
  loadMine();
  loadBalances();
}

watch(year, () => { loadBalances(); loadMine(); });
onMounted(() => { loadBalances(); loadMine(); loadApprovals(); });

// /app/leave?apply=1 (dashboard, command palette) opens the form once balances are in.
watch(
  () => [route.query.apply, balState.loading] as const,
  ([apply, loading]) => {
    if (apply !== "1" || loading) return;
    applyOpen.value = true;
    router.replace({ query: { ...route.query, apply: undefined } });
  },
  { immediate: true },
);
</script>

<template>
  <div>
    <PageHeader eyebrow="A3 · Leave" title="Leave" description="Your balances, requests and — if you lead a team — the approvals waiting on you.">
      <template #actions>
        <label for="leave-year" class="sr-only">Year</label>
        <select id="leave-year" v-model.number="year" class="input readout w-auto py-1.5 text-xs">
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
        <button class="btn-primary" :disabled="balState.loading" @click="applyOpen = true">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          Apply for leave
        </button>
      </template>
    </PageHeader>


    <BalanceStrip :balances="balances" :loading="balState.loading" :error="balState.error" :year="year" @retry="loadBalances" />

    <div role="tablist" aria-label="Leave sections" class="mt-8 mb-5 flex gap-1 overflow-x-auto border-b border-ink/15">
      <button
        v-for="(t, i) in tabs"
        :id="`tab-${t.id}`"
        :key="t.id"
        role="tab"
        :aria-selected="active === t.id"
        :aria-controls="t.id === 'mine' || visited.has(t.id) ? `panel-${t.id}` : undefined"
        :tabindex="active === t.id ? 0 : -1"
        class="-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
        :class="active === t.id ? 'border-flag font-medium text-ink' : 'border-transparent text-ink/55 hover:text-ink'"
        @click="active = t.id"
        @keydown="onTabKey($event, i)"
      >
        {{ t.label }}
        <span v-if="t.count" class="readout rounded-full bg-flag px-1.5 text-[10.5px] leading-[18px] text-on-accent" :aria-label="`${t.count} pending`">{{ t.count }}</span>
      </button>
    </div>

    <!-- My leave -->
    <section v-show="active === 'mine'" id="panel-mine" role="tabpanel" aria-labelledby="tab-mine" class="panel">
      <div class="panel-head">
        <h2 class="font-display text-lg font-medium">My requests</h2>
        <span class="ledger-label">{{ year }}</span>
      </div>
      <p v-if="mineState.actionError" class="mx-5 mt-4 text-sm text-rust" role="alert">{{ mineState.actionError }}</p>
      <div v-if="mineState.loading" class="grid gap-2 p-5" aria-busy="true" aria-label="Loading your requests">
        <div v-for="i in 3" :key="i" class="h-10 rounded-md border border-dashed border-ink/15 motion-safe:animate-pulse" />
      </div>
      <div v-else-if="mineState.error" class="flex flex-wrap items-center justify-between gap-3 p-5" role="alert">
        <p class="text-sm text-rust">{{ mineState.error }}</p>
        <button class="btn-ghost btn-sm" @click="loadMine">Retry</button>
      </div>
      <EmptyState v-else-if="!mine.length" :title="`No leave on record for ${year}`" hint="When you apply, your requests and their decisions show up here.">
        <button class="btn-ghost btn-sm" @click="applyOpen = true">Apply for leave</button>
      </EmptyState>
      <RequestsTable v-else :requests="mine" :busy-id="mineState.busyId" :caption="`My leave requests, ${year}`" @cancel="onCancelMine" />
    </section>

    <div v-if="visited.has('approvals')" v-show="active === 'approvals'" id="panel-approvals" role="tabpanel" aria-labelledby="tab-approvals">
      <ApprovalsPanel v-model:items="approvals" :loading="apprState.loading" :error="apprState.error" @retry="loadApprovals" @decided="onDecided" />
    </div>

    <div v-if="visited.has('team')" v-show="active === 'team'" id="panel-team" role="tabpanel" aria-labelledby="tab-team">
      <TeamRequests ref="team" @changed="onTeamChanged" />
    </div>

    <div v-if="visited.has('types')" v-show="active === 'types'" id="panel-types" role="tabpanel" aria-labelledby="tab-types">
      <LeaveTypesManager @changed="loadBalances" />
    </div>

    <ApplyLeaveModal :open="applyOpen" :balances="balances" :year="year" @close="applyOpen = false" @created="onCreated" />
  </div>
</template>
