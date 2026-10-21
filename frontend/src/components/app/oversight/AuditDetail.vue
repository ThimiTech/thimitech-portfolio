<script setup lang="ts">
import Modal from '../ui/Modal.vue'
import { timestamp } from '../inventory/inventory'
import { readable, label, type AuditEvent } from './oversight'
defineProps<{ event: AuditEvent | null }>()
defineEmits<{ close: []; trace: [id: string] }>()
</script>
<template>
  <Modal
    :open="!!event"
    :title="`Audit event #${event?.id ?? ''}`"
    width="max-w-3xl"
    @close="$emit('close')"
  >
    <template v-if="event">
      <p class="font-mono text-xs text-flag">
        {{ event.action.toUpperCase() }} · {{ event.target_model }} #{{ event.target_id }}
      </p>
      <dl class="my-5 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt class="ledger-label">Actor</dt>
          <dd class="mt-1">
            {{ event.actor_label
            }}<span v-if="event.actor_role" class="text-ink/60">
              · {{ label(event.actor_role) }}</span
            ><span v-if="event.actor_id" class="block text-xs text-ink/60"
              >User #{{ event.actor_id }}</span
            >
          </dd>
        </div>
        <div>
          <dt class="ledger-label">Recorded · NPT</dt>
          <dd class="mt-1">{{ timestamp(event.timestamp) }}</dd>
        </div>
        <div class="sm:col-span-2">
          <dt class="ledger-label">Source</dt>
          <dd class="mt-1 break-words">
            {{ event.source }} · {{ event.entry_point || 'System operation' }}
          </dd>
        </div>
        <div v-if="event.request_id" class="sm:col-span-2">
          <dt class="ledger-label">Request ID</dt>
          <dd class="mt-1 break-all font-mono text-xs">{{ event.request_id }}</dd>
        </div>
      </dl>
      <p class="mb-4 text-xs text-ink/65">
        Sensitive values are redacted at capture. A redacted field records that a change occurred.
      </p>
      <div class="overflow-x-auto">
        <table class="ledger-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Before</th>
              <th>After</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(change, field) in event.diff" :key="field">
              <th scope="row" class="text-left font-medium">{{ label(String(field)) }}</th>
              <td v-if="change.redacted" colspan="2" class="text-ink/60">
                Value redacted · changed
              </td>
              <template v-else
                ><td class="max-w-64 whitespace-pre-wrap break-words">
                  {{ readable(change.before) }}
                </td>
                <td class="max-w-64 whitespace-pre-wrap break-words">
                  {{ readable(change.after) }}
                </td></template
              >
            </tr>
            <tr v-if="!Object.keys(event.diff).length">
              <td colspan="3">No field values recorded.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <template #footer
      ><button
        v-if="event?.request_id"
        class="btn-ink btn-sm"
        @click="$emit('trace', event.request_id)"
      >
        Show this request's events</button
      ><button class="btn-ghost btn-sm" @click="$emit('close')">Close</button></template
    >
  </Modal>
</template>
