<script setup lang="ts">
import { ref, watch } from "vue";
import AuthForm from "./auth/AuthForm.vue";

// Landing-page sign-in dialog (opened from the public navbars). The full-page
// version lives at /login and /register (pages/AuthPage.vue).
defineOptions({ name: "LoginDialog" });
const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: []; loginSuccess: [] }>();

const mode = ref<"login" | "signup">("login");
const dialog = ref<HTMLElement | null>(null);

function close() {
  emit("close");
  mode.value = "login";
}
function done() {
  emit("loginSuccess");
  close();
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") close();
}
watch(
  () => props.open,
  (o) => {
    if (o) {
      document.addEventListener("keydown", onKey);
      setTimeout(() => dialog.value?.querySelector<HTMLElement>("input")?.focus());
    } else document.removeEventListener("keydown", onKey);
  },
);
</script>

<template>
  <div v-if="props.open" class="fixed inset-0 z-[10000] flex items-center justify-center bg-scrim/60 px-4 backdrop-blur-sm" @click.self="close">
    <div
      ref="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-title"
      class="max-h-[94vh] w-full max-w-sm overflow-y-auto rounded-2xl border border-ink/10 bg-paper p-7 shadow-xl"
    >
      <div class="flex items-center justify-between">
        <h2 id="login-title" class="font-display text-xl font-semibold text-ink">
          {{ mode === "login" ? "Sign in" : "Create account" }}
        </h2>
        <button type="button" aria-label="Close" class="rounded-md p-1 text-ink/50 hover:bg-panel hover:text-ink" @click="close">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>
      <p class="mt-1 mb-6 text-sm text-ink/60">
        {{ mode === "login" ? "Staff and applicants sign in here." : "Create an account to apply for open roles." }}
      </p>
      <AuthForm :mode="mode" id-prefix="modal" @switch="mode = $event" @done="done" />
    </div>
  </div>
</template>
