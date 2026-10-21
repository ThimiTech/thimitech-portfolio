<script setup lang="ts">
import { onMounted, ref } from "vue";
import api from "@/api/api";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import DataTable, { type Column } from "../../components/app/ui/DataTable.vue";
import StatusPill from "../../components/app/ui/StatusPill.vue";
import LoadError from "../../components/app/org/LoadError.vue";
import { errorMessage } from "../../components/app/pm/pm";
import { money, monthLabel, type MyPayslip } from "../../components/app/finance/finance";

const rows = ref<MyPayslip[]>([]);
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = (await api.get<MyPayslip[]>("finance/my-payslips/")).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const columns: Column<MyPayslip>[] = [
  { key: "period", label: "Month", sortable: true },
  { key: "gross", label: "Gross", class: "text-right" },
  { key: "deductions", label: "Deductions", class: "text-right" },
  { key: "net", label: "Net pay", class: "text-right" },
  { key: "status", label: "Status", sortable: true },
  { key: "actions", label: "Open", srOnly: true, class: "text-right" },
];
</script>

<template>
  <div>
    <PageHeader eyebrow="Self-service" title="My pay" description="Your issued and paid payslips. Open one to view or print it." />
    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />
    <DataTable
      v-else
      :rows="rows"
      :columns="columns"
      :loading="loading"
      :row-key="(r) => r.id"
      caption="My payslips"
      empty-title="No payslips yet"
      empty-hint="Payslips appear here once HR issues them."
    >
      <template #cell-period="{ row }"><span class="font-medium text-ink">{{ monthLabel(row.period) }}</span></template>
      <template #cell-gross="{ row }"><span class="readout">{{ money(row.gross, row.currency) }}</span></template>
      <template #cell-deductions="{ row }"><span class="readout">{{ money(row.deductions, row.currency) }}</span></template>
      <template #cell-net="{ row }"><span class="readout font-medium">{{ money(row.net, row.currency) }}</span></template>
      <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
      <template #cell-actions="{ row }">
        <RouterLink :to="`/app/my-pay/${row.id}`" class="btn-ghost btn-sm" :aria-label="`Open payslip for ${monthLabel(row.period)}`">View</RouterLink>
      </template>
    </DataTable>
  </div>
</template>
