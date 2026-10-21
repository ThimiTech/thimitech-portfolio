<script setup lang="ts">
import { confirmDialog } from "../ui/confirm";
import { onMounted, reactive, ref } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import EmptyState from "../ui/EmptyState.vue";
import StatusPill from "../ui/StatusPill.vue";
import { type LeaveType, errorMessage, fieldErrors, fmtDays } from "./leave";

const emit = defineEmits<{ changed: [] }>();

const types = ref<LeaveType[]>([]);
const loading = ref(true);
const error = ref("");
const actionError = ref("");
const busyId = ref<number | null>(null);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    types.value = (await api.get<LeaveType[]>("leave/types/")).data;
  } catch (e) {
    error.value = errorMessage(e, "Couldn't load leave types.");
  } finally {
    loading.value = false;
  }
}
onMounted(load);

// ── Editor ─────────────────────────────────────────────
const editing = ref<LeaveType | null>(null);
const editorOpen = ref(false);
const blank = { name: "", code: "", annual_quota: 0, is_paid: true, color: "#7a6a52", is_active: true };
const form = reactive({ ...blank });
const errors = ref<Record<string, string>>({});
const saving = ref(false);
const codeTouched = ref(false);

function openEditor(t: LeaveType | null) {
  editing.value = t;
  Object.assign(form, t
    ? { name: t.name, code: t.code, annual_quota: t.annual_quota, is_paid: t.is_paid, color: t.color || "#7a6a52", is_active: t.is_active }
    : blank);
  codeTouched.value = !!t;
  errors.value = {};
  editorOpen.value = true;
}

function onName() {
  if (!codeTouched.value) form.code = form.name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 30);
}

async function save() {
  saving.value = true;
  errors.value = {};
  try {
    const payload = { ...form, annual_quota: Number(form.annual_quota) || 0 };
    const { data } = editing.value
      ? await api.patch<LeaveType>(`leave/types/${editing.value.id}/`, payload)
      : await api.post<LeaveType>("leave/types/", payload);
    types.value = editing.value
      ? types.value.map((t) => (t.id === data.id ? data : t))
      : [...types.value, data].sort((a, b) => a.name.localeCompare(b.name));
    editorOpen.value = false;
    emit("changed");
  } catch (e) {
    const fe = fieldErrors(e);
    errors.value = fe.detail || !Object.keys(fe).length ? { non_field_errors: errorMessage(e) } : fe;
  } finally {
    saving.value = false;
  }
}

// ── Deactivate / reactivate ────────────────────────────
async function remove(t: LeaveType) {
  if (!(await confirmDialog({ title: "Remove leave type", body: `Remove “${t.name}”? If it has requests it will be deactivated instead of deleted.`, confirmLabel: "Remove" }))) return;
  busyId.value = t.id;
  actionError.value = "";
  try {
    const res = await api.delete<LeaveType | "">(`leave/types/${t.id}/`);
    // 204 = deleted; 200 + body = had requests, so it was deactivated.
    types.value = res.status === 204 || !res.data
      ? types.value.filter((x) => x.id !== t.id)
      : types.value.map((x) => (x.id === t.id ? (res.data as LeaveType) : x));
    emit("changed");
  } catch (e) {
    actionError.value = errorMessage(e);
  } finally {
    busyId.value = null;
  }
}

async function reactivate(t: LeaveType) {
  busyId.value = t.id;
  actionError.value = "";
  try {
    const { data } = await api.patch<LeaveType>(`leave/types/${t.id}/`, { is_active: true });
    types.value = types.value.map((x) => (x.id === t.id ? data : x));
    emit("changed");
  } catch (e) {
    actionError.value = errorMessage(e);
  } finally {
    busyId.value = null;
  }
}
</script>

<template>
  <section class="panel" aria-labelledby="types-heading">
    <div class="panel-head">
      <div>
        <h2 id="types-heading" class="font-display text-lg font-medium">Leave types</h2>
        <p class="text-xs text-ink/50">Quota 0 means no fixed allowance — no balance check applies.</p>
      </div>
      <button class="btn-ink btn-sm" @click="openEditor(null)">New type</button>
    </div>

    <p v-if="actionError" class="mx-5 mt-4 text-sm text-rust" role="alert">{{ actionError }}</p>

    <div v-if="loading" class="grid gap-2 p-5" aria-busy="true" aria-label="Loading leave types">
      <div v-for="i in 4" :key="i" class="h-10 rounded-md border border-dashed border-ink/15 motion-safe:animate-pulse" />
    </div>
    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 p-5" role="alert">
      <p class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>
    <EmptyState v-else-if="!types.length" title="No leave types yet" hint="Create the first one — Annual, Sick, Casual…" />

    <div v-else class="overflow-x-auto">
      <table class="ledger-table min-w-[620px]">
        <caption class="sr-only">Leave types</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Code</th>
            <th scope="col" class="text-right">Quota / yr</th>
            <th scope="col">Paid</th>
            <th scope="col">State</th>
            <th scope="col"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in types" :key="t.id" :class="t.is_active ? '' : 'text-ink/45'">
            <td>
              <span class="flex items-center gap-2">
                <span class="h-2.5 w-2.5 rounded-full border border-ink/10" :style="{ background: t.color || '#7a6a52' }" aria-hidden="true" />
                {{ t.name }}
              </span>
            </td>
            <td class="readout text-xs">{{ t.code }}</td>
            <td class="readout text-right">{{ t.annual_quota ? fmtDays(t.annual_quota) : "—" }}</td>
            <td class="text-xs">{{ t.is_paid ? "Paid" : "Unpaid" }}</td>
            <td><StatusPill :status="t.is_active ? 'active' : 'inactive'" /></td>
            <td class="whitespace-nowrap text-right">
              <button class="btn-ghost btn-sm" :aria-label="`Edit ${t.name}`" @click="openEditor(t)">Edit</button>
              <button v-if="t.is_active" class="btn-danger btn-sm ml-1.5" :disabled="busyId === t.id" :aria-label="`Remove ${t.name}`" @click="remove(t)">Remove</button>
              <button v-else class="btn-ghost btn-sm ml-1.5" :disabled="busyId === t.id" :aria-label="`Reactivate ${t.name}`" @click="reactivate(t)">Reactivate</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :open="editorOpen" :title="editing ? `Edit ${editing.name}` : 'New leave type'" @close="editorOpen = false">
      <form id="leave-type-form" class="grid gap-4" novalidate @submit.prevent="save">
        <p v-if="errors.non_field_errors" class="rounded-lg border border-rust/30 bg-rust/5 px-3 py-2 text-sm text-rust" role="alert">{{ errors.non_field_errors }}</p>
        <div class="grid gap-4 sm:grid-cols-[1fr_140px]">
          <div class="field">
            <label for="lt-name" class="ledger-label">Name</label>
            <input id="lt-name" v-model="form.name" class="input" required maxlength="80" @input="onName" />
            <p v-if="errors.name" class="text-xs text-rust">{{ errors.name }}</p>
          </div>
          <div class="field">
            <label for="lt-code" class="ledger-label">Code</label>
            <input id="lt-code" v-model="form.code" class="input readout" required maxlength="30" pattern="[-a-zA-Z0-9_]+" @input="codeTouched = true" />
            <p v-if="errors.code" class="text-xs text-rust">{{ errors.code }}</p>
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="field">
            <label for="lt-quota" class="ledger-label">Annual quota (days)</label>
            <input id="lt-quota" v-model.number="form.annual_quota" type="number" min="0" step="0.5" class="input readout" aria-describedby="lt-quota-hint" />
            <p id="lt-quota-hint" class="text-[11px] text-ink/45">0 = no fixed allowance</p>
            <p v-if="errors.annual_quota" class="text-xs text-rust">{{ errors.annual_quota }}</p>
          </div>
          <div class="field">
            <label for="lt-color" class="ledger-label">Colour</label>
            <div class="flex items-center gap-2">
              <input id="lt-color" v-model="form.color" type="color" class="h-9 w-12 cursor-pointer rounded-md border border-ink/15 bg-sheet p-1" />
              <span class="readout text-xs text-ink/55">{{ form.color }}</span>
            </div>
            <p v-if="errors.color" class="text-xs text-rust">{{ errors.color }}</p>
          </div>
        </div>
        <div class="flex flex-wrap gap-5">
          <label class="flex items-center gap-2 text-sm"><input v-model="form.is_paid" type="checkbox" class="h-4 w-4 accent-flag" /> Paid leave</label>
          <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox" class="h-4 w-4 accent-flag" /> Active</label>
        </div>
      </form>
      <template #footer>
        <button type="button" class="btn-ghost btn-sm" @click="editorOpen = false">Cancel</button>
        <button type="submit" form="leave-type-form" class="btn-primary btn-sm" :disabled="saving">{{ saving ? "Saving…" : "Save type" }}</button>
      </template>
    </Modal>
  </section>
</template>
