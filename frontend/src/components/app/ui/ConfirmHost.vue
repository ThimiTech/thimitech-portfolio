<script setup lang="ts">
import Modal from "./Modal.vue";
import { confirmState, settleConfirm } from "./confirm";
</script>

<template>
  <Modal :open="confirmState.open" :title="confirmState.opts.title" width="max-w-md" @close="settleConfirm(false)">
    <p class="text-sm leading-relaxed text-ink-2">{{ confirmState.opts.body }}</p>
    <template #footer>
      <button type="button" class="btn-ghost btn-sm" @click="settleConfirm(false)">Keep it</button>
      <button
        type="button"
        class="btn-sm"
        :class="confirmState.opts.danger === false ? 'btn-primary' : 'btn-danger'"
        @click="settleConfirm(true)"
      >
        {{ confirmState.opts.confirmLabel ?? "Confirm" }}
      </button>
    </template>
  </Modal>
</template>
