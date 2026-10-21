<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { confirmDialog } from '../ui/confirm'
import { errorMessage } from '../pm/pm'
const props = defineProps<{
  resource: 'payslips' | 'invoices' | 'expenses'
  id: number
  status: string
}>()
const emit = defineEmits<{ changed: [] }>()
const busy = ref(false)
const error = ref('')
const actionDialog = ref('')
const note = ref('')
async function change(action: string, data: object = {}) {
  busy.value = true
  error.value = ''
  try {
    await api.post(`finance/${props.resource}/${props.id}/${action}/`, data)
    actionDialog.value = ''
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function finalize(action: string) {
  if (
    !(await confirmDialog({
      title: action === 'void' ? 'Void this record?' : 'Confirm this step?',
      body:
        action === 'void'
          ? 'The record will be kept in history and excluded from totals.'
          : 'Finalized amounts will be locked. Check the details before proceeding.',
      confirmLabel: 'Confirm',
      danger: action === 'void',
    }))
  )
    return
  await change(action)
}
function open(action: string) {
  note.value = ''
  error.value = ''
  actionDialog.value = action
}
function submitNote() {
  return change(
    actionDialog.value,
    actionDialog.value === 'mark-paid'
      ? { payment_reference: note.value }
      : { decision_note: note.value },
  )
}
</script>
<template>
  <div>
    <div class="flex flex-wrap gap-2">
      <template v-if="resource === 'expenses'">
        <button
          v-if="['draft', 'rejected'].includes(status)"
          class="btn-ghost btn-sm"
          :disabled="busy"
          @click="change('submit')"
        >
          Submit for review
        </button>
        <template v-if="status === 'submitted'"
          ><button class="btn-ink btn-sm" :disabled="busy" @click="open('approve')">Approve</button
          ><button class="btn-danger btn-sm" :disabled="busy" @click="open('reject')">
            Reject
          </button></template
        >
        <button
          v-if="status === 'approved'"
          class="btn-ink btn-sm"
          :disabled="busy"
          @click="open('mark-paid')"
        >
          Record payment
        </button>
      </template>
      <template v-else
        ><button
          v-if="status === 'draft'"
          class="btn-ink btn-sm"
          :disabled="busy"
          @click="finalize('issue')"
        >
          Mark issued</button
        ><button
          v-if="status === 'issued'"
          class="btn-ink btn-sm"
          :disabled="busy"
          @click="open('mark-paid')"
        >
          Record payment</button
        ><button
          v-if="['draft', 'issued'].includes(status)"
          class="btn-danger btn-sm"
          :disabled="busy"
          @click="finalize('void')"
        >
          Void
        </button></template
      >
    </div>
    <p v-if="error && !actionDialog" role="alert" class="mt-3 text-sm text-rust">{{ error }}</p>
    <Modal
      :open="!!actionDialog"
      :title="
        actionDialog === 'mark-paid'
          ? 'Record a completed payment'
          : actionDialog === 'approve'
            ? 'Approve expense'
            : 'Reject expense'
      "
      @close="actionDialog = ''"
      ><form class="grid gap-4" @submit.prevent="submitNote">
        <p v-if="actionDialog === 'mark-paid'" class="text-sm text-ink/65">
          Record a payment already completed outside this workspace.
        </p>
        <label class="field"
          ><span class="ledger-label">{{
            actionDialog === 'mark-paid' ? 'Payment reference' : 'Decision note'
          }}</span
          ><textarea
            v-model="note"
            class="input"
            :required="actionDialog === 'mark-paid'"
            :maxlength="actionDialog === 'mark-paid' ? 200 : 2000"
            rows="3"
          />
        </label>
        <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
        <button class="btn-ink justify-self-end" :disabled="busy">
          {{ busy ? 'Saving…' : 'Confirm' }}
        </button>
      </form></Modal
    >
  </div>
</template>
