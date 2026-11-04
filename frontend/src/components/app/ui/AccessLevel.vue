<script setup lang="ts">
// Access-level picker: offers only the levels at or below the viewer's own clearance.
import { computed } from "vue";
import { LEVEL_HINT, LEVEL_LABEL, useAuth, type Level } from "@/stores/auth";

const model = defineModel<Level>({ default: 1 });
withDefaults(defineProps<{ id?: string; compact?: boolean; disabled?: boolean }>(), { id: undefined });
const { user } = useAuth();
const levels = computed(() => ([1, 2, 3, 4] as Level[]).filter((l) => l <= (user.value?.clearance ?? 1) || l === model.value));
</script>

<template>
  <select
    :id="id"
    v-model.number="model"
    class="input"
    :class="compact && '!w-auto !py-1 text-xs'"
    :disabled="disabled || levels.length < 2"
    :aria-label="id ? undefined : 'Access level'"
    :title="LEVEL_HINT[model]"
  >
    <option v-for="l in levels" :key="l" :value="l">{{ LEVEL_LABEL[l] }}</option>
  </select>
</template>
