<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
defineOptions({ name: "AppModal" });

const props = withDefaults(defineProps<{ open: boolean; title: string; width?: string }>(), {
  width: "max-w-lg",
});
const emit = defineEmits<{ close: [] }>();

const dialog = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;

function onKey(e: KeyboardEvent) {
  const dialogs = document.querySelectorAll('[role="dialog"]');
  if (dialogs[dialogs.length - 1] !== dialog.value) return;
  if (e.key === "Escape") emit("close");
  if (e.key === 'Tab' && dialog.value) {
    const focusable = [...dialog.value.querySelectorAll<HTMLElement>('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previousFocus = document.activeElement as HTMLElement | null;
      document.addEventListener("keydown", onKey);
      await nextTick();
      dialog.value?.querySelector<HTMLElement>("input, select, textarea, button:not([data-close])")?.focus();
    } else {
      document.removeEventListener("keydown", onKey);
      previousFocus?.focus();
    }
  },
  { immediate: true },
);
onBeforeUnmount(() => { document.removeEventListener("keydown", onKey); if (props.open) previousFocus?.focus(); });
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[10000] flex items-end justify-center bg-scrim/60 p-0 backdrop-blur-[2px] sm:items-center sm:p-4"
      @click.self="emit('close')"
    >
      <div
        ref="dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        class="rise max-h-[92vh] w-full overflow-y-auto rounded-t-2xl border border-ink/10 bg-sheet shadow-2xl sm:rounded-2xl"
        :class="width"
      >
        <div class="panel-head sticky top-0 z-10 bg-sheet">
          <h2 class="font-display text-lg font-medium">{{ title }}</h2>
          <button
            data-close
            class="rounded-md p-1 text-ink/50 hover:bg-panel hover:text-ink"
            aria-label="Close"
            @click="emit('close')"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <div class="p-5">
          <slot />
        </div>
        <div v-if="$slots.footer" class="flex justify-end gap-2 border-t border-dashed border-ink/15 px-5 py-3.5">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
