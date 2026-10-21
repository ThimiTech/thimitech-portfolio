<script setup lang="ts">
import StatusPill from "../ui/StatusPill.vue";
import Avatar from "../ui/Avatar.vue";
import { type LeaveRequest, fmtDays, fmtRange, fmtStamp } from "./leave";

defineProps<{ requests: LeaveRequest[]; showPerson?: boolean; busyId?: number | null; caption: string }>();
defineEmits<{ cancel: [req: LeaveRequest] }>();
</script>

<template>
  <div class="overflow-x-auto">
    <table class="ledger-table min-w-[720px]">
      <caption class="sr-only">{{ caption }}</caption>
      <thead>
        <tr>
          <th v-if="showPerson" scope="col">Employee</th>
          <th scope="col">Type</th>
          <th scope="col">Dates</th>
          <th scope="col" class="text-right">Days</th>
          <th scope="col">Status</th>
          <th scope="col">Decision</th>
          <th scope="col"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in requests" :key="r.id">
          <td v-if="showPerson">
            <span class="flex items-center gap-2">
              <Avatar :name="r.user.full_name" :size="24" />
              <span class="truncate">{{ r.user.full_name }}</span>
            </span>
          </td>
          <td>
            <span class="flex items-center gap-2 whitespace-nowrap">
              <span class="h-2 w-2 rounded-full" :style="{ background: r.leave_type.color || '#7a6a52' }" aria-hidden="true" />
              {{ r.leave_type.name }}
            </span>
            <span v-if="r.reason" class="mt-0.5 block max-w-[220px] truncate text-[11.5px] text-ink/50" :title="r.reason">{{ r.reason }}</span>
          </td>
          <td class="readout text-[12.5px] whitespace-nowrap">
            {{ fmtRange(r.start_date, r.end_date) }}
            <span v-if="r.half_day" class="ledger-label ml-1 text-[9.5px]">½ day</span>
          </td>
          <td class="readout text-right">{{ fmtDays(r.days) }}</td>
          <td><StatusPill :status="r.status" /></td>
          <td class="max-w-[260px] text-[12.5px] text-ink/65">
            <template v-if="r.decided_at">
              <span class="readout block text-[11px] text-ink/45">
                {{ r.approver?.full_name ?? "—" }} · {{ fmtStamp(r.decided_at) }}
              </span>
              <span v-if="r.decision_note" class="line-clamp-2" :title="r.decision_note">“{{ r.decision_note }}”</span>
            </template>
            <span v-else-if="r.status === 'pending'" class="text-ink/45">
              Awaiting {{ r.designated_approver?.full_name ?? "HR" }}
            </span>
            <span v-else class="text-ink/35">—</span>
          </td>
          <td class="text-right">
            <button
              v-if="r.can_cancel"
              class="btn-ghost btn-sm"
              :disabled="busyId === r.id"
              :aria-label="`Cancel ${r.leave_type.name} leave ${fmtRange(r.start_date, r.end_date)}`"
              @click="$emit('cancel', r)"
            >
              {{ busyId === r.id ? "Cancelling…" : "Cancel" }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
