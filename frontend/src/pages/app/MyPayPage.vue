<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import api from "@/api/api";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import DataTable, { type Column } from "../../components/app/ui/DataTable.vue";
import StatusPill from "../../components/app/ui/StatusPill.vue";
import LoadError from "../../components/app/org/LoadError.vue";
import MyClaims from "../../components/app/finance/MyClaims.vue";
import { errorMessage } from "../../components/app/pm/pm";
import { amount, money, monthLabel, type MyPayslip } from "../../components/app/finance/finance";

const rows = ref<MyPayslip[]>([]);
const loading = ref(true);
const error = ref("");
const fy = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = (await api.get<MyPayslip[]>("finance/my-payslips/")).data;
    fy.value = rows.value[0]?.fiscal_year || "";
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const years = computed(() => [...new Set(rows.value.map((r) => r.fiscal_year))]);
/** Year-to-date totals: what you need for a tax return, a bank loan or a visa application. */
const ytd = computed(() => {
  const t = { gross: 0, net: 0, ssf: 0, ssfCo: 0, tds: 0, n: 0 };
  for (const r of rows.value.filter((x) => x.fiscal_year === fy.value)) {
    t.gross += +r.gross; t.net += +r.net; t.ssf += +r.ssf_employee; t.ssfCo += +r.ssf_employer; t.tds += +r.tds; t.n++;
  }
  return t;
});

const columns: Column<MyPayslip>[] = [
  { key: "period", label: "Month", sortable: true },
  { key: "gross", label: "Gross", class: "text-right" },
  { key: "total_deductions", label: "Deductions", class: "text-right" },
  { key: "net", label: "Net pay", class: "text-right" },
  { key: "status", label: "Status", sortable: true },
  { key: "actions", label: "Open", srOnly: true, class: "text-right" },
];
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)] gap-8">
    <div>
      <PageHeader eyebrow="Self-service" title="My pay" description="Your payslips, yearly totals for tax and SSF, and expense claims.">
        <template #actions>
          <RouterLink to="/app/drive?view=mine" class="btn-ghost">My documents →</RouterLink>
        </template>
      </PageHeader>
      <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />
      <section v-if="years.length" class="mb-6">
        <div class="mb-3 flex items-center gap-3">
          <h2 class="text-lg font-medium">Fiscal year totals</h2>
          <select v-model="fy" class="input w-auto font-mono text-sm" aria-label="Fiscal year">
            <option v-for="y in years" :key="y" :value="y">FY {{ y }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <div class="panel p-4"><p class="ledger-label">Gross earned</p><p class="readout mt-2 text-xl">{{ amount(ytd.gross) }}</p><p class="mt-1 text-xs text-ink/55">{{ ytd.n }} payslips</p></div>
          <div class="panel p-4"><p class="ledger-label">Take-home</p><p class="readout mt-2 text-xl">{{ amount(ytd.net) }}</p></div>
          <div class="panel p-4"><p class="ledger-label">Tax deducted</p><p class="readout mt-2 text-xl">{{ amount(ytd.tds) }}</p><p class="mt-1 text-xs text-ink/55">TDS / 1% SST</p></div>
          <div class="panel p-4"><p class="ledger-label">Your SSF (11%)</p><p class="readout mt-2 text-xl">{{ amount(ytd.ssf) }}</p></div>
          <div class="panel p-4"><p class="ledger-label">Company SSF (20%)</p><p class="readout mt-2 text-xl">{{ amount(ytd.ssfCo) }}</p><p class="mt-1 text-xs text-ink/55">On top of your pay</p></div>
        </div>
      </section>
      <DataTable
        v-if="!error"
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
        <template #cell-total_deductions="{ row }"><span class="readout">{{ money(row.total_deductions, row.currency) }}</span></template>
        <template #cell-net="{ row }"><span class="readout font-medium">{{ money(row.net, row.currency) }}</span></template>
        <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
        <template #cell-actions="{ row }">
          <RouterLink :to="`/app/my-pay/${row.id}`" class="btn-ghost btn-sm" :aria-label="`Open payslip for ${monthLabel(row.period)}`">View</RouterLink>
        </template>
      </DataTable>
    </div>
    <MyClaims />
  </div>
</template>
