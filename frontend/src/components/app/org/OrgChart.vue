<script setup lang="ts">
import { RouterLink } from "vue-router";
import Avatar from "../ui/Avatar.vue";
import OrgTreeNode from "./OrgTreeNode.vue";
import type { Structure } from "./org";

defineProps<{ structure: Structure; orgName: string; meId?: number }>();
</script>

<template>
  <div>
    <!-- Root marker -->
    <div class="flex items-center gap-2.5">
      <span class="inline-flex h-7 w-7 items-center justify-center rounded-full border border-ink/20 bg-ink font-display text-xs text-paper" aria-hidden="true">
        {{ orgName.slice(0, 1) }}
      </span>
      <span class="font-display text-base text-ink">{{ orgName }}</span>
      <span class="readout text-[11px] text-ink/40">· {{ structure.departments.length }} top-level</span>
    </div>

    <ul class="org-tree" :aria-label="`${orgName} departments`">
      <OrgTreeNode v-for="n in structure.departments" :key="n.id" :node="n" :me-id="meId" />

      <li v-if="structure.unassigned.length" class="org-branch">
        <article class="inline-block w-full max-w-xl rounded-xl border border-dashed border-ink/20 p-3.5 sm:p-4" aria-label="Unassigned staff">
          <h3 class="ledger-label">Unassigned · {{ structure.unassigned.length }}</h3>
          <ul class="mt-2.5 flex flex-wrap gap-x-4 gap-y-2">
            <li v-for="m in structure.unassigned" :key="m.id">
              <RouterLink :to="{ name: 'app-person', params: { id: m.id } }" class="flex items-center gap-2 text-sm text-ink/80 hover:underline">
                <Avatar :name="m.full_name" :photo="m.photo" :size="22" />{{ m.full_name }}
              </RouterLink>
            </li>
          </ul>
        </article>
      </li>
    </ul>
  </div>
</template>

<style>
/* Surveyor's tree: dashed hairline trunk, solid tick into each node. Works at any depth and width. */
.org-tree {
  margin: 0;
  padding: 0 0 0 0.875rem;
  list-style: none;
}
.org-branch {
  position: relative;
  padding: 0.75rem 0 0 1.5rem;
}
.org-branch::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-left: 1px dashed color-mix(in srgb, var(--color-ink) 25%, transparent);
}
.org-branch:last-child::before {
  bottom: auto;
  height: 2.1rem;
}
.org-branch::after {
  content: "";
  position: absolute;
  left: 0;
  top: 2.1rem;
  width: 1.25rem;
  border-top: 1px solid color-mix(in srgb, var(--color-river) 55%, transparent);
}
</style>
