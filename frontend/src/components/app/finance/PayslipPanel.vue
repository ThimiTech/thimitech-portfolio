<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import RecordActions from './RecordActions.vue'
import DataTable, { type Column } from '../ui/DataTable.vue'
import StatusPill from '../ui/StatusPill.vue'
import LoadError from '../org/LoadError.vue'
import { useServerTable } from '../ui/serverTable'
import { errorMessage, todayNPT } from '../pm/pm'
import { money, type Salary, type Payslip } from './finance'
defineProps<{ salaries: Salary[] }>()
const emit = defineEmits<{ changed: [] }>()
const STATUSES = ['draft', 'issued', 'paid', 'void']
const status = ref('all')
const table = useServerTable<Payslip>('finance/payslips/', {
  params: () => ({ status: status.value === 'all' ? undefined : status.value }),
})
const columns: Column<Payslip>[] = [
  { key: 'employee_name', label: 'Employee', sortable: true, orderBy: 'employee__first_name', class: 'min-w-40' },
  { key: 'period', label: 'Month', sortable: true },
  { key: 'net', label: 'Net', class: 'text-right' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'actions', label: 'Actions', srOnly: true, class: 'text-right' },
]
function changed() {
  table.load()
  emit('changed')
}
onMounted(table.load)
const open = ref(false)
const selected = ref<Payslip | null>(null)
const busy = ref(false)
const error = ref('')
function openGenerator() {
  open.value = true
  error.value = ''
}
const generate = reactive({ salary: 0, month: todayNPT().slice(0, 7) })
const edit = reactive({ basic: '', allowances: '', deductions: '', notes: '' })
function view(s: Payslip) {
  selected.value = s
  Object.assign(edit, {
    basic: s.basic,
    allowances: s.allowances,
    deductions: s.deductions,
    notes: s.notes,
  })
  error.value = ''
}
async function create() {
  busy.value = true
  error.value = ''
  try {
    await api.post('finance/payslips/generate/', {
      salary: generate.salary,
      period: generate.month + '-01',
    })
    open.value = false
    changed()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    await api.patch(`finance/payslips/${selected.value!.id}/`, edit)
    selected.value = null
    changed()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <section>
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-lg font-medium">Monthly payslips</h2>
      <button class="btn-ink" @click="openGenerator">+ Generate payslip</button>
    </div>
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
      :row-key="(r) => r.id"
      caption="Payslips"
      search-placeholder="Employee name or email…"
      empty-title="No payslips in this view"
      empty-hint="Generate a draft from an active salary structure. Review deductions before issuing."
    >
          <template #toolbar>
            <label class="sr-only" for="pay-status">Payslip status</label>
            <select id="pay-status" v-model="status" class="input w-auto capitalize">
              <option value="all">All statuses</option>
              <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
            </select>
          </template>
      <template #cell-employee_name="{ row }">
        <span class="font-medium text-ink">{{ row.employee_name || 'Staff #' + row.employee }}</span>
        <span v-if="row.payment_reference" class="block text-xs text-ink/55">Payment: {{ row.payment_reference }}</span>
      </template>
      <template #cell-period="{ row }"><span class="readout text-xs">{{ row.period.slice(0, 7) }}</span></template>
      <template #cell-net="{ row }"><span class="readout">{{ money(row.net) }}</span></template>
      <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
      <template #cell-actions="{ row }">
        <div class="flex flex-wrap items-start justify-end gap-2">
          <button class="btn-ghost btn-sm" :aria-label="(row.status === 'draft' ? 'Review draft for ' : 'View payslip for ') + row.employee_name" @click="view(row)">
            {{ row.status === 'draft' ? 'Review' : 'View' }}</button
          ><RecordActions resource="payslips" :id="row.id" :status="row.status" @changed="changed" />
        </div>
      </template>
    </DataTable>
    <Modal :open="open" title="Generate monthly payslip" @close="open = false"
      ><form class="grid gap-4" @submit.prevent="create">
        <p class="text-sm text-ink/65">
          Copies the selected salary structure into a draft. Review any partial-month adjustments
          and manual deductions before issuing.
        </p>
        <label class="field"
          ><span class="ledger-label">Salary structure</span
          ><select v-model="generate.salary" class="input" required>
            <option :value="0" disabled>Select employee</option>
            <option v-for="s in salaries.filter((s) => s.active)" :key="s.id" :value="s.id">
              {{ s.employee_name }} · {{ money(s.net) }}
            </option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Payroll month</span
          ><input v-model="generate.month" type="month" class="input" required
        /></label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy || !generate.salary">
          {{ busy ? 'Generating…' : 'Generate draft' }}
        </button>
      </form></Modal
    >
    <Modal
      :open="!!selected"
      :title="selected ? selected.employee_name + ' · ' + selected.period.slice(0, 7) : 'Payslip'"
      @close="selected = null"
      ><form v-if="selected" class="grid gap-4" @submit.prevent="save">
        <p class="font-mono text-xs uppercase text-river">{{ selected.status }} · NPR</p>
        <label
          v-for="field in ['basic', 'allowances', 'deductions'] as const"
          :key="field"
          class="field"
          ><span class="ledger-label">{{ field }}</span
          ><input
            v-model="edit[field]"
            class="input"
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            required
            :readonly="selected.status !== 'draft'"
        /></label>
        <dl class="grid grid-cols-2 gap-3 border-y border-ink/15 py-4">
          <div>
            <dt class="ledger-label">Saved gross</dt>
            <dd class="readout mt-2">{{ money(selected.gross) }}</dd>
          </div>
          <div>
            <dt class="ledger-label">Saved net</dt>
            <dd class="readout mt-2">{{ money(selected.net) }}</dd>
          </div>
        </dl>
        <label class="field"
          ><span class="ledger-label">Notes</span
          ><textarea
            v-model="edit.notes"
            class="input"
            rows="3"
            :readonly="selected.status !== 'draft'"
          />
        </label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button
          v-if="selected.status === 'draft'"
          class="btn-ink justify-self-end"
          :disabled="busy"
        >
          {{ busy ? 'Saving…' : 'Save draft' }}
        </button>
      </form></Modal
    >
  </section>
</template>
