<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import StatusPill from '../ui/StatusPill.vue'
import { confirmDialog } from '../ui/confirm'
import { toast } from '../ui/toast'
import { errorMessage } from '../pm/pm'
import RecordActions from './RecordActions.vue'
import SalaryPanel from './SalaryPanel.vue'
import { amount, dateLabel, downloadFrom, lookups, monthLabel, type Payslip, type Salary, type Statutory } from './finance'

const props = defineProps<{ fy: string }>()
const month = ref(new Date().toISOString().slice(0, 7))
const slips = ref<Payslip[]>([])
const salaries = ref<Salary[]>([])
const dues = ref<Statutory | null>(null)
const busy = ref(false)
const workingDays = ref<number | ''>('')
const period = computed(() => month.value + '-01')

async function loadSlips() {
  slips.value = (await api.get<Payslip[]>('finance/payslips/', { params: { period: period.value } })).data
}
async function loadAll() {
  const [s, d] = await Promise.all([api.get<Salary[]>('finance/salaries/'), api.get<Statutory>('finance/reports/statutory/', { params: { fy: props.fy } })])
  salaries.value = s.data
  dues.value = d.data
}
onMounted(async () => {
  // open on the latest month that has payslips
  const { data } = await api
    .get<{ results: Payslip[] }>('finance/payslips/', { params: { page: 1, page_size: 1, ordering: '-period' } })
    .catch(() => ({ data: { results: [] as Payslip[] } }))
  if (data.results[0]) month.value = data.results[0].period.slice(0, 7)
  await Promise.all([loadSlips(), loadAll()]).catch(() => toast.error('Could not load payroll.'))
})
watch(month, () => loadSlips().catch(() => {}))
watch(() => props.fy, () => loadAll().catch(() => {}))

const totals = computed(() => {
  const t = { gross: 0, ssf: 0, tds: 0, other: 0, net: 0, er: 0, ctc: 0 }
  for (const s of slips.value.filter((x) => x.status !== 'void')) {
    t.gross += +s.gross; t.ssf += +s.ssf_employee; t.tds += +s.tds; t.other += +s.deductions; t.net += +s.net; t.er += +s.ssf_employer; t.ctc += +s.cost_to_company
  }
  return t
})
const drafts = computed(() => slips.value.filter((s) => s.status === 'draft').length)

async function run(action: string, body: object, done: (d: Record<string, unknown>) => string) {
  busy.value = true
  try {
    const { data } = await api.post(`finance/payslips/${action}/`, body)
    toast.success(done(data))
    await Promise.all([loadSlips(), loadAll()])
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
const generate = () => run('generate-month', { period: period.value, working_days: workingDays.value || null }, (d) =>
  `${d.created} draft payslips created.` + ((d.skipped as string[]).length ? ` Skipped: ${(d.skipped as string[]).join('; ')}` : ''))
async function issueAll() {
  if (!(await confirmDialog({ title: `Issue ${drafts.value} payslips?`, body: 'Staff are notified and amounts are locked.', confirmLabel: 'Issue' }))) return
  run('issue-month', { period: period.value }, (d) => `${d.issued} payslips issued; staff notified.`)
}
const match = () => run('match-payments', { period: period.value }, (d) => {
  const l = (d.linked as string[]).length, m = (d.missing as string[]).length, a = (d.ambiguous as string[]).length
  return `${l} matched to bank lines.` + (m ? ` ${m} not found in the bank yet.` : '') + (a ? ` ${a} ambiguous, link them from Bank & cash.` : '')
})
function exportSheet(type: 'xlsx' | 'csv') {
  downloadFrom('finance/export/', { what: 'payroll', type, period: period.value }).catch(() => toast.error('Export failed.'))
}

// ---- edit a draft
const editing = ref<Payslip | null>(null)
const form = reactive({ basic: '', allowances: '', bonus: '', working_days: null as number | null, days_worked: null as number | null, deductions: '', ssf_employee: '', ssf_employer: '', tds: '', notes: '', auto: true })
const error = ref('')
function edit(s: Payslip) {
  editing.value = s
  error.value = ''
  Object.assign(form, { basic: s.basic, allowances: s.allowances, bonus: s.bonus, working_days: s.working_days, days_worked: s.days_worked, deductions: s.deductions,
    ssf_employee: s.ssf_employee, ssf_employer: s.ssf_employer, tds: s.tds, notes: s.notes, auto: true })
}
async function save() {
  const { auto, ssf_employee, ssf_employer, tds, ...rest } = form
  try {
    await api.patch(`finance/payslips/${editing.value!.id}/`, auto ? { ...rest, recalculate: true } : { ...rest, ssf_employee, ssf_employer, tds })
    editing.value = null
    await loadSlips()
  } catch (e) {
    error.value = errorMessage(e)
  }
}
const salaryChanged = () => loadAll().catch(() => {})
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)] gap-8">
    <section>
      <div class="mb-4 flex flex-wrap items-end gap-3">
        <div>
          <h2 class="text-lg font-medium">Salary sheet</h2>
          <p class="text-sm text-ink/60">{{ monthLabel(period) }} · SSF members: 11% from pay + 20% by company, no SST. Others: 1% SST.</p>
        </div>
        <span class="flex-1" />
        <label class="field"><span class="ledger-label">Month</span><input v-model="month" type="month" class="input w-auto" /></label>
        <label class="field"><span class="ledger-label">Working days</span><input v-model.number="workingDays" type="number" min="1" max="31" class="input w-24" placeholder="full" /></label>
        <button class="btn-ink" :disabled="busy" @click="generate">Generate drafts</button>
        <button class="btn-ghost" :disabled="busy || !drafts" @click="issueAll">Issue {{ drafts || '' }} drafts</button>
        <button class="btn-ghost" :disabled="busy || !slips.length" @click="match">Match bank payments</button>
        <button class="btn-ghost btn-sm" :disabled="!slips.length" @click="exportSheet('xlsx')">Excel</button>
      </div>
      <div class="panel relative overflow-x-auto">
        <table class="ledger-table text-[13px]">
          <thead>
            <tr>
              <th>Employee</th><th class="text-right">Basic</th><th class="text-right">Allow.</th><th class="text-right">Bonus</th><th class="text-right">Days</th>
              <th class="text-right">Gross</th><th class="text-right">SSF 11%</th><th class="text-right">TDS</th><th class="text-right">Other</th>
              <th class="text-right">Net pay</th><th class="text-right">Co. SSF 20%</th><th>Status</th><th><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in slips" :key="s.id" :class="s.status === 'void' && 'opacity-50'">
              <td class="min-w-48">
                <span class="block font-medium text-ink">{{ s.employee_name }}</span>
                <span class="block text-xs text-ink/55">{{ [s.employee_meta.designation, s.employee_meta.bank_name, s.employee_meta.bank_account].filter(Boolean).join(' · ') || '—' }}</span>
                <span v-if="s.employee_meta.pan" class="block text-xs text-ink/55">PAN {{ s.employee_meta.pan }}</span>
              </td>
              <td class="readout text-right">{{ amount(s.basic, 0) }}</td>
              <td class="readout text-right">{{ amount(s.allowances, 0) }}</td>
              <td class="readout text-right">{{ Number(s.bonus) ? amount(s.bonus, 0) : '' }}</td>
              <td class="readout text-right">{{ s.working_days ? `${s.days_worked}/${s.working_days}` : '' }}</td>
              <td class="readout text-right">{{ amount(s.gross) }}</td>
              <td class="readout text-right">{{ Number(s.ssf_employee) ? amount(s.ssf_employee) : '' }}</td>
              <td class="readout text-right">{{ Number(s.tds) ? amount(s.tds) : '' }}</td>
              <td class="readout text-right">{{ Number(s.deductions) ? amount(s.deductions) : '' }}</td>
              <td class="readout text-right font-medium text-ink">{{ amount(s.net) }}</td>
              <td class="readout text-right text-ink/60">{{ Number(s.ssf_employer) ? amount(s.ssf_employer) : '' }}</td>
              <td>
                <StatusPill :status="s.status" />
                <span v-if="s.transaction_ids.length" class="mt-1 block text-[11px] text-moss">bank line linked</span>
              </td>
              <td><div class="flex justify-end gap-2">
                <button v-if="s.status === 'draft'" class="btn-ghost btn-sm" @click="edit(s)">Edit</button>
                <RecordActions resource="payslips" :id="s.id" :status="s.status" @changed="loadSlips" />
              </div></td>
            </tr>
            <tr v-if="!slips.length"><td colspan="13" class="py-8 text-center text-ink/60">No payslips for {{ monthLabel(period) }}. Generate drafts from the salary structures below.</td></tr>
          </tbody>
          <tfoot v-if="slips.length" class="font-medium">
            <tr>
              <td>Total · cost to company {{ amount(totals.ctc, 0) }}</td><td colspan="4" />
              <td class="readout text-right">{{ amount(totals.gross) }}</td><td class="readout text-right">{{ amount(totals.ssf) }}</td>
              <td class="readout text-right">{{ amount(totals.tds) }}</td><td class="readout text-right">{{ amount(totals.other) }}</td>
              <td class="readout text-right">{{ amount(totals.net) }}</td><td class="readout text-right">{{ amount(totals.er) }}</td><td colspan="2" />
            </tr>
          </tfoot>
        </table>
      </div>
    </section>

    <section v-if="dues">
      <h2 class="text-lg font-medium">TDS and SSF dues · FY {{ fy }}</h2>
      <p class="mb-4 text-sm text-ink/60">Deposit TDS to IRD by the 25th and SSF by the 15th of the next Nepali month. Record each deposit in Bank &amp; cash under "TDS deposit" or "SSF contribution".</p>
      <div class="mb-4 grid gap-3 sm:grid-cols-2">
        <div v-for="k in (['tds', 'ssf'] as const)" :key="k" class="panel p-4">
          <p class="ledger-label">{{ k === 'tds' ? 'TDS (IRD)' : 'SSF (11% + 20%)' }}</p>
          <p class="readout mt-2 text-xl" :class="Number(dues.totals[k].outstanding) > 0 ? 'text-rust' : 'text-moss'">{{ amount(dues.totals[k].outstanding) }} outstanding</p>
          <p class="mt-1 text-xs text-ink/55">Withheld {{ amount(dues.totals[k].accrued) }} · deposited {{ amount(dues.totals[k].deposited) }}</p>
        </div>
      </div>
      <div v-if="dues.months.length" class="panel relative overflow-x-auto">
        <table class="ledger-table text-[13px]">
          <thead><tr><th>Payroll month</th><th class="text-right">TDS</th><th>TDS due</th><th class="text-right">SSF employee</th><th class="text-right">SSF company</th><th class="text-right">SSF total</th><th>SSF due</th></tr></thead>
          <tbody>
            <tr v-for="m in dues.months" :key="m.period">
              <td>{{ monthLabel(m.period) }}</td>
              <td class="readout text-right">{{ amount(m.tds) }}</td><td class="whitespace-nowrap">{{ Number(m.tds) ? dateLabel(m.tds_due) : '' }}</td>
              <td class="readout text-right">{{ amount(m.ssf_employee) }}</td><td class="readout text-right">{{ amount(m.ssf_employer) }}</td>
              <td class="readout text-right">{{ amount(m.ssf_total) }}</td><td class="whitespace-nowrap">{{ Number(m.ssf_total) ? dateLabel(m.ssf_due) : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <SalaryPanel :salaries="salaries" :staff="lookups.staff" @changed="salaryChanged" />

    <Modal :open="!!editing" :title="editing ? `Payslip · ${editing.employee_name} · ${monthLabel(editing.period)}` : ''" @close="editing = null">
      <form class="grid gap-3" @submit.prevent="save">
        <div class="grid grid-cols-3 gap-3">
          <label class="field"><span class="ledger-label">Basic</span><input v-model="form.basic" type="number" step="0.01" min="0" class="input readout" required /></label>
          <label class="field"><span class="ledger-label">Allowances</span><input v-model="form.allowances" type="number" step="0.01" min="0" class="input readout" required /></label>
          <label class="field"><span class="ledger-label">Bonus</span><input v-model="form.bonus" type="number" step="0.01" min="0" class="input readout" /></label>
          <label class="field"><span class="ledger-label">Working days</span><input v-model.number="form.working_days" type="number" min="1" max="31" class="input" /></label>
          <label class="field"><span class="ledger-label">Days worked</span><input v-model.number="form.days_worked" type="number" min="0" max="31" class="input" /></label>
          <label class="field"><span class="ledger-label">Other deductions</span><input v-model="form.deductions" type="number" step="0.01" min="0" class="input readout" /></label>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.auto" type="checkbox" class="accent-ink" /> Work out SSF and TDS automatically</label>
        <div v-if="!form.auto" class="grid grid-cols-3 gap-3">
          <label class="field"><span class="ledger-label">SSF employee</span><input v-model="form.ssf_employee" type="number" step="0.01" min="0" class="input readout" /></label>
          <label class="field"><span class="ledger-label">SSF company</span><input v-model="form.ssf_employer" type="number" step="0.01" min="0" class="input readout" /></label>
          <label class="field"><span class="ledger-label">TDS</span><input v-model="form.tds" type="number" step="0.01" min="0" class="input readout" /></label>
        </div>
        <label class="field"><span class="ledger-label">Notes on the slip</span><textarea v-model="form.notes" class="input" rows="2" /></label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end">Save draft</button>
      </form>
    </Modal>
  </div>
</template>
