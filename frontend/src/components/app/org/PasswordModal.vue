<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "@/components/app/ui/Modal.vue";
import FormField from "./FormField.vue";
import { apiError } from "./org";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: []; saved: [] }>();

const form = reactive({ current_password: "", new_password: "", confirm: "" });
const saving = ref(false);
const error = ref("");
const fieldErrors = ref<Record<string, string>>({});

watch(
  () => props.open,
  (o) => {
    if (!o) return;
    Object.assign(form, { current_password: "", new_password: "", confirm: "" });
    error.value = "";
    fieldErrors.value = {};
  },
);

async function submit() {
  error.value = "";
  fieldErrors.value = {};
  if (form.new_password !== form.confirm) {
    fieldErrors.value = { confirm: "The two new passwords don't match." };
    return;
  }
  saving.value = true;
  try {
    await api.post("org/people/me/password/", { current_password: form.current_password, new_password: form.new_password });
    emit("saved");
  } catch (e) {
    const err = apiError(e);
    error.value = err.message;
    fieldErrors.value = err.fields;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal :open="open" title="Change password" width="max-w-md" @close="emit('close')">
    <form id="pw-form" class="grid gap-4" novalidate @submit.prevent="submit">
      <FormField id="pw-current" label="Current password" :error="fieldErrors.current_password">
        <input id="pw-current" v-model="form.current_password" type="password" required class="input"
          autocomplete="current-password" aria-describedby="pw-current-msg" />
      </FormField>
      <FormField id="pw-new" label="New password" :error="fieldErrors.new_password" hint="At least 8 characters; not all numbers.">
        <input id="pw-new" v-model="form.new_password" type="password" required class="input"
          autocomplete="new-password" aria-describedby="pw-new-msg" />
      </FormField>
      <FormField id="pw-confirm" label="Repeat new password" :error="fieldErrors.confirm">
        <input id="pw-confirm" v-model="form.confirm" type="password" required class="input"
          autocomplete="new-password" aria-describedby="pw-confirm-msg" />
      </FormField>
      <p v-if="error" class="text-sm text-rust" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button type="button" class="btn-ghost btn-sm" @click="emit('close')">Cancel</button>
      <button type="submit" form="pw-form" class="btn-primary btn-sm"
        :disabled="saving || !form.current_password || !form.new_password || !form.confirm">
        {{ saving ? "Saving…" : "Change password" }}
      </button>
    </template>
  </Modal>
</template>
