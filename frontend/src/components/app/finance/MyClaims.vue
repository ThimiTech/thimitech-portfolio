<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import StatusPill from '../ui/StatusPill.vue'
import { confirmDialog } from '../ui/confirm'
import { toast } from '../ui/toast'
import { errorMessage, todayNPT } from '../pm/pm'
import RecordFiles from './RecordFiles.vue'
import { amount, dateLabel, type Category, type Expense } from './finance'

/** "I paid for something for the company": draft → submit (with receipt) → approved → reimbursed. */
const claims = ref<Expense[]>([])
const categories = ref<Category[]>([])
const editing = ref<Expense | null>(null)
const open = ref(false)
const error = ref('')
const form = reactive({ description: '', date: todayNPT(), amount: '', category: null as number | null, notes: '' })
async function load() {
  const [c, k] = await Promise.all([api.get<Expense[]>('finance/my-expenses/'), api.get<Category[]>('finance/categories/', { params: { kind: 'expense' } })])
  claims.value = c.data
  categories.value = k.data.filter((x) => x.active)
}
onMounted(() => load().catch(() => {}))
const owed = computed(() => claims.value.filter((c) => c.status === 'approved').reduce((s, c) => s + Number(c.amount), 0))
function edit(c?: Expense) {
  editing.value = c || null
  error.value = ''
  Object.assign(form, c ? { description: c.description, date: c.date, amount: c.amount, category: c.category, notes: c.notes } : { description: '', date: todayNPT(), amount: '', category: null, notes: '' })
  open.value = true
}
async function save() {
  try {
    const { data } = editing.value ? await api.patch<Expense>(`finance/my-expenses/${editing.value.id}/`, form) : await api.post<Expense>('finance/my-expenses/', form)
    editing.value = data
    await load()
    toast.success('Saved. Attach the receipt, then submit.')
  } catch (e) {
    error.value = errorMessage(e)
  }
}
async function act(c: Expense, action: 'submit' | 'delete') {
  try {
    if (action === 'delete') {
      if (!(await confirmDialog({ title: 'Delete this draft?', body: c.description, confirmLabel: 'Delete', danger: true }))) return
      await api.delete(`finance/my-expenses/${c.id}/`)
    } else await api.post(`finance/my-expenses/${c.id}/submit/`)
    open.value = false
    await load()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
</script>

<template>
  <section>
    <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 class="text-lg font-medium">My claims</h2>
        <p class="text-sm text-ink/60">Paid for something for the company? Record it with the receipt and submit it for reimbursement.<span v-if="owed"> The company owes you <b class="readout">{{ amount(owed) }}</b>.</span></p>
      </div>
      <button class="btn-ink" @click="edit()">+ New claim</button>
    </div>
    <div v-if="claims.length" class="panel relative overflow-x-auto">
      <table class="ledger-table text-sm">
        <thead><tr><th>Date</th><th>What</th><th class="text-right">Amount</th><th>Status</th><th /></tr></thead>
        <tbody>
          <tr v-for="c in claims" :key="c.id">
            <td class="whitespace-nowrap">{{ dateLabel(c.date) }}</td>
            <td><span class="block text-ink">{{ c.description }}</span><span class="text-xs text-ink/55">{{ c.category_name || '—' }} · {{ c.files.length }} receipt{{ c.files.length === 1 ? '' : 's' }}</span>
              <span v-if="c.decision_note" class="block text-xs text-ink/60">Note: {{ c.decision_note }}</span></td>
            <td class="readout text-right">{{ amount(c.amount) }}</td>
            <td><StatusPill :status="c.status" :label="c.status === 'approved' ? 'approved · to be paid' : c.status === 'paid' ? 'reimbursed' : undefined" /></td>
            <td class="text-right whitespace-nowrap">
              <template v-if="['draft', 'rejected'].includes(c.status)">
                <button class="btn-ghost btn-sm" @click="edit(c)">Edit</button>
                <button class="btn-ink btn-sm ml-2" @click="act(c, 'submit')">Submit</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="panel p-5 text-sm text-ink/60">No claims yet.</p>

    <Modal :open="open" :title="editing ? 'Claim' : 'New claim'" @close="open = false">
      <form class="grid gap-3" @submit.prevent="save">
        <label class="field"><span class="ledger-label">What did you pay for?</span><input v-model="form.description" class="input" required maxlength="500" placeholder="Cursor subscription, client meeting tea, printing…" /></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="ledger-label">Date</span><input v-model="form.date" type="date" class="input" required /></label>
          <label class="field"><span class="ledger-label">Amount (NPR)</span><input v-model="form.amount" type="number" min="0.01" step="0.01" class="input readout" required /></label>
        </div>
        <label class="field"><span class="ledger-label">Category</span>
          <select v-model="form.category" class="input"><option :value="null">Not sure</option><option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option></select></label>
        <label class="field"><span class="ledger-label">Notes</span><textarea v-model="form.notes" class="input" rows="2" /></label>
        <div v-if="editing" class="rounded-lg border border-ink/10 p-3">
          <p class="ledger-label mb-2">Receipt</p>
          <RecordFiles :link="{ expense: editing.id }" folder="Receipts & claims" :readonly="!['draft', 'rejected'].includes(editing.status)" />
        </div>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <div class="flex flex-wrap justify-between gap-2">
          <button v-if="editing?.status === 'draft'" type="button" class="btn-danger btn-sm" @click="act(editing, 'delete')">Delete draft</button><span v-else />
          <div class="flex gap-2">
            <button class="btn-ghost">Save</button>
            <button v-if="editing && ['draft', 'rejected'].includes(editing.status)" type="button" class="btn-ink" @click="act(editing, 'submit')">Submit for approval</button>
          </div>
        </div>
      </form>
    </Modal>
  </section>
</template>
