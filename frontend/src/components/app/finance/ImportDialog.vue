<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { toast } from '../ui/toast'
import { errorMessage } from '../pm/pm'
import { amount, dateLabel, lookups } from './finance'

const props = defineProps<{ open: boolean; defaultAccount?: number }>()
const emit = defineEmits<{ close: []; imported: [] }>()
interface Row { date: string; description: string; party: string; category: string | null; debit: string; credit: string; duplicate: boolean }
const account = ref(0)
const file = ref<File | null>(null)
const preview = ref<{ created: number; duplicates: number; rows: Row[] } | null>(null)
const busy = ref(false)
const error = ref('')
watch(() => props.open, (o) => {
  if (!o) return
  account.value = props.defaultAccount || lookups.accounts.find((a) => a.active)?.id || 0
  file.value = null
  preview.value = null
  error.value = ''
})
async function send(dryRun: boolean) {
  if (!file.value) return
  busy.value = true
  error.value = ''
  const form = new FormData()
  form.append('account', String(account.value))
  form.append('file', file.value)
  form.append('dry_run', String(dryRun))
  try {
    const { data } = await api.post('finance/transactions/import/', form)
    if (dryRun) preview.value = data
    else {
      toast.success(`${data.created} lines added${data.duplicates ? `, ${data.duplicates} already in the books` : ''}. New lines are marked for review.`)
      emit('imported')
      emit('close')
    }
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
function pick(e: Event) {
  file.value = (e.target as HTMLInputElement).files?.[0] || null
  preview.value = null
  if (file.value) send(true)
}
</script>

<template>
  <Modal :open="open" title="Import a bank statement" width="max-w-3xl" @close="emit('close')">
    <div class="grid gap-4">
      <p class="text-sm text-ink/65">
        Download the statement from e-banking as Excel or CSV and drop it here. Columns are detected automatically
        (date, description/particulars, debit/withdrawal, credit/deposit; party, category and note if present).
        Lines already in the books are skipped, so overlapping statements are safe.
      </p>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"><span class="ledger-label">Into account</span>
          <select v-model.number="account" class="input" @change="file && send(true)">
            <option v-for="a in lookups.accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select></label>
        <label class="field"><span class="ledger-label">Statement file</span>
          <input type="file" accept=".csv,.xlsx,.xlsm" class="input" @change="pick" /></label>
      </div>
      <p v-if="busy && !preview" class="text-sm text-ink/60">Reading…</p>
      <template v-if="preview">
        <p class="text-sm"><b>{{ preview.created }}</b> new lines · {{ preview.duplicates }} already in the books</p>
        <div class="max-h-80 overflow-auto rounded-lg border border-ink/10">
          <table class="ledger-table text-xs">
            <thead><tr><th>Date</th><th>Description</th><th>Category</th><th class="text-right">Out</th><th class="text-right">In</th><th /></tr></thead>
            <tbody>
              <tr v-for="(r, i) in preview.rows" :key="i" :class="r.duplicate && 'opacity-45'">
                <td class="whitespace-nowrap">{{ dateLabel(r.date) }}</td>
                <td>{{ r.party ? r.party + ' · ' : '' }}{{ r.description }}</td>
                <td>{{ r.category || '—' }}</td>
                <td class="readout text-right">{{ Number(r.debit) ? amount(r.debit) : '' }}</td>
                <td class="readout text-right">{{ Number(r.credit) ? amount(r.credit) : '' }}</td>
                <td>{{ r.duplicate ? 'already in' : 'new' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ink justify-self-end" :disabled="busy || !preview || !preview.created" @click="send(false)">
        {{ busy ? 'Importing…' : `Add ${preview?.created || 0} lines` }}
      </button>
    </div>
  </Modal>
</template>
