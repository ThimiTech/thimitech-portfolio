<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/api'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import TabBar from '@/components/app/ui/TabBar.vue'
import EmptyState from '@/components/app/ui/EmptyState.vue'
import SkeletonBlock from '@/components/app/ui/SkeletonBlock.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import SalaryPanel from '@/components/app/finance/SalaryPanel.vue'
import PayslipPanel from '@/components/app/finance/PayslipPanel.vue'
import ExpensePanel from '@/components/app/finance/ExpensePanel.vue'
import InvoicePanel from '@/components/app/finance/InvoicePanel.vue'
import {
  money,
  type Salary,
  type Staff,
  type FinanceSummary,
} from '@/components/app/finance/finance'
const tab = ref('Overview')
const TABS = ['Overview', 'Salaries', 'Payslips', 'Expenses', 'Invoices'].map((id) => ({ id, label: id }))
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const salaries = ref<Salary[]>([])
const staff = ref<Staff[]>([])
const summary = ref<FinanceSummary | null>(null)
async function load(initial = false) {
  if (initial) loading.value = true
  refreshing.value = true
  error.value = ''
  try {
    // Salaries stay a full list (one per employee; the payslip generator needs them all).
    // Payslips, expenses and invoices are paged by their panels.
    const [s, people, totals] = await Promise.all([
      api.get<Salary[]>('finance/salaries/'),
      api.get<Staff[]>('org/people/', { params: { is_active: true } }),
      api.get<FinanceSummary>('finance/summary/'),
    ])
    salaries.value = s.data
    staff.value = people.data
    summary.value = totals.data
  } catch {
    error.value = 'Could not load finance records. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}
onMounted(() => load(true))
</script>
<template>
  <div>
    <PageHeader eyebrow="Administration · Finance" title="Finance" description="Monthly NPR payroll, expenses, and client invoices." />
    <TabBar v-model="tab" :tabs="TABS" label="Finance views" id-prefix="fin" class="mb-6" />
    <SkeletonBlock v-if="loading" :rows="4" height="h-16" label="Loading finance" />
    <LoadError v-else-if="error" :message="error" :busy="refreshing" @retry="load(true)" />
    <div v-else :id="`fin-panel-${tab}`" role="tabpanel" :aria-labelledby="`fin-tab-${tab}`" :aria-busy="refreshing">
      <section v-if="tab === 'Overview'" class="grid gap-6">
        <div class="grid grid-cols-2 gap-3">
          <div class="panel p-4">
            <p class="ledger-label">Draft payslips</p>
            <p class="readout mt-2 text-3xl">{{ summary?.draft_payslips }}</p>
          </div>
          <div class="panel p-4">
            <p class="ledger-label">Expenses awaiting review</p>
            <p class="readout mt-2 text-3xl">{{ summary?.submitted_expenses }}</p>
          </div>
        </div>
        <section v-for="total in summary?.currencies" :key="total.currency" class="panel p-5">
          <h2 class="font-medium">{{ total.currency }} · all recorded periods</h2>
          <dl class="mt-5 grid gap-6 sm:grid-cols-3">
            <div>
              <dt class="ledger-label">Payroll recorded paid</dt>
              <dd class="readout mt-2 text-lg">{{ money(total.payroll_paid, total.currency) }}</dd>
            </div>
            <div>
              <dt class="ledger-label">Approved / paid expenses</dt>
              <dd class="readout mt-2 text-lg">
                {{ money(total.expenses_approved, total.currency) }}
              </dd>
            </div>
            <div>
              <dt class="ledger-label">Issued invoices outstanding</dt>
              <dd class="readout mt-2 text-lg">
                {{ money(total.invoice_outstanding, total.currency) }}
              </dd>
            </div>
          </dl>
        </section>
        <div v-if="!summary?.currencies.length" class="panel">
          <EmptyState title="No totals yet" hint="Start with a salary structure, an expense, or an invoice. Totals appear when records are approved or issued." />
        </div>
      </section>
      <SalaryPanel
        v-else-if="tab === 'Salaries'"
        :salaries="salaries"
        :staff="staff"
        @changed="load()"
      />
      <PayslipPanel
        v-else-if="tab === 'Payslips'"
        :salaries="salaries"
        @changed="load()"
      />
      <ExpensePanel
        v-else-if="tab === 'Expenses'"
        :staff="staff"
        @changed="load()"
      />
      <InvoicePanel v-else @changed="load()" />
    </div>
  </div>
</template>
