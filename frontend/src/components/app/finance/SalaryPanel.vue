<script setup lang="ts">
import { reactive, ref } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { errorMessage, todayNPT } from '../pm/pm'
import { money, staffName, type Salary, type Staff } from './finance'
defineProps<{ salaries: Salary[]; staff: Staff[] }>()
const emit = defineEmits<{ changed: [] }>()
const open = ref(false)
const editing = ref<number | null>(null)
const busy = ref(false)
const error = ref('')
const form = reactive({
  employee: 0,
  basic: '0.00',
  allowances: '0.00',
  deductions: '0.00',
  effective_from: todayNPT(),
  active: true,
  notes: '',
})
function edit(salary?: Salary) {
  editing.value = salary?.id || null
  error.value = ''
  Object.assign(form, {
    employee: salary?.employee || 0,
    basic: salary?.basic || '0.00',
    allowances: salary?.allowances || '0.00',
    deductions: salary?.deductions || '0.00',
    effective_from: salary?.effective_from || todayNPT(),
    active: salary?.active ?? true,
    notes: salary?.notes || '',
  })
  open.value = true
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    if (editing.value) await api.patch(`finance/salaries/${editing.value}/`, form)
    else await api.post('finance/salaries/', form)
    open.value = false
    emit('changed')
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
      <h2 class="text-lg font-medium">Salary structures</h2>
      <button class="btn-ink" @click="edit()">+ Add structure</button>
    </div>
    <p v-if="!salaries.length" class="panel p-8 text-sm text-ink/65">
      Set each employee’s monthly NPR pay before generating payslips.
    </p>
    <div v-else class="panel overflow-x-auto">
      <table class="ledger-table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Gross / month</th>
            <th>Deductions</th>
            <th>Net / month</th>
            <th>Effective</th>
            <th>Status</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in salaries" :key="s.id">
            <td>{{ s.employee_name || 'Staff #' + s.employee }}</td>
            <td class="whitespace-nowrap readout">{{ money(s.gross) }}</td>
            <td class="whitespace-nowrap readout">{{ money(s.deductions) }}</td>
            <td class="whitespace-nowrap readout">{{ money(s.net) }}</td>
            <td class="whitespace-nowrap">{{ s.effective_from }}</td>
            <td>{{ s.active ? 'Active' : 'Inactive' }}</td>
            <td>
              <button
                class="btn-ghost btn-sm"
                :aria-label="'Edit salary for ' + s.employee_name"
                @click="edit(s)"
              >
                Edit
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <Modal
      :open="open"
      :title="editing ? 'Edit salary structure' : 'New salary structure'"
      @close="open = false"
      ><form class="grid gap-4" @submit.prevent="save">
        <label class="field"
          ><span class="ledger-label">Employee</span
          ><select v-model="form.employee" class="input" required :disabled="!!editing">
            <option :value="0" disabled>Select staff member</option>
            <option v-for="p in staff" :key="p.id" :value="p.id">{{ staffName(p) }}</option>
          </select></label
        >
        <p class="text-xs text-ink/65">Monthly NPR amounts. Deductions are entered manually.</p>
        <label class="field"
          ><span class="ledger-label">Basic pay</span
          ><input
            v-model="form.basic"
            class="input"
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            required /></label
        ><label class="field"
          ><span class="ledger-label">Allowances</span
          ><input
            v-model="form.allowances"
            class="input"
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            required /></label
        ><label class="field"
          ><span class="ledger-label">Manual deductions</span
          ><input
            v-model="form.deductions"
            class="input"
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            required /></label
        ><label class="field"
          ><span class="ledger-label">Effective from</span
          ><input v-model="form.effective_from" class="input" type="date" required /></label
        ><label class="field"
          ><span class="ledger-label">Notes</span
          ><textarea v-model="form.notes" class="input" rows="2" /></label
        ><label class="flex items-center gap-2 text-sm"
          ><input v-model="form.active" type="checkbox" class="accent-ink" /> Active
          structure</label
        >
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy || !form.employee">
          {{ busy ? 'Saving…' : 'Save structure' }}
        </button>
      </form></Modal
    >
  </section>
</template>
