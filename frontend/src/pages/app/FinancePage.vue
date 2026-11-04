<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/api'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import TabBar from '@/components/app/ui/TabBar.vue'
import SkeletonBlock from '@/components/app/ui/SkeletonBlock.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import OverviewPanel from '@/components/app/finance/OverviewPanel.vue'
import LedgerPanel from '@/components/app/finance/LedgerPanel.vue'
import PayrollPanel from '@/components/app/finance/PayrollPanel.vue'
import ExpensePanel from '@/components/app/finance/ExpensePanel.vue'
import InvoicePanel from '@/components/app/finance/InvoicePanel.vue'
import ReportsPanel from '@/components/app/finance/ReportsPanel.vue'
import SetupPanel from '@/components/app/finance/SetupPanel.vue'
import { fiscalYear, loadLookups, type FiscalYear } from '@/components/app/finance/finance'

const route = useRoute()
const router = useRouter()
const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'ledger', label: 'Bank & cash' },
  { id: 'payroll', label: 'Payroll' },
  { id: 'claims', label: 'Staff claims' },
  { id: 'invoices', label: 'Invoices' },
  { id: 'reports', label: 'Reports & export' },
  { id: 'setup', label: 'Setup' },
]
const tab = computed({
  get: () => (TABS.some((t) => t.id === route.query.tab) ? String(route.query.tab) : 'overview'),
  set: (t: string) => router.replace({ query: { tab: t === 'overview' ? undefined : t } }),
})
const years = ref<FiscalYear[]>([])
const loading = ref(true)
const error = ref('')
const closed = computed(() => years.value.find((y) => y.name === fiscalYear.value)?.closed)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [{ data }] = await Promise.all([api.get<{ current: string; years: FiscalYear[] }>('finance/fiscal-years/'), loadLookups()])
    years.value = data.years
    if (!data.years.some((y) => y.name === fiscalYear.value)) fiscalYear.value = data.current
  } catch {
    error.value = 'Could not load the books. Please try again.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
/** Child panels jump here, e.g. Overview → "12 lines need review". */
function go(t: string, query: Record<string, string> = {}) {
  router.replace({ query: { tab: t, ...query } })
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Administration · Books" title="Finance"
      description="Bank and cash books, payroll with SSF and TDS, staff claims, invoices, and everything your CA needs.">
      <template #actions>
        <label class="sr-only" for="fin-fy">Fiscal year</label>
        <select id="fin-fy" v-model="fiscalYear" class="input w-auto font-mono text-sm" :disabled="loading">
          <option v-for="y in years" :key="y.name" :value="y.name">FY {{ y.name }}{{ y.closed ? ' · closed' : '' }}</option>
        </select>
      </template>
    </PageHeader>
    <TabBar v-model="tab" :tabs="TABS" label="Finance views" id-prefix="fin" class="mb-6" />
    <SkeletonBlock v-if="loading" :rows="4" height="h-16" label="Loading finance" />
    <LoadError v-else-if="error" :message="error" :busy="loading" @retry="load" />
    <div v-else :id="`fin-panel-${tab}`" role="tabpanel" :aria-labelledby="`fin-tab-${tab}`">
      <p v-if="closed && ['ledger', 'payroll'].includes(tab)" class="mb-4 rounded-lg border border-contour/40 bg-contour/10 px-4 py-2.5 text-sm text-contour-ink">
        FY {{ fiscalYear }} is closed. Its bank lines and statements are read-only.
      </p>
      <OverviewPanel v-if="tab === 'overview'" :fy="fiscalYear" @go="go" />
      <LedgerPanel v-else-if="tab === 'ledger'" :fy="fiscalYear" />
      <PayrollPanel v-else-if="tab === 'payroll'" :fy="fiscalYear" />
      <ExpensePanel v-else-if="tab === 'claims'" />
      <InvoicePanel v-else-if="tab === 'invoices'" />
      <ReportsPanel v-else-if="tab === 'reports'" :fy="fiscalYear" />
      <SetupPanel v-else :years="years" @changed="load" />
    </div>
  </div>
</template>
