<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { errorMessage } from '../pm/pm'
import RecordFiles from './RecordFiles.vue'
import { amount, dateLabel, type Account, type Statement } from './finance'

/** Bank statements for one account and whether the books agree with each. */
const props = defineProps<{ account: Account; fy: string }>()
const emit = defineEmits<{ changed: [] }>()
const list = ref<Statement[]>([])
const open = ref(false)
const viewing = ref<Statement | null>(null)
const form = reactive({ start: '', end: '', opening_balance: '', closing_balance: '', notes: '' })
const error = ref('')
async function load() {
  list.value = (await api.get<Statement[]>('finance/statements/', { params: { account: props.account.id } })).data
}
watch(() => props.account.id, () => load().catch(() => {}), { immediate: true })
function add() {
  const last = list.value[0]
  Object.assign(form, { start: last ? nextDay(last.end) : props.account.opening_date, end: '', opening_balance: last?.closing_balance || props.account.opening_balance, closing_balance: '', notes: '' })
  error.value = ''
  open.value = true
}
function nextDay(d: string) {
  const x = new Date(d + 'T00:00:00Z')
  x.setUTCDate(x.getUTCDate() + 1)
  return x.toISOString().slice(0, 10)
}
async function save() {
  try {
    await api.post('finance/statements/', { account: props.account.id, ...form })
    open.value = false
    await load()
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <div class="panel flex flex-wrap items-center gap-2 px-4 py-3 text-sm">
    <span class="ledger-label mr-1">Statements</span>
    <button v-for="s in list" :key="s.id" type="button" class="rounded-full border px-2.5 py-1 text-xs"
      :class="s.reconciliation.reconciled ? 'border-moss/30 bg-moss/10 text-moss' : 'border-rust/30 bg-rust/10 text-rust'" @click="viewing = s">
      {{ dateLabel(s.start) }} – {{ dateLabel(s.end) }} · {{ s.reconciliation.reconciled ? 'matches bank' : 'off by ' + amount(s.reconciliation.difference) }}
    </button>
    <span v-if="!list.length" class="text-xs text-ink/55">None yet. Add the statement's closing balance to check the books against the bank.</span>
    <button type="button" class="btn-ghost btn-sm ml-auto" @click="add">+ Statement</button>
  </div>

  <Modal :open="open" :title="`Statement · ${account.name}`" @close="open = false">
    <form class="grid gap-3" @submit.prevent="save">
      <div class="grid grid-cols-2 gap-3">
        <label class="field"><span class="ledger-label">From</span><input v-model="form.start" type="date" class="input" required /></label>
        <label class="field"><span class="ledger-label">To</span><input v-model="form.end" type="date" class="input" required /></label>
        <label class="field"><span class="ledger-label">Opening balance</span><input v-model="form.opening_balance" type="number" step="0.01" class="input readout" required /></label>
        <label class="field"><span class="ledger-label">Closing balance</span><input v-model="form.closing_balance" type="number" step="0.01" class="input readout" required /></label>
      </div>
      <label class="field"><span class="ledger-label">Notes</span><input v-model="form.notes" class="input" /></label>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ink justify-self-end">Save and reconcile</button>
    </form>
  </Modal>

  <Modal :open="!!viewing" :title="viewing ? `Statement ${dateLabel(viewing.start)} – ${dateLabel(viewing.end)}` : ''" @close="viewing = null">
    <div v-if="viewing" class="grid gap-4 text-sm">
      <table class="ledger-table">
        <thead><tr><th /><th class="text-right">Bank says</th><th class="text-right">Books say</th></tr></thead>
        <tbody>
          <tr><td>Opening ({{ viewing.reconciliation.bs_start }} BS)</td><td class="readout text-right">{{ amount(viewing.opening_balance) }}</td><td class="readout text-right">{{ amount(viewing.reconciliation.computed_opening) }}</td></tr>
          <tr><td>Closing ({{ viewing.reconciliation.bs_end }} BS)</td><td class="readout text-right">{{ amount(viewing.closing_balance) }}</td><td class="readout text-right">{{ amount(viewing.reconciliation.computed_closing) }}</td></tr>
        </tbody>
      </table>
      <p :class="viewing.reconciliation.reconciled ? 'text-moss' : 'text-rust'">
        {{ viewing.reconciliation.reconciled ? 'Reconciled: the books match the bank statement.' : `Difference of ${amount(viewing.reconciliation.difference)}: a line is missing, duplicated or has a wrong amount.` }}
      </p>
      <div>
        <p class="ledger-label mb-2">Statement copy</p>
        <RecordFiles :link="{ statement: viewing.id }" :folder="`Bank statements/FY ${fy.replace('/', '-')}`" :fiscal-year="fy" />
      </div>
    </div>
  </Modal>
</template>
