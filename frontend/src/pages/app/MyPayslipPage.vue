<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import api from "@/api/api";
import SkeletonBlock from "../../components/app/ui/SkeletonBlock.vue";
import LoadError from "../../components/app/org/LoadError.vue";
import StatusPill from "../../components/app/ui/StatusPill.vue";
import { errorMessage } from "../../components/app/pm/pm";
import { money, monthLabel, type MyPayslip } from "../../components/app/finance/finance";
import { timestamp } from "../../components/app/inventory/inventory";

const route = useRoute();
const slip = ref<MyPayslip | null>(null);
const orgName = ref("Thimi Tech");
const error = ref("");
const loading = ref(true);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    slip.value = (await api.get<MyPayslip>(`finance/my-payslips/${route.params.id}/`)).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
  api.get<{ name: string }>("org/organization/").then(({ data }) => data.name && (orgName.value = data.name)).catch(() => {});
}
onMounted(load);

const print = () => window.print();
</script>

<template>
  <div>
    <div class="no-print mb-6 flex flex-wrap items-center justify-between gap-3">
      <RouterLink to="/app/my-pay" class="text-sm text-river hover:text-ink">← My pay</RouterLink>
      <button v-if="slip" type="button" class="btn-ink btn-sm" @click="print">Print / save as PDF</button>
    </div>

    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />
    <SkeletonBlock v-else-if="loading" :rows="6" label="Loading payslip" />

    <article v-else-if="slip" class="payslip-print panel mx-auto max-w-2xl p-8" aria-labelledby="slip-title">
      <header class="flex flex-wrap items-start justify-between gap-4 border-b border-ink/15 pb-5">
        <div>
          <p class="ledger-label">{{ orgName }}</p>
          <h1 id="slip-title" class="mt-1 font-display text-2xl text-ink">Payslip · {{ monthLabel(slip.period) }}</h1>
        </div>
        <StatusPill :status="slip.status" />
      </header>

      <dl class="grid grid-cols-2 gap-x-6 gap-y-3 border-b border-ink/15 py-5 text-sm">
        <div><dt class="ledger-label">Employee</dt><dd class="mt-1 text-ink">{{ slip.employee_name || slip.employee_email }}</dd></div>
        <div><dt class="ledger-label">Email</dt><dd class="mt-1 text-ink">{{ slip.employee_email }}</dd></div>
        <div><dt class="ledger-label">Designation</dt><dd class="mt-1 text-ink">{{ slip.designation || "—" }}</dd></div>
        <div><dt class="ledger-label">Department</dt><dd class="mt-1 text-ink">{{ slip.department || "—" }}</dd></div>
      </dl>

      <table class="w-full border-b border-ink/15 text-sm">
        <caption class="sr-only">Earnings and deductions</caption>
        <tbody>
          <tr><th scope="row" class="py-2 text-left font-normal text-ink/70">Basic pay</th><td class="readout py-2 text-right">{{ money(slip.basic, slip.currency) }}</td></tr>
          <tr><th scope="row" class="py-2 text-left font-normal text-ink/70">Allowances</th><td class="readout py-2 text-right">{{ money(slip.allowances, slip.currency) }}</td></tr>
          <tr class="border-t border-dashed border-ink/15"><th scope="row" class="py-2 text-left font-medium">Gross pay</th><td class="readout py-2 text-right">{{ money(slip.gross, slip.currency) }}</td></tr>
          <tr><th scope="row" class="py-2 text-left font-normal text-ink/70">Deductions</th><td class="readout py-2 text-right">− {{ money(slip.deductions, slip.currency) }}</td></tr>
          <tr class="border-t border-ink/30"><th scope="row" class="py-3 text-left font-display text-lg">Net pay</th><td class="readout py-3 text-right text-lg font-medium">{{ money(slip.net, slip.currency) }}</td></tr>
        </tbody>
      </table>

      <dl class="grid gap-3 pt-5 text-sm">
        <div v-if="slip.issued_at"><dt class="ledger-label">Issued</dt><dd class="mt-1">{{ timestamp(slip.issued_at) }}</dd></div>
        <div v-if="slip.paid_at"><dt class="ledger-label">Paid</dt><dd class="mt-1">{{ timestamp(slip.paid_at) }}<template v-if="slip.payment_reference"> · ref {{ slip.payment_reference }}</template></dd></div>
        <div v-if="slip.notes"><dt class="ledger-label">Notes</dt><dd class="mt-1 whitespace-pre-line text-ink/75">{{ slip.notes }}</dd></div>
      </dl>
      <p class="mt-8 text-xs text-ink/45">Generated from Thimi Tech OS. Amounts are as issued; contact HR about any discrepancy.</p>
    </article>
  </div>
</template>

<style>
/* Print only the payslip: hide the app shell (sidebar, header, toasts) without touching the layout. */
@media print {
  body * { visibility: hidden !important; }
  .payslip-print, .payslip-print * { visibility: visible !important; }
  .payslip-print {
    position: absolute; inset: 0 auto auto 0; width: 100%; max-width: none;
    margin: 0; border: 0; box-shadow: none; background: #fff; color: #000;
  }
  .no-print { display: none !important; }
  @page { margin: 16mm; }
}
</style>
