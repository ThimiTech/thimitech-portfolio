<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import FormField from "./FormField.vue";
import { apiError, type Department, type Person } from "./org";

const props = defineProps<{ open: boolean; department?: Department | null; departments: Department[] }>();
const emit = defineEmits<{ close: []; saved: [dept: Department] }>();

const form = reactive({ name: "", description: "", parent: null as number | null, manager_id: null as number | null });
const staff = ref<Person[]>([]);
const saving = ref(false);
const error = ref("");
const fe = ref<Record<string, string>>({});

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    const d = props.department;
    Object.assign(form, {
      name: d?.name ?? "",
      description: d?.description ?? "",
      parent: d?.parent ?? null,
      manager_id: d?.manager?.id ?? null,
    });
    error.value = "";
    fe.value = {};
    if (!staff.value.length) {
      try {
        // Active staff only — the backend rejects guests and inactive users as managers.
        staff.value = (await api.get<Person[]>("org/people/", { params: { is_active: "true" } })).data;
      } catch {
        /* falls back to the current manager option */
      }
    }
  },
  { immediate: true },
);

/** A department can't sit under itself or one of its own sub-departments. */
const parentOptions = computed(() => {
  const self = props.department?.id;
  if (!self) return props.departments;
  const banned = new Set([self]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const d of props.departments) {
      if (d.parent !== null && banned.has(d.parent) && !banned.has(d.id)) {
        banned.add(d.id);
        grew = true;
      }
    }
  }
  return props.departments.filter((d) => !banned.has(d.id));
});

async function submit() {
  if (!form.name.trim()) {
    fe.value = { name: "Give the department a name." };
    return;
  }
  saving.value = true;
  error.value = "";
  fe.value = {};
  const body = { ...form, name: form.name.trim(), description: form.description.trim() };
  try {
    const d = props.department;
    const saved = d
      ? (await api.patch<Department>(`org/departments/${d.id}/`, body)).data
      : (await api.post<Department>("org/departments/", body)).data;
    emit("saved", saved);
  } catch (e) {
    const err = apiError(e);
    error.value = err.message;
    fe.value = err.fields;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal :open="open" :title="department ? `Edit ${department.name}` : 'New department'" @close="emit('close')">
    <form id="dept-form" class="grid gap-4" novalidate @submit.prevent="submit">
      <p v-if="error" class="rounded-lg border border-rust/25 bg-rust/5 px-3 py-2 text-sm text-rust" role="alert">{{ error }}</p>
      <FormField id="dept-name" label="Name" :error="fe.name">
        <input id="dept-name" v-model="form.name" required class="input" aria-describedby="dept-name-msg" />
      </FormField>
      <FormField id="dept-desc" label="Description" optional :error="fe.description">
        <textarea id="dept-desc" v-model="form.description" rows="3" class="input" aria-describedby="dept-desc-msg" />
      </FormField>
      <div class="grid gap-4 sm:grid-cols-2">
        <FormField id="dept-parent" label="Parent department" :error="fe.parent" hint="Leave empty for a top-level department.">
          <select id="dept-parent" v-model="form.parent" class="input" aria-describedby="dept-parent-msg">
            <option :value="null">— Top level —</option>
            <option v-for="d in parentOptions" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </FormField>
        <FormField id="dept-mgr" label="Manager" :error="fe.manager_id" hint="Approves this team's leave.">
          <select id="dept-mgr" v-model="form.manager_id" class="input" aria-describedby="dept-mgr-msg">
            <option :value="null">— No manager —</option>
            <option
              v-if="department?.manager && !staff.some((s) => s.id === department!.manager!.id)"
              :value="department.manager.id"
            >
              {{ department.manager.full_name }}
            </option>
            <option v-for="s in staff" :key="s.id" :value="s.id">
              {{ s.full_name || s.email }}{{ s.designation ? ` — ${s.designation}` : "" }}
            </option>
          </select>
        </FormField>
      </div>
    </form>
    <template #footer>
      <button type="button" class="btn-ghost" @click="emit('close')">Cancel</button>
      <button type="submit" form="dept-form" class="btn-primary" :disabled="saving">
        {{ saving ? "Saving…" : department ? "Save" : "Create department" }}
      </button>
    </template>
  </Modal>
</template>
