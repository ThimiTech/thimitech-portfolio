<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import api from '@/api/api'
import SkeletonBlock from '../ui/SkeletonBlock.vue'
import LoadError from '../org/LoadError.vue'
import MoneyChart from './MoneyChart.vue'
import { amount, KIND_LABEL, type Overview } from './finance'

const props = defineProps<{ fy: string }>()
const emit = defineEmits<{ go: [tab: string, query?: Record<string, string>] }>()
const data = ref<Overview | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get<Overview>('finance/reports/overview/', { params: { fy: props.fy } })).data
  } catch {
    error.value = 'Could not load the overview.'
  } finally {
    loading.value = false
  }
}
watch(() => props.fy, load, { immediate: true })

const owed = computed(() => (data.value?.owed_to_staff || []).reduce((s, r) => s + Number(r.amount), 0))
/** Things someone should do, most urgent first. Empty = books are tidy. */
const todo = computed(() => {
  const d = data.value
  if (!d) return []
  const out: { text: string; action: string; tab: string; query?: Record<string, string>; tone: string }[] = []
  if (d.to_review) out.push({ text: `${d.to_review} bank line${d.to_review > 1 ? 's' : ''} need a category, a person or a check`, action: 'Review', tab: 'ledger', query: { status: 'review' }, tone: 'contour' })
  if (d.claims_waiting) out.push({ text: `${d.claims_waiting} staff claim${d.claims_waiting > 1 ? 's' : ''} waiting for a decision`, action: 'Decide', tab: 'claims', tone: 'contour' })
  if (Number(d.statutory.tds.outstanding) > 0) out.push({ text: `TDS of Rs ${amount(d.statutory.tds.outstanding)} withheld but not yet recorded as deposited`, action: 'See dues', tab: 'payroll', tone: 'rust' })
  if (Number(d.statutory.ssf.outstanding) > 0) out.push({ text: `SSF of Rs ${amount(d.statutory.ssf.outstanding)} (11% + 20%) not yet recorded as deposited`, action: 'See dues', tab: 'payroll', tone: 'rust' })
  if (owed.value > 0) out.push({ text: `Rs ${amount(owed.value)} owed to staff for approved claims`, action: 'Pay', tab: 'claims', tone: 'sky' })
  return out
})
const TONE: Record<string, string> = { contour: 'bg-contour', rust: 'bg-rust', sky: 'bg-sky' }
const chartRows = computed(() => (data.value?.months || []).map((m) => ({ label: m.label, in: Number(m.in), out: Number(m.out) })))
const spend = computed(() => {
  const rows = (data.value?.categories || []).filter((c) => Number(c.out) > 0 && c.kind !== 'transfer')
  const top = rows.slice(0, 8)
  const rest = rows.slice(8).reduce((s, c) => s + Number(c.out), 0)
  const list = top.map((c) => ({ name: c.name, value: Number(c.out), kind: c.kind }))
  if (rest) list.push({ name: `Other (${rows.length - 8} categories)`, value: rest, kind: 'expense' })
  return list
})
const spendMax = computed(() => Math.max(1, ...spend.value.map((s) => s.value)))
</script>

<template>
  <SkeletonBlock v-if="loading && !data" :rows="5" height="h-20" label="Loading overview" />
  <LoadError v-else-if="error" :message="error" :busy="loading" @retry="load" />
  <div v-else-if="data" class="grid grid-cols-[minmax(0,1fr)] gap-6" :aria-busy="loading">
    <section v-if="todo.length" class="panel divide-y divide-ink/10" aria-label="Needs attention">
      <div v-for="t in todo" :key="t.text" class="flex flex-wrap items-center gap-3 px-5 py-3">
        <span class="h-2 w-2 shrink-0 rounded-full" :class="TONE[t.tone]" aria-hidden="true" />
        <p class="min-w-0 flex-1 text-sm text-ink">{{ t.text }}</p>
        <button type="button" class="btn-ghost btn-sm" @click="emit('go', t.tab, t.query)">{{ t.action }} →</button>
      </div>
    </section>
    <p v-else class="panel px-5 py-3 text-sm text-moss">Books are tidy for FY {{ data.fy }}: nothing to review, no claims waiting, statutory dues recorded.</p>

    <section class="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Key figures">
      <div class="panel p-4">
        <p class="ledger-label">Cash now</p>
        <p class="readout mt-2 text-2xl text-ink">{{ amount(data.cash, 0) }}</p>
        <p class="mt-1 text-xs text-ink/55">NPR across active accounts</p>
      </div>
      <div class="panel p-4">
        <p class="ledger-label">Income · FY {{ data.fy }}</p>
        <p class="readout mt-2 text-2xl text-ink">{{ amount(data.income, 0) }}</p>
        <p class="mt-1 text-xs text-ink/55">Receivable: {{ amount(data.receivable, 0) }}</p>
      </div>
      <div class="panel p-4">
        <p class="ledger-label">Spent · FY {{ data.fy }}</p>
        <p class="readout mt-2 text-2xl text-ink">{{ amount(Number(data.spent) + Number(data.claims_spent), 0) }}</p>
        <p class="mt-1 text-xs text-ink/55">Bank {{ amount(data.spent, 0) }} · staff-paid {{ amount(data.claims_spent, 0) }}</p>
      </div>
      <div class="panel p-4">
        <p class="ledger-label">Runway</p>
        <p class="readout mt-2 text-2xl text-ink">{{ data.runway_months === null ? '—' : data.runway_months + ' mo' }}</p>
        <p class="mt-1 text-xs text-ink/55">Burn {{ amount(data.monthly_burn, 0) }} / month (last 3 months)</p>
      </div>
    </section>

    <MoneyChart :title="`Money in and out by month · FY ${data.fy}`" :rows="chartRows" :filename="`thimitech-cashflow-FY${data.fy.replace('/', '-')}`" />

    <div class="grid gap-6 lg:grid-cols-2">
      <section class="panel p-5">
        <h3 class="mb-4 font-medium text-ink">Where the money went</h3>
        <p v-if="!spend.length" class="text-sm text-ink/60">No spending recorded in this fiscal year.</p>
        <ul class="grid gap-3">
          <li v-for="s in spend" :key="s.name">
            <div class="flex items-baseline justify-between gap-3 text-sm">
              <span class="min-w-0 truncate text-ink">{{ s.name }} <span class="text-xs text-ink/45">· {{ KIND_LABEL[s.kind as keyof typeof KIND_LABEL] || s.kind }}</span></span>
              <span class="readout shrink-0 text-ink/80">{{ amount(s.value, 0) }}</span>
            </div>
            <div class="mt-1.5 h-1.5 rounded-full bg-ink/[0.06]"><div class="h-1.5 rounded-full bg-chart-out" :style="{ width: (s.value / spendMax) * 100 + '%' }" /></div>
          </li>
        </ul>
        <p v-if="data.kinds.uncategorized.out !== '0.00'" class="mt-4 text-xs text-ink/60">
          Rs {{ amount(data.kinds.uncategorized.out, 0) }} out is not categorised yet.
          <button type="button" class="text-river underline" @click="emit('go', 'ledger', { category: 'none' })">Categorise</button>
        </p>
      </section>

      <section class="grid content-start gap-6">
        <div class="panel p-5">
          <h3 class="mb-3 font-medium text-ink">Accounts</h3>
          <ul class="divide-y divide-ink/10">
            <li v-for="a in data.accounts" :key="a.id" class="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
              <button type="button" class="min-w-0 text-left text-sm text-ink hover:underline" @click="emit('go', 'ledger', { account: String(a.id) })">
                {{ a.name }} <span v-if="!a.active" class="text-xs text-ink/45">· inactive</span>
              </button>
              <span class="readout text-sm">{{ a.currency }} {{ amount(a.balance) }}</span>
              <span class="w-full text-xs text-ink/55">FY in {{ amount(a.fy_in, 0) }} · out {{ amount(a.fy_out, 0) }} · {{ a.entries }} lines</span>
            </li>
          </ul>
          <p v-if="!data.accounts.length" class="text-sm text-ink/60">Add your bank account under Setup to start the books.</p>
        </div>
        <div class="panel p-5">
          <h3 class="mb-3 font-medium text-ink">Payroll · FY {{ data.fy }} <span class="text-xs font-normal text-ink/50">({{ data.payroll.slips }} payslips)</span></h3>
          <dl class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <dt class="text-ink/60">Gross pay</dt><dd class="readout text-right">{{ amount(data.payroll.gross) }}</dd>
            <dt class="text-ink/60">Net paid to staff</dt><dd class="readout text-right">{{ amount(data.payroll.net) }}</dd>
            <dt class="text-ink/60">SSF (employee 11%)</dt><dd class="readout text-right">{{ amount(data.payroll.ssf_employee) }}</dd>
            <dt class="text-ink/60">SSF (company 20%)</dt><dd class="readout text-right">{{ amount(data.payroll.ssf_employer) }}</dd>
            <dt class="text-ink/60">TDS withheld</dt><dd class="readout text-right">{{ amount(data.payroll.tds) }}</dd>
            <dt class="font-medium text-ink">Cost to company</dt><dd class="readout text-right font-medium">{{ amount(data.payroll.cost) }}</dd>
          </dl>
        </div>
        <div v-if="data.owed_to_staff.length" class="panel p-5">
          <h3 class="mb-3 font-medium text-ink">Owed to staff (approved claims)</h3>
          <ul class="grid gap-1.5 text-sm">
            <li v-for="o in data.owed_to_staff" :key="o.employee" class="flex justify-between gap-3">
              <span>{{ o.name }} <span class="text-xs text-ink/50">· {{ o.claims }} claims</span></span><span class="readout">{{ amount(o.amount) }}</span>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </div>
</template>
