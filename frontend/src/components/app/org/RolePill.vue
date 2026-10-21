<script setup lang="ts">
import type { Role } from "@/stores/auth";
import { ROLE_LABEL } from "./org";

defineProps<{ role: Role }>();

// Rank reads left-to-right as more filled pips; colour is never the only signal.
const PIPS: Record<Role, number> = { guest: 0, employee: 1, manager: 2, hr_admin: 3, super_admin: 4 };
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10.5px] tracking-[0.08em] whitespace-nowrap uppercase"
    :class="
      role === 'guest'
        ? 'border-dashed border-ink/25 text-ink/55'
        : role === 'super_admin' || role === 'hr_admin'
          ? 'border-river/40 bg-river/10 text-river'
          : 'border-ink/15 bg-ink/[0.04] text-ink/70'
    "
  >
    <span class="flex gap-px" aria-hidden="true">
      <span
        v-for="i in 4"
        :key="i"
        class="h-1.5 w-[3px] rounded-[1px]"
        :class="i <= PIPS[role] ? 'bg-current' : 'bg-current/20'"
      />
    </span>
    {{ ROLE_LABEL[role] }}
  </span>
</template>
