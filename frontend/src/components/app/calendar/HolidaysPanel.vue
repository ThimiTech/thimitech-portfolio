<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import EmptyState from "../ui/EmptyState.vue";
import StatusPill from "../ui/StatusPill.vue";
import HolidayBulk from "./HolidayBulk.vue";
import { fmtDate, parseError, todayNPT, type Holiday } from "./calendar";

const emit = defineEmits<{ changed: [] }>();

const thisYear = Number(todayNPT().slice(0, 4));
const year = ref(thisYear);
const years = [thisYear - 1, thisYear, thisYear + 1, thisYear + 2];

const list = ref<Holiday[]>([]);
const loading = ref(true);
const error = ref("");
let seq = 0;

async function load() {
  const mine = ++seq;
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.get<Holiday[]>("calendar/holidays/", { params: { year: year.value } });
    if (mine === seq) list.value = data;
  } catch (e) {
    if (mine === seq) error.value = parseError(e).detail;
  } finally {
    if (mine === seq) loading.value = false;
  }
}
watch(year, load, { immediate: true });

// ── Add / edit ──
const modal = reactive({ open: false, id: null as number | null, saving: false, detail: "" });
const form = reactive({ name: "", date: "", description: "", is_optional: false });
const fieldErr = ref<Record<string, string>>({});

function openForm(h?: Holiday) {
  modal.open = true;
  modal.id = h?.id ?? null;
  modal.detail = "";
  fieldErr.value = {};
  Object.assign(form, h ? { name: h.name, date: h.date, description: h.description, is_optional: h.is_optional } : { name: "", date: `${year.value}-01-01`, description: "", is_optional: false });
}

async function save() {
  fieldErr.value = {};
  modal.detail = "";
  if (!form.name.trim()) fieldErr.value.name = "Name is required.";
  if (!form.date) fieldErr.value.date = "Date is required.";
  if (Object.keys(fieldErr.value).length) return;
  modal.saving = true;
  try {
    const body = { ...form, name: form.name.trim() };
    if (modal.id == null) await api.post("calendar/holidays/", body);
    else await api.patch(`calendar/holidays/${modal.id}/`, body);
    modal.open = false;
    const y = Number(form.date.slice(0, 4));
    if (y !== year.value) year.value = y; // jumps to the saved holiday's year (triggers load)
    else await load();
    emit("changed");
  } catch (e) {
    const err = parseError(e);
    fieldErr.value = err.fields;
    modal.detail = err.detail;
  } finally {
    modal.saving = false;
  }
}

// ── Delete (two-step inline confirm, optimistic) ──
const confirming = ref<number | null>(null);
const rowError = ref("");
async function remove(h: Holiday) {
  if (confirming.value !== h.id) {
    confirming.value = h.id;
    return;
  }
  confirming.value = null;
  rowError.value = "";
  const before = list.value;
  list.value = list.value.filter((x) => x.id !== h.id);
  try {
    await api.delete(`calendar/holidays/${h.id}/`);
    emit("changed");
  } catch (e) {
    list.value = before;
    rowError.value = `Couldn't delete “${h.name}”: ${parseError(e).detail}`;
  }
}

function onBulkDone() {
  load();
  emit("changed");
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
    <section class="panel min-w-0" aria-labelledby="hol-title">
      <div class="panel-head flex-wrap">
        <div>
          <p class="ledger-label">Register</p>
          <h2 id="hol-title" class="font-display text-lg font-medium">Holidays · {{ year }}</h2>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex items-center rounded-full border border-ink/15">
            <button type="button" class="rounded-l-full px-2.5 py-1.5 text-ink/60 hover:bg-panel hover:text-ink" aria-label="Previous year" @click="year--">‹</button>
            <label for="hol-year" class="sr-only">Year</label>
            <select id="hol-year" v-model.number="year" class="readout border-x border-ink/15 bg-transparent px-2 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-river/30">
              <option v-for="y in years.includes(year) ? years : [...years, year].sort()" :key="y" :value="y">{{ y }}</option>
            </select>
            <button type="button" class="rounded-r-full px-2.5 py-1.5 text-ink/60 hover:bg-panel hover:text-ink" aria-label="Next year" @click="year++">›</button>
          </div>
          <button type="button" class="btn-primary btn-sm" @click="openForm()">Add holiday</button>
        </div>
      </div>

      <p v-if="rowError" class="mx-5 mt-4 rounded-lg border border-rust/30 bg-rust/10 px-3 py-2 text-sm text-rust" role="alert">{{ rowError }}</p>

      <div v-if="loading" class="space-y-2 p-5" aria-busy="true" aria-label="Loading holidays">
        <div v-for="n in 6" :key="n" class="h-9 animate-pulse rounded border border-dashed border-ink/10 bg-panel/40" />
      </div>
      <div v-else-if="error" class="panel-body text-sm text-rust" role="alert">
        {{ error }} <button type="button" class="btn-ghost btn-sm ml-2" @click="load">Retry</button>
      </div>
      <EmptyState v-else-if="!list.length" :title="`No holidays logged for ${year}`" hint="Add them one by one, or paste the year's list.">
        <button type="button" class="btn-ghost btn-sm" @click="openForm()">Add holiday</button>
      </EmptyState>
      <div v-else class="overflow-x-auto">
        <table class="ledger-table min-w-[520px]">
          <caption class="sr-only">Holidays in {{ year }}</caption>
          <thead>
            <tr><th scope="col">Date</th><th scope="col">Holiday</th><th scope="col">Type</th><th scope="col" class="text-right">Actions</th></tr>
          </thead>
          <tbody>
            <tr v-for="h in list" :key="h.id">
              <td class="whitespace-nowrap">
                <span class="readout text-[12.5px]">{{ h.date }}</span>
                <span class="ml-2 font-mono text-[10.5px] text-ink/45 uppercase">{{ fmtDate(h.date, { weekday: "short" }) }}</span>
              </td>
              <td>
                <p class="font-medium">{{ h.name }}</p>
                <p v-if="h.description" class="max-w-md truncate text-xs text-ink/50" :title="h.description">{{ h.description }}</p>
              </td>
              <td><StatusPill :status="h.is_optional ? 'optional' : 'holiday'" :label="h.is_optional ? 'Optional' : 'Public'" /></td>
              <td class="text-right whitespace-nowrap">
                <button type="button" class="btn-ghost btn-sm" :aria-label="`Edit ${h.name}`" @click="openForm(h)">Edit</button>
                <button
                  type="button"
                  class="btn-danger btn-sm ml-1.5"
                  :aria-label="confirming === h.id ? `Confirm delete ${h.name}` : `Delete ${h.name}`"
                  @click="remove(h)"
                  @blur="confirming === h.id && (confirming = null)"
                >
                  {{ confirming === h.id ? "Confirm?" : "Delete" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel h-fit" aria-labelledby="bulk-title">
      <div class="panel-head">
        <h2 id="bulk-title" class="font-display text-lg font-medium">Import a list</h2>
      </div>
      <div class="panel-body"><HolidayBulk @done="onBulkDone" /></div>
    </section>

    <Modal :open="modal.open" :title="modal.id == null ? 'Add holiday' : 'Edit holiday'" @close="modal.open = false">
      <form id="holiday-form" class="grid gap-4" novalidate @submit.prevent="save">
        <p v-if="modal.detail" class="rounded-lg border border-rust/30 bg-rust/10 px-3 py-2 text-sm text-rust" role="alert">{{ modal.detail }}</p>
        <div class="field">
          <label for="hol-name" class="ledger-label">Name</label>
          <input id="hol-name" v-model="form.name" class="input" maxlength="150" required :aria-invalid="!!fieldErr.name" />
          <p v-if="fieldErr.name" class="text-xs text-rust">{{ fieldErr.name }}</p>
        </div>
        <div class="field">
          <label for="hol-date" class="ledger-label">Date</label>
          <input id="hol-date" v-model="form.date" type="date" class="input" required :aria-invalid="!!fieldErr.date" />
          <p v-if="fieldErr.date" class="text-xs text-rust">{{ fieldErr.date }}</p>
        </div>
        <div class="field">
          <label for="hol-desc" class="ledger-label">Description <span class="normal-case tracking-normal text-ink/35">(optional)</span></label>
          <textarea id="hol-desc" v-model="form.description" rows="2" class="input" />
        </div>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="form.is_optional" type="checkbox" class="h-4 w-4 accent-flag" />
          Optional holiday <span class="text-ink/45">(still a working day)</span>
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn-ghost" @click="modal.open = false">Cancel</button>
        <button type="submit" form="holiday-form" class="btn-primary" :disabled="modal.saving">{{ modal.saving ? "Saving…" : "Save" }}</button>
      </template>
    </Modal>
  </div>
</template>
