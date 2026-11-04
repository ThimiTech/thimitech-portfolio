<script setup lang="ts">
import { reactive, ref } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { confirmDialog } from '../ui/confirm'
import { toast } from '../ui/toast'
import { errorMessage, todayNPT } from '../pm/pm'
import { useAuth } from '@/stores/auth'
import { amount, dateLabel, KIND_LABEL, KINDS, loadLookups, lookups, type Account, type Category, type FiscalYear } from './finance'

defineProps<{ years: FiscalYear[] }>()
const emit = defineEmits<{ changed: [] }>()
const { hasRole } = useAuth()
const error = ref('')

// ---- accounts
const acctOpen = ref(false)
const acctId = ref<number | null>(null)
const acct = reactive({ name: '', kind: 'bank', institution: '', number: '', currency: 'NPR', opening_balance: '0', opening_date: todayNPT(), active: true, notes: '' })
function editAccount(a?: Account) {
  acctId.value = a?.id ?? null
  error.value = ''
  Object.assign(acct, a ? { ...a } : { name: '', kind: 'bank', institution: '', number: '', currency: 'NPR', opening_balance: '0', opening_date: todayNPT(), active: true, notes: '' })
  acctOpen.value = true
}
async function saveAccount() {
  try {
    if (acctId.value) await api.patch(`finance/accounts/${acctId.value}/`, acct)
    else await api.post('finance/accounts/', acct)
    acctOpen.value = false
    await loadLookups()
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
  }
}

// ---- categories
const catOpen = ref(false)
const catId = ref<number | null>(null)
const cat = reactive({ name: '', kind: 'expense', description: '', active: true })
function editCategory(c?: Category) {
  catId.value = c?.id ?? null
  error.value = ''
  Object.assign(cat, c ? { name: c.name, kind: c.kind, description: c.description, active: c.active } : { name: '', kind: 'expense', description: '', active: true })
  catOpen.value = true
}
async function saveCategory() {
  try {
    if (catId.value) await api.patch(`finance/categories/${catId.value}/`, cat)
    else await api.post('finance/categories/', cat)
    catOpen.value = false
    await loadLookups()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

// ---- fiscal years
async function closeYear(y: FiscalYear) {
  if (!(await confirmDialog({ title: `Close FY ${y.name}?`, body: 'Bank lines and statements in this year become read-only. A super admin can reopen it.', confirmLabel: 'Close year' }))) return
  try {
    await api.post('finance/fiscal-years/', { name: y.name })
    toast.success(`FY ${y.name} closed`)
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function reopen(y: FiscalYear) {
  if (!y.close || !(await confirmDialog({ title: `Reopen FY ${y.name}?`, body: 'Its books become editable again. Close it again after the changes.', confirmLabel: 'Reopen' }))) return
  try {
    await api.delete(`finance/fiscal-years/${y.close.id}/`)
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const today = todayNPT()
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)] gap-8">
    <section>
      <div class="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-medium">Accounts</h2>
          <p class="text-sm text-ink/60">Bank accounts, petty cash, cards and wallets. The opening balance is the balance at the start of the opening date.</p>
        </div>
        <button class="btn-ink" @click="editAccount()">+ Account</button>
      </div>
      <div class="panel relative overflow-x-auto">
        <table class="ledger-table">
          <thead><tr><th>Account</th><th>Number</th><th class="text-right">Opening</th><th class="text-right">Balance now</th><th>Lines</th><th /></tr></thead>
          <tbody>
            <tr v-for="a in lookups.accounts" :key="a.id" :class="!a.active && 'opacity-55'">
              <td><span class="block text-ink">{{ a.name }}</span><span class="text-xs text-ink/55">{{ a.institution || a.kind }} · {{ a.currency }}</span></td>
              <td class="readout text-xs">{{ a.number || '—' }}</td>
              <td class="readout text-right">{{ amount(a.opening_balance) }}<span class="block text-[11px] text-ink/50">{{ dateLabel(a.opening_date) }}</span></td>
              <td class="readout text-right">{{ amount(a.balance) }}</td>
              <td>{{ a.entries }}</td>
              <td><button class="btn-ghost btn-sm" @click="editAccount(a)">Edit</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-medium">Categories</h2>
          <p class="text-sm text-ink/60">"Transfer" categories (loans, capital, director transfers) move money without counting as income or spending.</p>
        </div>
        <button class="btn-ink" @click="editCategory()">+ Category</button>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="k in KINDS" :key="k" class="panel p-4">
          <p class="ledger-label mb-2">{{ KIND_LABEL[k] }}</p>
          <ul class="grid gap-1">
            <li v-for="c in lookups.categories.filter((x) => x.kind === k)" :key="c.id" class="flex items-center justify-between gap-2 text-sm">
              <button type="button" class="min-w-0 truncate text-left hover:underline" :class="!c.active && 'text-ink/40 line-through'" @click="editCategory(c)">{{ c.name }}</button>
              <span class="text-xs text-ink/45">{{ c.entries || 0 }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section>
      <h2 class="text-lg font-medium">Fiscal years</h2>
      <p class="mb-3 text-sm text-ink/60">Shrawan 1 to Ashadh end. Close a year after the audit so its books cannot change.</p>
      <div class="panel relative overflow-x-auto">
        <table class="ledger-table">
          <thead><tr><th>Year</th><th>Dates</th><th>Status</th><th /></tr></thead>
          <tbody>
            <tr v-for="y in years" :key="y.name">
              <td class="readout">{{ y.name }}</td>
              <td class="text-sm">{{ dateLabel(y.start) }} – {{ dateLabel(y.end) }}</td>
              <td class="text-sm">{{ y.closed ? `Closed by ${y.close?.closed_by_name}` : y.end < today ? 'Ended, open' : 'Current / open' }}</td>
              <td class="text-right">
                <button v-if="!y.closed && y.end < today" class="btn-ghost btn-sm" @click="closeYear(y)">Close year</button>
                <button v-if="y.closed && hasRole('super_admin')" class="btn-ghost btn-sm" @click="reopen(y)">Reopen</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <Modal :open="acctOpen" :title="acctId ? 'Edit account' : 'New account'" @close="acctOpen = false">
      <form class="grid gap-3" @submit.prevent="saveAccount">
        <label class="field"><span class="ledger-label">Name</span><input v-model="acct.name" class="input" required maxlength="120" placeholder="Bank name · Current" /></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="ledger-label">Type</span>
            <select v-model="acct.kind" class="input"><option value="bank">Bank account</option><option value="cash">Cash / petty cash</option><option value="card">Card</option><option value="wallet">Digital wallet</option></select></label>
          <label class="field"><span class="ledger-label">Currency</span><input v-model="acct.currency" class="input uppercase" maxlength="3" pattern="[A-Z]{3}" required /></label>
          <label class="field"><span class="ledger-label">Bank / provider</span><input v-model="acct.institution" class="input" maxlength="120" /></label>
          <label class="field"><span class="ledger-label">Account number</span><input v-model="acct.number" class="input" maxlength="40" /></label>
          <label class="field"><span class="ledger-label">Opening balance</span><input v-model="acct.opening_balance" type="number" step="0.01" class="input readout" required /></label>
          <label class="field"><span class="ledger-label">Opening date</span><input v-model="acct.opening_date" type="date" class="input" required /></label>
        </div>
        <label class="field"><span class="ledger-label">Notes</span><input v-model="acct.notes" class="input" /></label>
        <label class="flex items-center gap-2 text-sm"><input v-model="acct.active" type="checkbox" class="accent-ink" /> Active</label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end">Save account</button>
      </form>
    </Modal>
    <Modal :open="catOpen" :title="catId ? 'Edit category' : 'New category'" @close="catOpen = false">
      <form class="grid gap-3" @submit.prevent="saveCategory">
        <label class="field"><span class="ledger-label">Name</span><input v-model="cat.name" class="input" required maxlength="80" /></label>
        <label class="field"><span class="ledger-label">Kind</span>
          <select v-model="cat.kind" class="input"><option v-for="k in KINDS" :key="k" :value="k">{{ KIND_LABEL[k] }}</option></select></label>
        <label class="field"><span class="ledger-label">Description</span><input v-model="cat.description" class="input" maxlength="255" /></label>
        <label class="flex items-center gap-2 text-sm"><input v-model="cat.active" type="checkbox" class="accent-ink" /> Active (inactive categories stay on old lines)</label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end">Save category</button>
      </form>
    </Modal>
  </div>
</template>
