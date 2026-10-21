<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import api from "@/api/api";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import DataTable, { type Column } from "../../components/app/ui/DataTable.vue";
import EmptyState from "../../components/app/ui/EmptyState.vue";
import Modal from "../../components/app/ui/Modal.vue";
import SkeletonBlock from "../../components/app/ui/SkeletonBlock.vue";
import StatusPill from "../../components/app/ui/StatusPill.vue";
import LoadError from "../../components/app/org/LoadError.vue";
import { toast } from "../../components/app/ui/toast";
import { errorMessage } from "../../components/app/pm/pm";
import { timestamp, type MyAssignment } from "../../components/app/inventory/inventory";

const rows = ref<MyAssignment[]>([]);
const loading = ref(true);
const error = ref("");
const current = computed(() => rows.value.filter((a) => !a.returned_at));
const history = computed(() => rows.value.filter((a) => a.returned_at));

async function load() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = (await api.get<MyAssignment[]>("inventory/my-assets/")).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const reporting = ref<MyAssignment | null>(null);
const note = ref("");
const busy = ref(false);
const formError = ref("");
function openReport(a: MyAssignment) {
  reporting.value = a;
  note.value = "";
  formError.value = "";
}
async function submitReport() {
  busy.value = true;
  formError.value = "";
  try {
    await api.post(`inventory/my-assets/${reporting.value!.id}/report-issue/`, { note: note.value });
    toast.success(`HR has been told about ${reporting.value!.asset_name}.`);
    reporting.value = null;
  } catch (e) {
    formError.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}

const columns: Column<MyAssignment>[] = [
  { key: "asset_name", label: "Asset", sortable: true },
  { key: "assigned_at", label: "Assigned", sortable: true },
  { key: "returned_at", label: "Returned", sortable: true },
  { key: "return_condition", label: "Returned as" },
];
</script>

<template>
  <div class="space-y-8">
    <PageHeader eyebrow="Self-service" title="My assets" description="Equipment checked out to you, and everything you have handed back." />
    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />
    <SkeletonBlock v-else-if="loading" :rows="3" height="h-24" label="Loading your assets" />
    <template v-else>
      <section aria-labelledby="current-heading">
        <h2 id="current-heading" class="ledger-label mb-3">With you now</h2>
        <div v-if="!current.length" class="panel"><EmptyState title="Nothing assigned to you" hint="Assets HR hands over to you will show up here." /></div>
        <ul v-else class="grid gap-3 md:grid-cols-2">
          <li v-for="a in current" :key="a.id" class="panel flex flex-col">
            <div class="panel-head">
              <div class="min-w-0">
                <p class="truncate font-medium text-ink">{{ a.asset_name }}</p>
                <p class="readout text-[11px] text-ink/50">{{ a.asset_tag }} · {{ a.category }}<template v-if="a.serial_number"> · S/N {{ a.serial_number }}</template></p>
              </div>
              <StatusPill status="assigned" />
            </div>
            <div class="panel-body grid flex-1 gap-1 text-sm text-ink/70">
              <p>Since {{ timestamp(a.assigned_at) }}</p>
              <p v-if="a.due_back">Return by <span class="readout">{{ a.due_back }}</span></p>
              <p v-if="a.notes" class="text-ink/60">{{ a.notes }}</p>
            </div>
            <div class="flex justify-end border-t border-dashed border-ink/15 px-5 py-3">
              <button type="button" class="btn-ghost btn-sm" :aria-label="`Report an issue with ${a.asset_name}`" @click="openReport(a)">Report an issue</button>
            </div>
          </li>
        </ul>
      </section>

      <section aria-labelledby="history-heading">
        <h2 id="history-heading" class="ledger-label mb-3">History</h2>
        <DataTable
          :rows="history"
          :columns="columns"
          :row-key="(r) => r.id"
          caption="Returned assets"
          empty-title="No returned assets"
          empty-hint="Assets you hand back are kept here for reference."
        >
          <template #cell-asset_name="{ row }">
            <span class="font-medium text-ink">{{ row.asset_name }}</span>
            <span class="readout block text-[11px] text-ink/50">{{ row.asset_tag }}</span>
          </template>
          <template #cell-assigned_at="{ row }">{{ timestamp(row.assigned_at) }}</template>
          <template #cell-returned_at="{ row }">{{ row.returned_at ? timestamp(row.returned_at) : "—" }}</template>
          <template #cell-return_condition="{ row }"><StatusPill v-if="row.return_condition" :status="row.return_condition" /><span v-else>—</span></template>
        </DataTable>
      </section>
    </template>

    <Modal :open="!!reporting" :title="reporting ? `Report an issue · ${reporting.asset_name}` : 'Report an issue'" @close="reporting = null">
      <form class="grid gap-4" @submit.prevent="submitReport">
        <p class="text-sm text-ink/65">HR admins get a notification with your note. Describe what is wrong and how urgent it is.</p>
        <label class="field">
          <span class="ledger-label">What's wrong?</span>
          <textarea v-model="note" class="input" rows="4" maxlength="2000" required />
        </label>
        <p v-if="formError" role="alert" class="text-sm text-rust">{{ formError }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy || !note.trim()">{{ busy ? "Sending…" : "Send to HR" }}</button>
      </form>
    </Modal>
  </div>
</template>
