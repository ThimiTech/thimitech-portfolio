<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { errorMessage, todayNPT } from '../pm/pm'
import { staffName, type Staff } from '../finance/finance'
import { type Asset } from './inventory'
const props = defineProps<{ asset: Asset | null; staff: Staff[]; mode: 'assign' | 'return' }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const form = reactive({
  employee: 0,
  due_back: '',
  notes: '',
  condition: 'available',
  return_note: '',
})
const busy = ref(false)
const error = ref('')
watch(
  () => props.asset,
  () => {
    Object.assign(form, {
      employee: 0,
      due_back: '',
      notes: '',
      condition: 'available',
      return_note: '',
    })
    error.value = ''
  },
)
async function save() {
  if (!props.asset) return
  busy.value = true
  error.value = ''
  try {
    if (props.mode === 'assign')
      await api.post('inventory/assignments/', {
        asset: props.asset.id,
        employee: form.employee,
        due_back: form.due_back || null,
        notes: form.notes,
      })
    else
      await api.post(`inventory/assignments/${props.asset.assigned_to!.assignment}/return/`, {
        condition: form.condition,
        return_note: form.return_note,
      })
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <Modal
    :open="!!asset"
    :title="(mode === 'assign' ? 'Assign ' : 'Return ') + (asset?.tag || 'asset')"
    @close="emit('close')"
    ><form v-if="asset" class="grid gap-4" @submit.prevent="save">
      <p class="font-medium">{{ asset.name }}</p>
      <template v-if="mode === 'assign'"
        ><label class="field"
          ><span class="ledger-label">Staff member</span
          ><select v-model="form.employee" class="input" required>
            <option :value="0" disabled>Select staff member</option>
            <option v-for="p in staff" :key="p.id" :value="p.id">{{ staffName(p) }}</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Expected return</span
          ><input v-model="form.due_back" type="date" :min="todayNPT()" class="input" /></label
        ><label class="field"
          ><span class="ledger-label">Handover notes</span
          ><textarea v-model="form.notes" rows="3" class="input" /></label></template
      ><template v-else
        ><p class="text-sm text-ink/65">
          Assigned to {{ asset.assigned_to?.name }}. Confirm the asset has been received back.
        </p>
        <label class="field"
          ><span class="ledger-label">Returned condition / next status</span
          ><select v-model="form.condition" class="input">
            <option value="available">Available for use</option>
            <option value="maintenance">Needs maintenance</option>
            <option value="retired">Retire asset</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Return notes</span
          ><textarea v-model="form.return_note" rows="3" maxlength="5000" class="input" /></label
      ></template>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <button
        class="btn-ink justify-self-end"
        :disabled="busy || (mode === 'assign' && !form.employee)"
      >
        {{ busy ? 'Saving…' : mode === 'assign' ? 'Confirm assignment' : 'Confirm return' }}
      </button>
    </form></Modal
  >
</template>
