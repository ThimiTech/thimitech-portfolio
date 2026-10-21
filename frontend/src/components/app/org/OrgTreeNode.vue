<script setup lang="ts">
// One department in the org chart; renders its sub-departments recursively.
// Connectors: each <li> draws a dashed vertical rule + a horizontal tick (see .org-branch in OrgChart).
import { computed } from "vue";
import { RouterLink } from "vue-router";
import Avatar from "../ui/Avatar.vue";
import type { StructureNode } from "./org";

const props = defineProps<{ node: StructureNode; meId?: number }>();

// Manager is shown separately; don't repeat them in the crew row.
const crew = computed(() => props.node.members.filter((m) => m.id !== props.node.manager?.id));
const headcount = computed(() => props.node.members.length);
</script>

<template>
  <li class="org-branch">
    <article class="panel inline-block w-full max-w-xl p-3.5 sm:p-4" :aria-label="`${node.name} department`">
      <header class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 class="font-display text-[17px] leading-snug font-medium text-ink">{{ node.name }}</h3>
        <span class="readout text-[11px] text-ink/45">
          {{ String(headcount).padStart(2, "0") }} staff<template v-if="node.children.length"> · {{ node.children.length }} sub</template>
        </span>
      </header>
      <p v-if="node.description" class="mt-0.5 line-clamp-2 text-xs text-ink/55">{{ node.description }}</p>

      <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-3 border-t border-dashed border-ink/10 pt-3">
        <RouterLink
          v-if="node.manager"
          :to="{ name: 'app-person', params: { id: node.manager.id } }"
          class="group flex min-w-0 items-center gap-2 rounded-full pr-2 outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
        >
          <Avatar :name="node.manager.full_name" :photo="node.manager.photo" :size="30" />
          <span class="min-w-0 leading-tight">
            <span class="ledger-label block text-[9.5px]">Lead</span>
            <span class="block truncate text-sm text-ink group-hover:underline">
              {{ node.manager.full_name }}<span v-if="node.manager.id === meId" class="ml-1 font-mono text-[10px] text-flag uppercase">you</span>
            </span>
          </span>
        </RouterLink>
        <span v-else class="ledger-label text-ink/35">No lead assigned</span>

        <ul v-if="crew.length" class="flex flex-wrap items-center gap-1" :aria-label="`${node.name} members`">
          <li v-for="m in crew" :key="m.id">
            <RouterLink
              :to="{ name: 'app-person', params: { id: m.id } }"
              class="block rounded-full outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
              :aria-label="`${m.full_name}${m.designation ? ', ' + m.designation : ''}${m.id === meId ? ' (you)' : ''}`"
              :title="m.designation ? `${m.full_name} — ${m.designation}` : m.full_name"
            >
              <Avatar :name="m.full_name" :photo="m.photo" :size="26" :class="m.id === meId ? 'outline-2 outline-offset-1 outline-flag' : ''" />
            </RouterLink>
          </li>
        </ul>
      </div>
    </article>

    <ul v-if="node.children.length" class="org-tree" :aria-label="`Sub-departments of ${node.name}`">
      <OrgTreeNode v-for="c in node.children" :key="c.id" :node="c" :me-id="meId" />
    </ul>
  </li>
</template>
