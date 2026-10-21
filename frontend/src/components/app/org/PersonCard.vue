<script setup lang="ts">
import { RouterLink } from "vue-router";
import Avatar from "../ui/Avatar.vue";
import StatusPill from "../ui/StatusPill.vue";
import RolePill from "./RolePill.vue";
import type { Person } from "./org";

defineProps<{ person: Person; manage?: boolean; isSelf?: boolean; busy?: boolean }>();
const emit = defineEmits<{ onboard: []; toggleActive: [] }>();
</script>

<template>
  <article
    class="panel group relative flex h-full flex-col p-4 transition-colors focus-within:border-river/40 hover:border-ink/25"
    :class="person.is_active ? '' : 'bg-panel/40'"
  >
    <div class="flex items-start gap-3">
      <Avatar :name="person.full_name || person.email" :photo="person.photo" :size="48" />
      <div class="min-w-0 flex-1">
        <h3 class="truncate font-display text-[17px] leading-snug text-ink">
          <RouterLink
            :to="{ name: 'app-person', params: { id: person.id } }"
            class="outline-none after:absolute after:inset-0 after:rounded-xl after:content-[''] focus-visible:after:ring-2 focus-visible:after:ring-flag/40"
          >
            {{ person.full_name || person.email }}
          </RouterLink>
        </h3>
        <p class="truncate text-sm text-ink/60">{{ person.designation || (person.role === "guest" ? "Applicant" : "—") }}</p>
        <p class="mt-0.5 truncate font-mono text-[11px] tracking-wide text-ink/45 uppercase">
          <span aria-hidden="true">⌖ </span>{{ person.department?.name ?? "Unassigned" }}
        </p>
      </div>
    </div>

    <div class="mt-3 flex flex-wrap items-center gap-1.5">
      <RolePill :role="person.role" />
      <StatusPill v-if="!person.is_active" status="inactive" label="Inactive" />
      <span v-if="isSelf" class="font-mono text-[10.5px] tracking-wide text-flag uppercase">You</span>
    </div>

    <div class="flex-1" />
    <div class="mt-4 flex flex-wrap items-center gap-1.5 border-t border-dashed border-ink/10 pt-3">
      <a
        :href="`mailto:${person.email}`"
        class="relative z-10 inline-flex h-8 w-8 items-center justify-center rounded-full border border-ink/15 text-ink/60 hover:bg-panel hover:text-ink focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none"
        :aria-label="`Email ${person.full_name || person.email}`"
        :title="person.email"
      >
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 4h16v16H4z" /><path d="m4 6 8 7 8-7" /></svg>
      </a>
      <a
        v-if="person.phone"
        :href="`tel:${person.phone}`"
        class="relative z-10 inline-flex h-8 w-8 items-center justify-center rounded-full border border-ink/15 text-ink/60 hover:bg-panel hover:text-ink focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none"
        :aria-label="`Call ${person.full_name} at ${person.phone}`"
        :title="person.phone"
      >
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z" /></svg>
      </a>
      <span class="readout ml-1 truncate text-[11px] text-ink/45">{{ person.phone || person.email }}</span>

      <div v-if="manage && !isSelf" class="relative z-10 ml-auto flex gap-1.5">
        <button
          v-if="person.role === 'guest' && person.is_active"
          type="button"
          class="btn-ink btn-sm"
          :disabled="busy"
          :aria-label="`Onboard ${person.full_name || person.email} as employee`"
          @click="emit('onboard')"
        >
          Onboard
        </button>
        <button
          type="button"
          class="btn-sm"
          :class="person.is_active ? 'btn-danger' : 'btn-ghost'"
          :disabled="busy"
          :aria-label="`${person.is_active ? 'Deactivate' : 'Reactivate'} ${person.full_name || person.email}`"
          @click="emit('toggleActive')"
        >
          {{ person.is_active ? "Deactivate" : "Reactivate" }}
        </button>
      </div>
    </div>
  </article>
</template>
