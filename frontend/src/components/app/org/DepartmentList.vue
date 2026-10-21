<script setup lang="ts">
import { computed } from "vue";
import type { Department } from "./org";

const props = defineProps<{ departments: Department[]; manage?: boolean; busyId?: number | null }>();
const emit = defineEmits<{ edit: [d: Department]; remove: [d: Department] }>();

const nameOf = computed(() => new Map(props.departments.map((d) => [d.id, d.name])));
</script>

<template>
  <ul class="divide-y divide-dashed divide-ink/10">
    <li v-for="d in departments" :key="d.id" class="flex flex-wrap items-start gap-x-4 gap-y-2 px-5 py-3.5">
      <div class="min-w-0 flex-1 basis-48">
        <p class="font-medium text-ink">{{ d.name }}</p>
        <p class="mt-0.5 text-xs text-ink/55">
          <template v-if="d.parent">under {{ nameOf.get(d.parent) ?? "—" }} · </template>
          <span>Lead: {{ d.manager?.full_name ?? "unassigned" }}</span>
        </p>
      </div>
      <span class="readout self-center text-sm text-ink/70" :aria-label="`${d.member_count} staff`">
        {{ String(d.member_count).padStart(2, "0") }}<span class="ml-1 text-[11px] text-ink/40">staff</span>
      </span>
      <div v-if="manage" class="flex gap-1.5 self-center">
        <button type="button" class="btn-ghost btn-sm" :aria-label="`Edit ${d.name}`" @click="emit('edit', d)">Edit</button>
        <button type="button" class="btn-danger btn-sm" :disabled="busyId === d.id" :aria-label="`Delete ${d.name}`" @click="emit('remove', d)">
          Delete
        </button>
      </div>
    </li>
  </ul>
</template>
