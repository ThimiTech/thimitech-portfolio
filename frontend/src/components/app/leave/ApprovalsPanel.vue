<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import api from "@/api/api";
import { toast } from "../ui/toast";
import { useAuth } from "@/stores/auth";
import Avatar from "../ui/Avatar.vue";
import EmptyState from "../ui/EmptyState.vue";
import {
  type Balance, type BalancesResponse, type LeaveRequest,
  errorMessage, fmtDays, fmtRange, fmtStamp, plural,
} from "./leave";

const items = defineModel<LeaveRequest[]>("items", { required: true });
defineProps<{ loading: boolean; error: string }>();
const emit = defineEmits<{ retry: []; decided: [req: LeaveRequest] }>();

const { hasRole } = useAuth();
const isHR = computed(() => hasRole("hr_admin"));
const hrOnly = ref(false);
const shown = computed(() => (hrOnly.value ? items.value.filter((r) => !r.designated_approver) : items.value));

const notes = reactive<Record<number, string>>({});
const noteOpen = reactive<Record<number, boolean>>({});
const cardError = reactive<Record<number, string>>({});

// Requester balances, keyed "userId:year". null = not visible to us / failed.
const balances = reactive<Record<string, Balance[] | null>>({});
const key = (r: LeaveRequest) => `${r.user.id}:${r.start_date.slice(0, 4)}`;

watch(
  items,
  (list) => {
    for (const r of list) {
      const k = key(r);
      if (k in balances) continue;
      balances[k] = null;
      api.get<BalancesResponse>("leave/balances/", { params: { user: r.user.id, year: r.start_date.slice(0, 4) } })
        .then(({ data }) => { balances[k] = data.balances; })
        .catch(() => { /* not permitted or failed: card just omits the balance line */ });
    }
  },
  { immediate: true },
);

function balanceLine(r: LeaveRequest): string {
  const b = balances[key(r)]?.find((x) => x.leave_type.id === r.leave_type.id);
  if (!b) return "Balance not available";
  if (b.remaining === null) return `No fixed quota · ${plural(b.used, "day")} taken in ${r.start_date.slice(0, 4)}`;
  return `Balance: ${fmtDays(b.remaining)} of ${fmtDays(b.quota)} left · ${fmtDays(b.pending)} pending`;
}

async function decide(r: LeaveRequest, action: "approve" | "reject") {
  const note = (notes[r.id] ?? "").trim();
  cardError[r.id] = "";
  if (action === "reject" && !note) {
    noteOpen[r.id] = true;
    cardError[r.id] = `Add a note so ${r.user.full_name.split(" ")[0]} knows why.`;
    await nextTick();
    document.getElementById(`note-${r.id}`)?.focus();
    return;
  }
  // Optimistic: drop the card now, put it back where it was if the server refuses.
  const index = items.value.findIndex((x) => x.id === r.id);
  items.value = items.value.filter((x) => x.id !== r.id);
  toast.success(`${action === "approve" ? "Approved" : "Rejected"} ${r.user.full_name}'s ${r.leave_type.name} leave.`);
  try {
    const { data } = await api.post<LeaveRequest>(`leave/requests/${r.id}/${action}/`, { decision_note: note });
    delete notes[r.id];
    emit("decided", data);
  } catch (e) {
    const next = [...items.value];
    next.splice(Math.min(index, next.length), 0, r);
    items.value = next;
    cardError[r.id] = errorMessage(e);
    toast.error(`Couldn't ${action} ${r.user.full_name}'s request.`);
  }
}
</script>

<template>
  <section aria-labelledby="approvals-heading">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <h2 id="approvals-heading" class="ledger-label">Waiting on you</h2>
      <label v-if="isHR && items.some((r) => r.designated_approver)" class="flex items-center gap-2 text-xs text-ink/65">
        <input v-model="hrOnly" type="checkbox" class="h-3.5 w-3.5 accent-flag" />
        Only requests routed to HR
      </label>
    </div>

    <div v-if="loading" class="grid gap-3 lg:grid-cols-2" aria-busy="true" aria-label="Loading approvals">
      <div v-for="i in 2" :key="i" class="h-48 rounded-xl border border-dashed border-ink/15 bg-sheet/60 motion-safe:animate-pulse" />
    </div>

    <div v-else-if="error" class="panel flex flex-wrap items-center justify-between gap-3 px-5 py-4" role="alert">
      <p class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ghost btn-sm" @click="emit('retry')">Retry</button>
    </div>

    <div v-else-if="!shown.length" class="panel">
      <EmptyState title="Nothing to decide" hint="Requests from your team land here when they need your sign-off." />
    </div>

    <ul v-else class="grid gap-3 lg:grid-cols-2">
      <li v-for="r in shown" :key="r.id" class="panel rise flex flex-col">
        <div class="panel-head">
          <div class="flex min-w-0 items-center gap-3">
            <Avatar :name="r.user.full_name" :size="36" />
            <div class="min-w-0">
              <p class="truncate font-medium text-ink">{{ r.user.full_name }}</p>
              <p class="readout truncate text-[11px] text-ink/45">filed {{ fmtStamp(r.created_at) }}</p>
            </div>
          </div>
          <span class="flex shrink-0 items-center gap-1.5 text-xs text-ink/70">
            <span class="h-2 w-2 rounded-full" :style="{ background: r.leave_type.color || '#7a6a52' }" aria-hidden="true" />
            {{ r.leave_type.name }}
          </span>
        </div>

        <div class="panel-body grid flex-1 gap-3">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <p class="readout text-sm text-ink">
              {{ fmtRange(r.start_date, r.end_date) }}<span v-if="r.half_day" class="ledger-label ml-1.5 text-[9.5px]">½ day</span>
            </p>
            <p class="font-display text-2xl leading-none">{{ fmtDays(r.days) }}<span class="ml-1 font-body text-xs text-ink/45">{{ r.days === 1 ? "day" : "days" }}</span></p>
          </div>

          <p class="text-sm text-ink/75">“{{ r.reason }}”</p>

          <p class="readout text-[11px] text-ink/50">
            {{ balanceLine(r) }}
            <template v-if="isHR && r.designated_approver"> · routed to {{ r.designated_approver.full_name }}</template>
          </p>

          <div v-if="noteOpen[r.id]" class="field">
            <label :for="`note-${r.id}`" class="ledger-label">Decision note</label>
            <textarea :id="`note-${r.id}`" v-model="notes[r.id]" rows="2" maxlength="2000" class="input" placeholder="Required when rejecting" />
          </div>
          <button v-else type="button" class="justify-self-start text-xs text-river underline decoration-dotted underline-offset-4 hover:text-ink" @click="noteOpen[r.id] = true">
            + Add a note
          </button>

          <p v-if="cardError[r.id]" class="text-xs text-rust" role="alert">{{ cardError[r.id] }}</p>
        </div>

        <div class="flex justify-end gap-2 border-t border-dashed border-ink/15 px-5 py-3">
          <button class="btn-danger btn-sm" :aria-label="`Reject ${r.user.full_name}'s request`" @click="decide(r, 'reject')">Reject</button>
          <button class="btn-primary btn-sm" :aria-label="`Approve ${r.user.full_name}'s request`" @click="decide(r, 'approve')">Approve</button>
        </div>
      </li>
    </ul>
  </section>
</template>
