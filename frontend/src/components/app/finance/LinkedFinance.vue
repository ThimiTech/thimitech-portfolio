<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/api/api'
import DocViewer from '../pm/DocViewer.vue'
import { fileSize, type Doc } from '../pm/pm'
import { asDoc, fileBadge, type Browse, type DriveFile } from '../drive/drive'
import { amount, dateLabel, monthLabel, type Expense, type Invoice, type Payslip, type Salary, type Txn } from './finance'

/** Everything financial linked to one person or one project, with jumps to the full registers. Finance roles only. */
const props = defineProps<{ employee?: number; project?: number }>()
const key = computed(() => (props.employee ? { employee: props.employee } : { project: props.project! }))
const qs = computed(() => new URLSearchParams(Object.entries(key.value).map(([k, v]) => [k, String(v)])).toString())
const totals = ref<{ entries: number; in: string; out: string; by_category: { name: string; in: string; out: string; entries: number }[] } | null>(null)
const recent = ref<Txn[]>([])
const salary = ref<Salary | null>(null)
const slips = ref<Payslip[]>([])
const claims = ref<Expense[]>([])
const invoices = ref<Invoice[]>([])
const files = ref<DriveFile[]>([])
const viewing = ref<Doc | null>(null)

onMounted(async () => {
  const p = key.value
  const page = <T,>(url: string, extra = {}) => api.get<{ results: T[] }>(url, { params: { ...p, page: 1, page_size: 8, ...extra } }).then((r) => r.data.results)
  const jobs: Promise<unknown>[] = [
    api.get('finance/transactions/totals/', { params: p }).then((r) => (totals.value = r.data)),
    page<Txn>('finance/transactions/', { ordering: '-date' }).then((r) => (recent.value = r)),
    page<Expense>('finance/expenses/', { ordering: '-date' }).then((r) => (claims.value = r)),
    api.get<Browse>('drive/browse/', { params: p }).then((r) => (files.value = r.data.files)),
  ]
  if (props.employee) {
    jobs.push(api.get<Salary[]>('finance/salaries/', { params: p }).then((r) => (salary.value = r.data[0] || null)))
    jobs.push(page<Payslip>('finance/payslips/', { ordering: '-period', page_size: 6 }).then((r) => (slips.value = r)))
  } else jobs.push(page<Invoice>('finance/invoices/').then((r) => (invoices.value = r)))
  await Promise.allSettled(jobs)
})
const owed = computed(() => claims.value.filter((c) => c.status === 'approved').reduce((s, c) => s + Number(c.amount), 0))
</script>

<template>
  <section class="grid gap-4" aria-label="Linked finance">
    <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="panel p-4"><p class="ledger-label">Money out</p><p class="readout mt-1 text-lg text-chart-out">{{ amount(totals?.out, 0) }}</p><p class="text-xs text-ink/50">{{ totals?.entries || 0 }} bank lines</p></div>
      <div class="panel p-4"><p class="ledger-label">Money in</p><p class="readout mt-1 text-lg text-chart-in">{{ amount(totals?.in, 0) }}</p></div>
      <div v-if="employee" class="panel p-4"><p class="ledger-label">Monthly pay</p><p class="readout mt-1 text-lg">{{ salary ? amount(salary.gross, 0) : '—' }}</p><p class="text-xs text-ink/50">{{ salary ? (salary.ssf_enrolled ? 'SSF enrolled' : '1% SST') + (salary.active ? '' : ' · inactive') : 'No salary structure' }}</p></div>
      <div v-else class="panel p-4"><p class="ledger-label">Invoiced</p><p class="readout mt-1 text-lg">{{ amount(invoices.reduce((s, i) => s + Number(i.total), 0), 0) }}</p><p class="text-xs text-ink/50">{{ invoices.length }} invoices</p></div>
      <div class="panel p-4"><p class="ledger-label">Claims {{ employee ? 'owed to them' : 'on this project' }}</p><p class="readout mt-1 text-lg">{{ amount(employee ? owed : claims.reduce((s, c) => s + Number(c.amount), 0), 0) }}</p><p class="text-xs text-ink/50">{{ claims.length }} claims</p></div>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <div class="panel p-4">
        <div class="mb-2 flex items-center justify-between"><p class="ledger-label">Recent bank lines</p><RouterLink :to="`/app/finance?tab=ledger&${qs}`" class="text-xs text-river hover:underline">All →</RouterLink></div>
        <ul class="divide-y divide-ink/10 text-sm">
          <li v-for="t in recent" :key="t.id" class="flex items-baseline justify-between gap-3 py-1.5">
            <span class="min-w-0 truncate">{{ dateLabel(t.date) }} · {{ t.category_name || t.description }}</span>
            <span class="readout shrink-0" :class="Number(t.credit) ? 'text-chart-in' : 'text-chart-out'">{{ amount(Number(t.credit) || -Number(t.debit)) }}</span>
          </li>
          <li v-if="!recent.length" class="py-1.5 text-ink/55">None linked yet.</li>
        </ul>
      </div>
      <div v-if="employee" class="panel p-4">
        <div class="mb-2 flex items-center justify-between"><p class="ledger-label">Payslips</p><RouterLink to="/app/finance?tab=payroll" class="text-xs text-river hover:underline">Payroll →</RouterLink></div>
        <ul class="divide-y divide-ink/10 text-sm">
          <li v-for="s in slips" :key="s.id" class="flex justify-between gap-3 py-1.5"><span>{{ monthLabel(s.period) }} · {{ s.status }}</span><span class="readout">{{ amount(s.net) }}</span></li>
          <li v-if="!slips.length" class="py-1.5 text-ink/55">No payslips.</li>
        </ul>
        <p v-if="salary?.bank_account" class="mt-2 text-xs text-ink/55">Pays to {{ salary.bank_name }} {{ salary.bank_account }}{{ salary.pan ? ' · PAN ' + salary.pan : '' }}</p>
      </div>
      <div v-else class="panel p-4">
        <div class="mb-2 flex items-center justify-between"><p class="ledger-label">Invoices</p><RouterLink to="/app/finance?tab=invoices" class="text-xs text-river hover:underline">Invoices →</RouterLink></div>
        <ul class="divide-y divide-ink/10 text-sm">
          <li v-for="i in invoices" :key="i.id" class="flex justify-between gap-3 py-1.5"><span>{{ i.number }} · {{ i.client_name }} · {{ i.status }}</span><span class="readout">{{ amount(i.total) }}</span></li>
          <li v-if="!invoices.length" class="py-1.5 text-ink/55">No invoices linked.</li>
        </ul>
      </div>
    </div>

    <div class="panel p-4">
      <div class="mb-2 flex items-center justify-between"><p class="ledger-label">Documents ({{ files.length }})</p><RouterLink :to="`/app/drive?${qs}`" class="text-xs text-river hover:underline">Open in Drive →</RouterLink></div>
      <ul class="grid gap-1.5 sm:grid-cols-2">
        <li v-for="f in files.slice(0, 10)" :key="f.id">
          <button type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-sm hover:bg-panel/60" @click="viewing = asDoc(f)">
            <span class="rounded bg-ink/[0.06] px-1.5 font-mono text-[10px]">{{ fileBadge(f.extension) }}</span><span class="min-w-0 flex-1 truncate">{{ f.name }}</span><span class="text-[11px] text-ink/45">{{ fileSize(f.size) }}</span>
          </button>
        </li>
        <li v-if="!files.length" class="text-sm text-ink/55">No documents linked.</li>
      </ul>
    </div>
    <DocViewer :doc="viewing" @close="viewing = null" />
  </section>
</template>
