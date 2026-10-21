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
import { money, type Invoice, type InvoiceLine } from './finance'
const emit = defineEmits<{ changed: [] }>()
const STATUSES = ['draft', 'issued', 'paid', 'void']
const status = ref('all')
const table = useServerTable<Invoice>('finance/invoices/', {
  params: () => ({ status: status.value === 'all' ? undefined : status.value }),
})
const columns: Column<Invoice>[] = [
  { key: 'number', label: 'Invoice', sortable: true, class: 'whitespace-nowrap' },
  { key: 'client_name', label: 'Client', sortable: true, class: 'min-w-40' },
  { key: 'issue_date', label: 'Issued', sortable: true },
  { key: 'due_date', label: 'Due', sortable: true },
  { key: 'total', label: 'Total', class: 'text-right' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'actions', label: 'Actions', srOnly: true, class: 'text-right' },
]
function changed() {
  table.load()
  emit('changed')
}
onMounted(table.load)
const open = ref(false)
const editing = ref<Invoice | null>(null)
const busy = ref(false)
const error = ref('')
const form = reactive({
  number: '',
  client_name: '',
  client_email: '',
  issue_date: todayNPT(),
  due_date: '',
  currency: 'NPR',
  tax_amount: '0.00',
  notes: '',
  items: [{ description: '', quantity: '1.00', unit_price: '' }] as InvoiceLine[],
})
function edit(invoice?: Invoice) {
  editing.value = invoice || null
  error.value = ''
  Object.assign(form, {
    number: invoice?.number || '',
    client_name: invoice?.client_name || '',
    client_email: invoice?.client_email || '',
    issue_date: invoice?.issue_date || todayNPT(),
    due_date: invoice?.due_date || '',
    currency: invoice?.currency || 'NPR',
    tax_amount: invoice?.tax_amount || '0.00',
    notes: invoice?.notes || '',
    items: invoice
      ? invoice.items.map((i) => ({
          description: i.description,
          quantity: i.quantity,
          unit_price: i.unit_price,
        }))
      : [{ description: '', quantity: '1.00', unit_price: '' }],
  })
  open.value = true
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    if (editing.value) await api.patch(`finance/invoices/${editing.value.id}/`, form)
    else await api.post('finance/invoices/', form)
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
      <h2 class="text-lg font-medium">Client invoices</h2>
      <button class="btn-ink" @click="edit()">+ New invoice</button>
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
      caption="Client invoices"
      search-placeholder="Invoice number, client, or email…"
      empty-title="No invoices in this view"
      empty-hint="Add a client and line items to prepare your first invoice."
    >
          <template #toolbar>
            <label class="sr-only" for="inv-status">Invoice status</label>
            <select id="inv-status" v-model="status" class="input w-auto capitalize">
              <option value="all">All statuses</option>
              <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
            </select>
          </template>
      <template #cell-number="{ row }"><span class="readout text-xs text-flag">{{ row.number }}</span></template>
      <template #cell-client_name="{ row }">
        <span class="font-medium text-ink">{{ row.client_name }}</span>
        <span v-if="row.payment_reference" class="block text-xs text-ink/55">Payment: {{ row.payment_reference }}</span>
      </template>
      <template #cell-total="{ row }"><span class="readout">{{ money(row.total, row.currency) }}</span></template>
      <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
      <template #cell-actions="{ row }">
        <div class="flex flex-wrap items-start justify-end gap-2">
          <button class="btn-ghost btn-sm" :aria-label="'View invoice ' + row.number" @click="edit(row)">
            {{ row.status === 'draft' ? 'Review' : 'View' }}</button
          ><RecordActions resource="invoices" :id="row.id" :status="row.status" @changed="changed" />
        </div>
      </template>
    </DataTable>
    <Modal
      :open="open"
      :title="editing ? editing.number : 'New client invoice'"
      width="max-w-3xl"
      @close="open = false"
      ><form class="grid gap-4" @submit.prevent="save">
        <fieldset :disabled="!!editing && editing.status !== 'draft'" class="grid min-w-0 gap-4">
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="field"
              ><span class="ledger-label">Invoice number</span
              ><input v-model="form.number" class="input" maxlength="40" required /></label
            ><label class="field"
              ><span class="ledger-label">Client / organization</span
              ><input v-model="form.client_name" class="input" maxlength="200" required
            /></label>
          </div>
          <label class="field"
            ><span class="ledger-label">Client email</span
            ><input v-model="form.client_email" type="email" class="input"
          /></label>
          <div class="grid grid-cols-2 gap-3">
            <label class="field"
              ><span class="ledger-label">Issue date</span
              ><input v-model="form.issue_date" class="input" type="date" required /></label
            ><label class="field"
              ><span class="ledger-label">Due date</span
              ><input
                v-model="form.due_date"
                class="input"
                type="date"
                :min="form.issue_date"
                required
            /></label>
          </div>
          <fieldset class="grid min-w-0 gap-4">
            <legend class="ledger-label mb-3">Line items</legend>
            <div
              v-for="(item, index) in form.items"
              :key="index"
              class="grid gap-3 rounded-lg border border-ink/10 p-3 sm:grid-cols-[1fr_90px_130px_auto]"
            >
              <label class="field"
                ><span class="ledger-label">Description {{ index + 1 }}</span
                ><input v-model="item.description" required maxlength="500" class="input" /></label
              ><label class="field"
                ><span class="ledger-label">Quantity {{ index + 1 }}</span
                ><input
                  v-model="item.quantity"
                  type="number"
                  min="0.01"
                  max="999999.99"
                  step="0.01"
                  required
                  class="input" /></label
              ><label class="field"
                ><span class="ledger-label">Unit price {{ index + 1 }}</span
                ><input
                  v-model="item.unit_price"
                  type="number"
                  min="0"
                  max="9999999999.99"
                  step="0.01"
                  required
                  class="input" /></label
              ><button
                v-if="form.items.length > 1"
                type="button"
                class="self-end p-2 text-xs text-rust"
                :aria-label="'Remove line ' + (index + 1)"
                @click="form.items.splice(index, 1)"
              >
                Remove
              </button>
            </div>
            <button
              v-if="form.items.length < 100"
              type="button"
              class="btn-ghost justify-self-start"
              @click="form.items.push({ description: '', quantity: '1.00', unit_price: '' })"
            >
              + Add line
            </button>
          </fieldset>
          <div class="grid grid-cols-2 gap-3">
            <label class="field"
              ><span class="ledger-label">Manual tax amount</span
              ><input
                v-model="form.tax_amount"
                type="number"
                min="0"
                max="9999999999.99"
                step="0.01"
                required
                class="input" /></label
            ><label class="field"
              ><span class="ledger-label">Currency</span
              ><input
                v-model="form.currency"
                pattern="[A-Z]{3}"
                maxlength="3"
                class="input uppercase"
                required
            /></label>
          </div>
          <label class="field"
            ><span class="ledger-label">Notes / payment terms</span
            ><textarea v-model="form.notes" class="input" rows="3" />
          </label>
        </fieldset>
        <dl v-if="editing" class="grid grid-cols-3 gap-3 border-y border-ink/15 py-4">
          <div>
            <dt class="ledger-label">Saved subtotal</dt>
            <dd class="readout mt-2 text-sm">{{ money(editing.subtotal, editing.currency) }}</dd>
          </div>
          <div>
            <dt class="ledger-label">Tax amount</dt>
            <dd class="readout mt-2 text-sm">{{ money(editing.tax_amount, editing.currency) }}</dd>
          </div>
          <div>
            <dt class="ledger-label">Saved total</dt>
            <dd class="readout mt-2 text-sm">{{ money(editing.total, editing.currency) }}</dd>
          </div>
        </dl>
        <p class="text-xs text-ink/65">
          Line totals are rounded to two decimal places. Save the draft to review calculated totals.
        </p>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button
          v-if="!editing || editing.status === 'draft'"
          class="btn-ink justify-self-end"
          :disabled="busy"
        >
          {{ busy ? 'Saving…' : 'Save draft' }}
        </button>
      </form></Modal
    >
  </section>
</template>
