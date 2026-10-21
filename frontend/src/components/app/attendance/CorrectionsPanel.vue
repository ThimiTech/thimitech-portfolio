<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import DataTable, { type Column } from "../ui/DataTable.vue";
import EmptyState from "../ui/EmptyState.vue";
import StatusPill from "../ui/StatusPill.vue";
import LoadError from "../org/LoadError.vue";
import { toast } from "../ui/toast";
import { type Correction, errMsg, fmtDay, shiftDate, todayNPT } from "./attendance";

const props = defineProps<{ canApprove: boolean; startOpen?: boolean }>();
const emit = defineEmits<{ decided: [] }>();

const mine = ref<Correction[]>([]);
const approvals = ref<Correction[]>([]);
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [m, a] = await Promise.all([
      api.get<Correction[]>("attendance/corrections/"),
      props.canApprove ? api.get<Correction[]>("attendance/corrections/", { params: { scope: "approvals" } }) : null,
    ]);
    mine.value = m.data;
    approvals.value = a?.data ?? [];
  } catch (e) {
    error.value = errMsg(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const hhmm = (t: string | null) => (t ? t.slice(0, 5) : "—");

// ---- request form ----
const today = todayNPT();
const minDate = shiftDate(today, -30);
const maxDate = shiftDate(today, -1);
const open = ref(!!props.startOpen);
const busy = ref(false);
const formError = ref("");
const form = reactive({ date: maxDate, check_in: "", check_out: "", reason: "" });
function openForm() {
  Object.assign(form, { date: maxDate, check_in: "", check_out: "", reason: "" });
  formError.value = "";
  open.value = true;
}
async function submit() {
  busy.value = true;
  formError.value = "";
  try {
    const { data } = await api.post<Correction>("attendance/corrections/", { ...form, check_out: form.check_out || null });
    mine.value = [data, ...mine.value];
    open.value = false;
    toast.success(`Correction for ${fmtDay(data.date)} sent for approval.`);
  } catch (e) {
    formError.value = errMsg(e);
  } finally {
    busy.value = false;
  }
}

// ---- approvals ----
const notes = reactive<Record<number, string>>({});
const cardError = reactive<Record<number, string>>({});
async function decide(c: Correction, action: "approve" | "reject") {
  const note = (notes[c.id] ?? "").trim();
  if (action === "reject" && !note) {
    cardError[c.id] = "Add a note explaining the rejection.";
    document.getElementById(`cnote-${c.id}`)?.focus();
    return;
  }
  cardError[c.id] = "";
  try {
    await api.post(`attendance/corrections/${c.id}/${action}/`, { decision_note: note });
    approvals.value = approvals.value.filter((x) => x.id !== c.id);
    toast.success(`${action === "approve" ? "Approved" : "Rejected"} ${c.user_name}'s correction.`);
    emit("decided");
  } catch (e) {
    cardError[c.id] = errMsg(e);
  }
}

const columns: Column<Correction>[] = [
  { key: "date", label: "Day", sortable: true },
  { key: "times", label: "Requested times" },
  { key: "reason", label: "Reason", class: "min-w-48" },
  { key: "status", label: "Status", sortable: true },
  { key: "decision_note", label: "Decision" },
];
</script>

<template>
  <div class="space-y-8">
    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />

    <section v-if="canApprove && !error" aria-labelledby="corr-approvals">
      <h3 id="corr-approvals" class="ledger-label mb-3">Waiting on you</h3>
      <div v-if="!approvals.length && !loading" class="panel">
        <EmptyState title="Nothing to decide" hint="Correction requests from your team land here." />
      </div>
      <ul v-else class="grid gap-3 lg:grid-cols-2">
        <li v-for="c in approvals" :key="c.id" class="panel flex flex-col">
          <div class="panel-head">
            <p class="font-medium text-ink">{{ c.user_name }}</p>
            <p class="readout text-sm">{{ fmtDay(c.date) }}</p>
          </div>
          <div class="panel-body grid flex-1 gap-3">
            <p class="readout text-sm">{{ hhmm(c.check_in) }} → {{ hhmm(c.check_out) }}</p>
            <p class="text-sm text-ink/75">“{{ c.reason }}”</p>
            <label class="field">
              <span class="ledger-label">Decision note</span>
              <textarea :id="`cnote-${c.id}`" v-model="notes[c.id]" rows="2" maxlength="2000" class="input" placeholder="Required when rejecting" />
            </label>
            <p v-if="cardError[c.id]" class="text-xs text-rust" role="alert">{{ cardError[c.id] }}</p>
          </div>
          <div class="flex justify-end gap-2 border-t border-dashed border-ink/15 px-5 py-3">
            <button class="btn-danger btn-sm" :aria-label="`Reject ${c.user_name}'s correction`" @click="decide(c, 'reject')">Reject</button>
            <button class="btn-primary btn-sm" :aria-label="`Approve ${c.user_name}'s correction`" @click="decide(c, 'approve')">Approve</button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="!error" aria-labelledby="corr-mine">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h3 id="corr-mine" class="ledger-label">My correction requests</h3>
        <button type="button" class="btn-ink btn-sm" @click="openForm">+ Request a correction</button>
      </div>
      <DataTable
        :rows="mine"
        :columns="columns"
        :loading="loading"
        :row-key="(r) => r.id"
        caption="My attendance correction requests"
        empty-title="No corrections requested"
        empty-hint="Missed a punch? Request a correction for any of the last 30 days."
      >
        <template #cell-date="{ row }"><span class="readout">{{ fmtDay(row.date) }}</span></template>
        <template #cell-times="{ row }"><span class="readout">{{ hhmm(row.check_in) }} → {{ hhmm(row.check_out) }}</span></template>
        <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
        <template #cell-decision_note="{ row }">
          <span v-if="row.approver_name" class="text-sm">{{ row.approver_name }}<template v-if="row.decision_note">: {{ row.decision_note }}</template></span>
          <span v-else>—</span>
        </template>
      </DataTable>
    </section>

    <Modal :open="open" title="Request an attendance correction" @close="open = false">
      <form class="grid gap-4" @submit.prevent="submit">
        <p class="text-sm text-ink/65">Times are Nepal time. Your manager (or HR) approves it, and the day's record is updated.</p>
        <label class="field">
          <span class="ledger-label">Day</span>
          <input v-model="form.date" type="date" class="input" :min="minDate" :max="maxDate" required />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="ledger-label">Check-in</span><input v-model="form.check_in" type="time" class="input" required /></label>
          <label class="field"><span class="ledger-label">Check-out (optional)</span><input v-model="form.check_out" type="time" class="input" /></label>
        </div>
        <label class="field">
          <span class="ledger-label">Reason</span>
          <textarea v-model="form.reason" rows="3" maxlength="500" class="input" required />
        </label>
        <p v-if="formError" role="alert" class="text-sm text-rust">{{ formError }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy">{{ busy ? "Sending…" : "Send for approval" }}</button>
      </form>
    </Modal>
  </div>
</template>
