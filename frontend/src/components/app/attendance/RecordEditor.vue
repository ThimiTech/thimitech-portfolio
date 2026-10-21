<script setup lang="ts">
import { ref, watch } from "vue";
import { isAxiosError } from "axios";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import { errMsg, fmtDay, fmtTime, toISO, type AttendanceRecord, type RecordStatus, type WorkMode } from "./attendance";

const props = defineProps<{
  open: boolean;
  user: { id: number; full_name: string } | null;
  date: string;
  record: AttendanceRecord | null;
}>();
const emit = defineEmits<{ close: []; saved: [AttendanceRecord] }>();

const form = ref({ status: "present" as RecordStatus, work_mode: "office" as WorkMode, check_in: "", check_out: "", note: "" });
const initial = ref({ ...form.value });
const errors = ref<Record<string, string>>({});
const formError = ref("");
const saving = ref(false);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    const r = props.record;
    const hhmm = (iso: string | null | undefined) => (iso ? fmtTime(iso) : "");
    form.value = {
      status: r?.status ?? "present",
      work_mode: r?.work_mode ?? "office",
      check_in: hhmm(r?.check_in),
      check_out: hhmm(r?.check_out),
      note: r?.note ?? "",
    };
    initial.value = { ...form.value };
    errors.value = {};
    formError.value = "";
  },
);

async function save() {
  if (!props.user) return;
  saving.value = true;
  errors.value = {};
  formError.value = "";
  const body = {
    status: form.value.status,
    work_mode: form.value.work_mode,
    check_in: toISO(props.date, form.value.check_in),
    check_out: toISO(props.date, form.value.check_out),
    note: form.value.note.trim(),
  };
  // PATCH only what changed, so untouched times keep their original seconds.
  const changed = Object.fromEntries(
    (Object.keys(body) as (keyof typeof body)[]).filter((k) => form.value[k] !== initial.value[k]).map((k) => [k, body[k]]),
  );
  try {
    const { data } = props.record
      ? await api.patch<AttendanceRecord>(`attendance/records/${props.record.id}/`, changed)
      : await api.post<AttendanceRecord>("attendance/records/", { ...body, user: props.user.id, date: props.date });
    emit("saved", data);
  } catch (e) {
    const d = isAxiosError(e) ? e.response?.data : null;
    if (d && typeof d === "object" && !("detail" in d)) {
      for (const [k, v] of Object.entries(d as Record<string, unknown>)) {
        const msg = Array.isArray(v) ? String(v[0]) : String(v);
        if (k in form.value) errors.value[k] = msg;
        else formError.value = msg;
      }
    } else formError.value = errMsg(e, "Couldn't save this record.");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal :open="open" :title="record ? 'Correct record' : 'Add record'" @close="emit('close')">
    <form id="att-record-form" class="space-y-4" @submit.prevent="save">
      <p class="text-sm text-ink/70">
        <span class="font-medium text-ink">{{ user?.full_name }}</span> ·
        <span class="readout">{{ fmtDay(date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }) }}</span>
      </p>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="field">
          <label for="rec-status" class="ledger-label">Status</label>
          <select id="rec-status" v-model="form.status" class="input" :aria-invalid="!!errors.status" aria-describedby="rec-status-err">
            <option value="present">Present</option>
            <option value="late">Late</option>
            <option value="absent">Absent</option>
            <option value="on_leave">On leave</option>
          </select>
          <p v-if="errors.status" id="rec-status-err" class="text-xs text-rust">{{ errors.status }}</p>
        </div>
        <div class="field">
          <label for="rec-mode" class="ledger-label">Work mode</label>
          <select id="rec-mode" v-model="form.work_mode" class="input">
            <option value="office">Office</option>
            <option value="remote">Remote</option>
          </select>
        </div>
        <div class="field">
          <label for="rec-in" class="ledger-label">Check-in (NPT)</label>
          <input id="rec-in" v-model="form.check_in" type="time" class="input font-mono" :aria-invalid="!!errors.check_in" aria-describedby="rec-in-err" />
          <p v-if="errors.check_in" id="rec-in-err" class="text-xs text-rust">{{ errors.check_in }}</p>
        </div>
        <div class="field">
          <label for="rec-out" class="ledger-label">Check-out (NPT)</label>
          <input id="rec-out" v-model="form.check_out" type="time" class="input font-mono" :aria-invalid="!!errors.check_out" aria-describedby="rec-out-err" />
          <p v-if="errors.check_out" id="rec-out-err" class="text-xs text-rust">{{ errors.check_out }}</p>
        </div>
      </div>
      <div class="field">
        <label for="rec-note" class="ledger-label">Note</label>
        <input id="rec-note" v-model="form.note" maxlength="255" class="input" placeholder="Reason for the correction" />
        <p v-if="errors.note" class="text-xs text-rust">{{ errors.note }}</p>
      </div>
      <p v-if="record?.check_in_ip" class="font-mono text-[11px] text-ink/45">IP in {{ record.check_in_ip }}<template v-if="record.check_out_ip"> · out {{ record.check_out_ip }}</template></p>
      <p v-if="formError" class="rounded-md border border-rust/30 bg-rust/10 px-3 py-2 text-sm text-rust" role="alert">{{ formError }}</p>
    </form>
    <template #footer>
      <button type="button" class="btn-ghost btn-sm" @click="emit('close')">Cancel</button>
      <button type="submit" form="att-record-form" class="btn-primary btn-sm" :disabled="saving">{{ saving ? "Saving…" : "Save record" }}</button>
    </template>
  </Modal>
</template>
