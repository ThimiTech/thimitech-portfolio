<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { errorMessage } from '../pm/pm'
import { type Asset, type Category } from './inventory'
const props = defineProps<{ open: boolean; asset: Asset | null; categories: Category[] }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const busy = ref(false)
const error = ref('')
const form = reactive({
  tag: '',
  name: '',
  category: 0,
  serial_number: '',
  location: '',
  purchase_date: '',
  purchase_cost: '',
  currency: 'NPR',
  status: 'available',
  notes: '',
})
watch(
  () => props.open,
  (open) => {
    if (!open) return
    const a = props.asset
    error.value = ''
    Object.assign(form, {
      tag: a?.tag || '',
      name: a?.name || '',
      category: a?.category || props.categories[0]?.id || 0,
      serial_number: a?.serial_number || '',
      location: a?.location || '',
      purchase_date: a?.purchase_date || '',
      purchase_cost: a?.purchase_cost || '',
      currency: a?.currency || 'NPR',
      status: a?.status || 'available',
      notes: a?.notes || '',
    })
  },
)
async function save() {
  busy.value = true
  error.value = ''
  const payload = {
    ...form,
    purchase_date: form.purchase_date || null,
    purchase_cost: form.purchase_cost === '' ? null : form.purchase_cost,
  }
  try {
    if (props.asset) await api.patch(`inventory/assets/${props.asset.id}/`, payload)
    else await api.post('inventory/assets/', payload)
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
    :open="open"
    :title="asset ? 'Edit ' + asset.tag : 'Register asset'"
    width="max-w-2xl"
    @close="emit('close')"
    ><form class="grid gap-4" @submit.prevent="save">
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Asset tag</span
          ><input
            v-model="form.tag"
            class="input"
            required
            maxlength="40"
            placeholder="TT-001" /></label
        ><label class="field"
          ><span class="ledger-label">Category</span
          ><select v-model="form.category" class="input" required>
            <option :value="0" disabled>Select category</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select></label
        >
      </div>
      <label class="field"
        ><span class="ledger-label">Asset name</span
        ><input v-model="form.name" class="input" required maxlength="200"
      /></label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Serial number</span
          ><input v-model="form.serial_number" class="input" maxlength="120" /></label
        ><label class="field"
          ><span class="ledger-label">Location</span
          ><input v-model="form.location" class="input" maxlength="200"
        /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Purchase date</span
          ><input v-model="form.purchase_date" type="date" class="input" /></label
        ><label class="field"
          ><span class="ledger-label">Purchase cost</span
          ><input
            v-model="form.purchase_cost"
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            class="input"
        /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Currency</span
          ><input
            v-model="form.currency"
            class="input uppercase"
            pattern="[A-Z]{3}"
            maxlength="3"
            required /></label
        ><label class="field"
          ><span class="ledger-label">Status</span
          ><select v-model="form.status" class="input" :disabled="asset?.status === 'assigned'">
            <option value="available">Available</option>
            <option v-if="asset?.status === 'assigned'" value="assigned">Assigned</option>
            <option value="maintenance">Maintenance</option>
            <option value="retired">Retired</option>
          </select></label
        >
      </div>
      <p v-if="asset?.status === 'assigned'" class="text-xs text-ink/65">
        Return this asset before changing its availability.
      </p>
      <label class="field"
        ><span class="ledger-label">Notes</span
        ><textarea v-model="form.notes" class="input" rows="3" />
      </label>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ink justify-self-end" :disabled="busy || !form.category">
        {{ busy ? 'Saving…' : 'Save asset' }}
      </button>
    </form></Modal
  >
</template>
