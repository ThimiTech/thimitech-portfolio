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
import { money, staffName, type Expense, type Staff } from './finance'
defineProps<{ staff: Staff[] }>()
const emit = defineEmits<{ changed: [] }>()
const STATUSES = ['draft', 'submitted', 'approved', 'rejected', 'paid']
const status = ref('all')
const table = useServerTable<Expense>('finance/expenses/', {
  params: () => ({ status: status.value === 'all' ? undefined : status.value }),
})
const columns: Column<Expense>[] = [
  { key: 'description', label: 'Expense', class: 'min-w-48' },
  { key: 'employee_name', label: 'Claimant', sortable: true, orderBy: 'employee__first_name' },
  { key: 'date', label: 'Date', sortable: true },
  { key: 'amount', label: 'Amount', sortable: true, class: 'text-right' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'actions', label: 'Actions', srOnly: true, class: 'text-right' },
]
function changed() {
  table.load()
  emit('changed')
}
onMounted(table.load)
const open = ref(false)
const editing = ref<Expense | null>(null)
const busy = ref(false)
const error = ref('')
const form = reactive({
  employee: 0,
  description: '',
  date: todayNPT(),
  category: 'other',
  amount: '',
  currency: 'NPR',
  notes: '',
})
function edit(e?: Expense) {
  editing.value = e || null
  error.value = ''
  Object.assign(form, {
    employee: e?.employee || 0,
    description: e?.description || '',
    date: e?.date || todayNPT(),
    category: e?.category || 'other',
    amount: e?.amount || '',
    currency: e?.currency || 'NPR',
    notes: e?.notes || '',
  })
  open.value = true
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    if (editing.value) await api.patch(`finance/expenses/${editing.value.id}/`, form)
    else await api.post('finance/expenses/', form)
    open.value = false
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
      <h2 class="text-lg font-medium">Expense register</h2>
      <button class="btn-ink" @click="edit()">+ Record expense</button>
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
      caption="Expense register"
      search-placeholder="Description, category, or claimant…"
      empty-title="No expenses in this view"
      empty-hint="Record an expense, or change the status filter."
    >
          <template #toolbar>
            <label class="sr-only" for="exp-status">Expense status</label>
            <select id="exp-status" v-model="status" class="input w-auto capitalize">
              <option value="all">All statuses</option>
              <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
            </select>
          </template>
      <template #cell-description="{ row }">
        <span class="font-medium text-ink">{{ row.description }}</span>
        <span class="block text-xs capitalize text-ink/55">{{ row.category }}</span>
        <p v-if="row.notes" class="mt-1 text-xs whitespace-pre-wrap text-ink/60">{{ row.notes }}</p>
        <p v-if="row.decision_note" class="mt-1 text-xs text-ink/60">Decision: {{ row.decision_note }}</p>
        <p v-if="row.payment_reference" class="mt-1 text-xs text-ink/60">Payment: {{ row.payment_reference }}</p>
      </template>
      <template #cell-amount="{ row }"><span class="readout">{{ money(row.amount, row.currency) }}</span></template>
      <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
      <template #cell-actions="{ row }">
        <div class="flex flex-wrap items-start justify-end gap-2">
          <button
            v-if="['draft', 'rejected'].includes(row.status)"
            class="btn-ghost btn-sm"
            :aria-label="'Edit expense ' + row.description"
            @click="edit(row)"
          >Edit</button
          ><RecordActions resource="expenses" :id="row.id" :status="row.status" @changed="changed" />
        </div>
      </template>
    </DataTable>
    <Modal :open="open" :title="editing ? 'Edit expense' : 'Record expense'" @close="open = false"
      ><form class="grid gap-4" @submit.prevent="save">
        <label class="field"
          ><span class="ledger-label">Employee / claimant</span
          ><select v-model="form.employee" class="input" required>
            <option :value="0" disabled>Select staff member</option>
            <option v-for="p in staff" :key="p.id" :value="p.id">{{ staffName(p) }}</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Description</span
          ><input v-model="form.description" class="input" required maxlength="500"
        /></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"
            ><span class="ledger-label">Date</span
            ><input v-model="form.date" class="input" type="date" required /></label
          ><label class="field"
            ><span class="ledger-label">Category</span
            ><select v-model="form.category" class="input">
              <option v-for="c in ['travel', 'software', 'equipment', 'office', 'other']" :key="c">
                {{ c }}
              </option>
            </select></label
          >
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"
            ><span class="ledger-label">Amount</span
            ><input
              v-model="form.amount"
              class="input"
              type="number"
              min="0.01"
              max="9999999999.99"
              step="0.01"
              required /></label
          ><label class="field"
            ><span class="ledger-label">Currency</span
            ><input
              v-model="form.currency"
              class="input uppercase"
              pattern="[A-Z]{3}"
              maxlength="3"
              required
          /></label>
        </div>
        <label class="field"
          ><span class="ledger-label">Notes / receipt reference</span
          ><textarea v-model="form.notes" class="input" rows="3" />
        </label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy || !form.employee">
          {{ busy ? 'Saving…' : 'Save draft' }}
        </button>
      </form></Modal
    >
  </section>
</template>
