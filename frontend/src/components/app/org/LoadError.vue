<script setup lang="ts">
defineProps<{ message: string; busy?: boolean }>();
const emit = defineEmits<{ retry: [] }>();
</script>

<template>
  <div class="panel flex flex-col items-start gap-3 border-rust/25 p-5 sm:flex-row sm:items-center sm:justify-between" role="alert">
    <div class="flex items-start gap-3">
      <span class="mt-0.5 font-mono text-xs text-rust" aria-hidden="true">✕</span>
      <div>
        <p class="font-display text-base text-ink">Couldn't read this sheet</p>
        <p class="mt-0.5 text-sm text-ink/60">{{ message }}</p>
      </div>
    </div>
    <button type="button" class="btn-ghost btn-sm" :disabled="busy" @click="emit('retry')">
      {{ busy ? "Retrying…" : "Retry" }}
    </button>
  </div>
</template>
