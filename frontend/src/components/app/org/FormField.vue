<script setup lang="ts">
// Label + control + hint/error. The caller puts `:id="id"` and
// `:aria-describedby="`${id}-msg`"` on its control.
defineProps<{ id: string; label: string; error?: string; hint?: string; optional?: boolean }>();
</script>

<template>
  <div class="field">
    <label :for="id" class="ledger-label flex items-baseline justify-between gap-2">
      <span>{{ label }}</span>
      <span v-if="optional" class="normal-case tracking-normal text-ink/35">optional</span>
    </label>
    <slot />
    <p v-if="error" :id="`${id}-msg`" class="text-xs text-rust" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-msg`" class="text-xs text-ink/50">{{ hint }}</p>
  </div>
</template>
