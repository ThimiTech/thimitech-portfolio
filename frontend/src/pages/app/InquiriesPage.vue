<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import api from "@/api/api";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import DataTable, { type Column } from "@/components/app/ui/DataTable.vue";
import Modal from "@/components/app/ui/Modal.vue";
import StatusPill from "@/components/app/ui/StatusPill.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import { useServerTable } from "@/components/app/ui/serverTable";
import { toast } from "@/components/app/ui/toast";
import { errMsg } from "@/components/app/attendance/attendance";

type Status = "new" | "in_progress" | "closed" | "spam";
interface Inquiry {
  id: number; name: string; email: string; phone: string; company: string; message: string; status: Status
  assignee: number | null; assignee_detail: { id: number; full_name: string } | null; note: string; created_at: string
}
interface Person { id: number; full_name: string; role: string }

const STATUS: Record<Status, string> = { new: "New", in_progress: "In progress", closed: "Closed", spam: "Spam" };
const route = useRoute();
const status = ref<Status | "all">("all");
const table = useServerTable<Inquiry>("inquiries/", {
  params: () => ({ status: status.value === "all" ? undefined : status.value }),
});
const owners = ref<Person[]>([]);
const columns: Column<Inquiry>[] = [
  { key: "name", label: "From", sortable: true, class: "min-w-44" },
  { key: "message", label: "Message", class: "min-w-64" },
  { key: "status", label: "Status", sortable: true },
  { key: "assignee", label: "Owner", class: "min-w-32" },
  { key: "created_at", label: "Received", sortable: true, class: "whitespace-nowrap" },
];
const when = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kathmandu", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

const current = ref<Inquiry | null>(null);
const draft = reactive({ status: "new" as Status, assignee: null as number | null, note: "" });
const saving = ref(false);
function open(i: Inquiry) {
  current.value = i;
  Object.assign(draft, { status: i.status, assignee: i.assignee, note: i.note });
}
async function save() {
  if (!current.value) return;
  saving.value = true;
  try {
    await api.patch(`inquiries/${current.value.id}/`, draft);
    current.value = null;
    toast.success("Inquiry updated.");
    table.load();
  } catch (e) {
    toast.error(errMsg(e, "Couldn't save the inquiry."));
  } finally {
    saving.value = false;
  }
}

async function openFromLink() {
  const id = Number(route.query.open);
  if (!id) return;
  try {
    open((await api.get<Inquiry>(`inquiries/${id}/`)).data);
  } catch {
    /* gone, or not ours to see */
  }
}
watch(() => route.query.open, openFromLink);
onMounted(async () => {
  table.load();
  openFromLink();
  try {
    const { data } = await api.get<Person[]>("org/people/", { params: { is_active: true } });
    owners.value = data.filter((p) => ["manager", "hr_admin", "super_admin"].includes(p.role));
  } catch {
    /* the owner picker stays empty */
  }
});
</script>

<template>
  <div>
    <PageHeader eyebrow="Admin · Inquiries" title="Inquiries" description="Messages sent from the contact form on the public site. Give each one an owner and close it when it is answered." />

    <LoadError v-if="table.error.value" :message="table.error.value" :busy="table.loading.value" @retry="table.load()" />
    <DataTable
      v-model:page="table.page.value"
      v-model:search="table.search.value"
      v-model:ordering="table.ordering.value"
      :rows="table.rows.value"
      :total="table.total.value"
      :loading="table.loading.value"
      :page-size="table.pageSize"
      :columns="columns"
      :row-key="(i) => i.id"
      caption="Inquiries"
      search-placeholder="Name, email, company or message…"
      empty-title="No inquiries in this view"
      empty-hint="New messages from the public contact form appear here."
    >
      <template #toolbar>
        <label class="sr-only" for="inq-status">Status</label>
        <select id="inq-status" v-model="status" class="input w-auto">
          <option value="all">All</option>
          <option v-for="(label, id) in STATUS" :key="id" :value="id">{{ label }}</option>
        </select>
      </template>
      <template #cell-name="{ row }">
        <button type="button" class="text-left font-medium text-ink hover:text-flag focus-visible:outline-none focus-visible:underline" @click="open(row)">{{ row.name }}</button>
        <span class="block text-xs text-ink/55">{{ row.company || row.email }}</span>
      </template>
      <template #cell-message="{ row }"><span class="line-clamp-2 text-ink/75">{{ row.message }}</span></template>
      <template #cell-status="{ row }"><StatusPill :status="row.status" :label="STATUS[row.status]" /></template>
      <template #cell-assignee="{ row }">
        <template v-if="row.assignee_detail">{{ row.assignee_detail.full_name }}</template>
        <span v-else class="text-ink/40">Unassigned</span>
      </template>
      <template #cell-created_at="{ row }"><span class="readout text-xs">{{ when(row.created_at) }}</span></template>
    </DataTable>

    <Modal :open="!!current" :title="current ? `From ${current.name}` : ''" width="max-w-2xl" @close="current = null">
      <template v-if="current">
        <dl class="grid gap-3 text-sm sm:grid-cols-3">
          <div><dt class="ledger-label">Email</dt><dd><a :href="`mailto:${current.email}`" class="break-all text-river hover:text-flag">{{ current.email }}</a></dd></div>
          <div><dt class="ledger-label">Phone</dt><dd class="readout">{{ current.phone || "—" }}</dd></div>
          <div><dt class="ledger-label">Company</dt><dd>{{ current.company || "—" }}</dd></div>
        </dl>
        <p class="ledger-label mt-4">Message · {{ when(current.created_at) }}</p>
        <p class="mt-1 max-h-60 overflow-y-auto text-sm leading-relaxed whitespace-pre-line text-ink/85">{{ current.message }}</p>

        <div class="mt-5 grid gap-4 border-t border-dashed border-ink/15 pt-5 sm:grid-cols-2">
          <label class="field">
            <span class="ledger-label">Status</span>
            <select v-model="draft.status" class="input">
              <option v-for="(label, id) in STATUS" :key="id" :value="id">{{ label }}</option>
            </select>
          </label>
          <label class="field">
            <span class="ledger-label">Owner</span>
            <select v-model="draft.assignee" class="input">
              <option :value="null">Unassigned</option>
              <option v-for="p in owners" :key="p.id" :value="p.id">{{ p.full_name }}</option>
            </select>
          </label>
          <label class="field sm:col-span-2">
            <span class="ledger-label">Follow-up notes</span>
            <textarea v-model="draft.note" rows="3" class="input" placeholder="What was agreed, and what happens next." />
          </label>
        </div>
      </template>
      <template #footer>
        <a v-if="current" :href="`mailto:${current.email}`" class="btn-ghost mr-auto">Reply by email</a>
        <button type="button" class="btn-ghost" @click="current = null">Cancel</button>
        <button type="button" class="btn-primary" :disabled="saving" @click="save">Save</button>
      </template>
    </Modal>
  </div>
</template>
