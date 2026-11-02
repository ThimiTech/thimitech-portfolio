<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { confirmDialog } from '../ui/confirm'
import { toast } from '../ui/toast'
import { errorMessage, todayNPT } from '../pm/pm'
import RecordFiles from './RecordFiles.vue'
import { amount, categoriesByKind, lookups, staffName, type Invoice, type Payslip, type Txn } from './finance'

const props = defineProps<{ open: boolean; txn: Txn | null; defaultAccount?: number }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const blank = () => ({
  account: props.defaultAccount || lookups.accounts.find((a) => a.active)?.id || 0,
  date: todayNPT(),
  direction: 'out' as 'in' | 'out',
  amount: '',
  description: '',
  party: '',
  reference: '',
  category: null as number | null,
  note: '',
  checked: true,
  employee: null as number | null,
  project: null as number | null,
  payslip: null as number | null,
  invoice: null as number | null,
})
const form = reactive(blank())
const busy = ref(false)
const error = ref('')
const parties = ref<string[]>([])
const payslips = ref<Payslip[]>([])
const invoices = ref<Invoice[]>([])

watch(
  () => props.open,
  (open) => {
    if (!open) return
    error.value = ''
    const t = props.txn
    Object.assign(form, blank(), t ? {
      account: t.account, date: t.date, direction: Number(t.credit) > 0 ? 'in' : 'out', amount: Number(t.credit) > 0 ? t.credit : t.debit,
      description: t.description, party: t.party, reference: t.reference, category: t.category, note: t.note, checked: t.status === 'confirmed',
      employee: t.employee, project: t.project, payslip: t.payslip, invoice: t.invoice,
    } : {})
    if (!parties.value.length) api.get<string[]>('finance/transactions/parties/').then((r) => (parties.value = r.data)).catch(() => {})
    api.get<Invoice[]>('finance/invoices/').then((r) => (invoices.value = r.data)).catch(() => {})
  },
)
watch(() => [props.open, form.employee], () => {
  payslips.value = []
  if (props.open && form.employee) api.get<Payslip[]>('finance/payslips/', { params: { employee: form.employee } }).then((r) => (payslips.value = r.data)).catch(() => {})
})
const groups = computed(() => categoriesByKind(lookups.categories))
const kind = computed(() => lookups.categories.find((c) => c.id === form.category)?.kind)
const currency = computed(() => lookups.accounts.find((a) => a.id === form.account)?.currency || 'NPR')

async function save() {
  busy.value = true
  error.value = ''
  const body = {
    account: form.account, date: form.date, description: form.description || form.party || 'Entry', party: form.party, reference: form.reference,
    category: form.category, note: form.note, status: form.checked ? 'confirmed' : 'review', employee: form.employee, project: form.project,
    payslip: form.payslip, invoice: form.invoice,
    debit: form.direction === 'out' ? form.amount : '0', credit: form.direction === 'in' ? form.amount : '0',
  }
  try {
    if (props.txn) await api.patch(`finance/transactions/${props.txn.id}/`, body)
    else await api.post('finance/transactions/', body)
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function remove() {
  if (!props.txn || !(await confirmDialog({ title: 'Delete this line?', body: 'Only delete lines entered by mistake. Bank lines should match the statement.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`finance/transactions/${props.txn.id}/`)
    toast.success('Line deleted')
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <Modal :open="open" :title="txn ? 'Bank / cash line' : 'Add entry'" width="max-w-2xl" @close="emit('close')">
    <form class="grid gap-4" @submit.prevent="save">
      <div class="grid grid-cols-2 gap-3">
        <div class="col-span-2 flex rounded-lg border border-ink/15 p-1" role="radiogroup" aria-label="Direction">
          <button v-for="d in (['out', 'in'] as const)" :key="d" type="button" role="radio" :aria-checked="form.direction === d"
            class="flex-1 rounded-md px-3 py-1.5 text-sm transition" :class="form.direction === d ? (d === 'out' ? 'bg-chart-out text-on-accent' : 'bg-chart-in text-on-accent') : 'text-ink/70'"
            @click="form.direction = d">{{ d === 'out' ? 'Money out (paid)' : 'Money in (received)' }}</button>
        </div>
        <label class="field"><span class="ledger-label">Account</span>
          <select v-model.number="form.account" class="input" required>
            <option v-for="a in lookups.accounts" :key="a.id" :value="a.id">{{ a.name }} ({{ a.currency }})</option>
          </select></label>
        <label class="field"><span class="ledger-label">Amount ({{ currency }})</span>
          <input v-model="form.amount" class="input readout" type="number" min="0.01" step="0.01" required /></label>
        <label class="field"><span class="ledger-label">Date</span><input v-model="form.date" type="date" class="input" required /></label>
        <label class="field"><span class="ledger-label">{{ form.direction === 'out' ? 'Paid to' : 'Received from' }}</span>
          <input v-model="form.party" class="input" list="fin-parties" maxlength="200" placeholder="Person, company or bank" />
          <datalist id="fin-parties"><option v-for="p in parties" :key="p" :value="p" /></datalist></label>
        <label class="field col-span-2"><span class="ledger-label">Description (as on the statement)</span>
          <input v-model="form.description" class="input" maxlength="500" /></label>
        <label class="field"><span class="ledger-label">Category</span>
          <select v-model="form.category" class="input">
            <option :value="null">Not sure yet</option>
            <optgroup v-for="g in groups" :key="g.kind" :label="g.label">
              <option v-for="c in g.items" :key="c.id" :value="c.id">{{ c.name }}</option>
            </optgroup>
          </select></label>
        <label class="field"><span class="ledger-label">Reference / cheque no.</span><input v-model="form.reference" class="input" maxlength="120" /></label>
      </div>

      <fieldset class="grid gap-3 rounded-lg border border-ink/10 p-3">
        <legend class="ledger-label px-1">Who or what is it for?</legend>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="text-xs text-ink/60">Person</span>
            <select v-model="form.employee" class="input"><option :value="null">—</option>
              <option v-for="p in lookups.staff" :key="p.id" :value="p.id">{{ staffName(p) }}</option></select></label>
          <label class="field"><span class="text-xs text-ink/60">Project</span>
            <select v-model="form.project" class="input"><option :value="null">—</option>
              <option v-for="p in lookups.projects" :key="p.id" :value="p.id">{{ p.name }}</option></select></label>
          <label v-if="form.employee && (kind === 'payroll' || form.payslip)" class="field"><span class="text-xs text-ink/60">Pays payslip</span>
            <select v-model="form.payslip" class="input"><option :value="null">—</option>
              <option v-for="s in payslips" :key="s.id" :value="s.id">{{ s.period.slice(0, 7) }} · net {{ amount(s.net) }} · {{ s.status }}</option></select></label>
          <label v-if="form.direction === 'in' || form.invoice" class="field"><span class="text-xs text-ink/60">Settles invoice</span>
            <select v-model="form.invoice" class="input"><option :value="null">—</option>
              <option v-for="i in invoices" :key="i.id" :value="i.id">{{ i.number }} · {{ i.client_name }} · {{ amount(i.total) }}</option></select></label>
        </div>
      </fieldset>

      <label class="field"><span class="ledger-label">Note</span><textarea v-model="form.note" class="input" rows="2" placeholder="What it was for, who approved it…" /></label>
      <label class="flex items-center gap-2 text-sm"><input v-model="form.checked" type="checkbox" class="accent-ink" /> Checked: category and details are correct</label>

      <div v-if="txn" class="rounded-lg border border-ink/10 p-3">
        <p class="ledger-label mb-2">Receipts & documents</p>
        <RecordFiles :link="{ transaction: txn.id }" :folder="`Transactions/FY ${txn.fiscal_year.replace('/', '-')}`" :fiscal-year="txn.fiscal_year" />
      </div>
      <p v-else class="text-xs text-ink/55">Save first, then attach receipts or transfer slips.</p>

      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <div class="flex flex-wrap justify-between gap-2">
        <button v-if="txn" type="button" class="btn-danger btn-sm" @click="remove">Delete</button><span v-else />
        <button class="btn-ink" :disabled="busy || !form.account || !form.amount">{{ busy ? 'Saving…' : 'Save' }}</button>
      </div>
    </form>
  </Modal>
</template>
