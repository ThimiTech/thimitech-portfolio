<script setup lang="ts">
// Create a person (HR) or edit one. Field set follows the backend rules:
// self -> contact fields + photo; hr_admin+ -> everything (role limited by grant rules, never own role).
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import { useAuth, type Role } from "@/stores/auth";
import Modal from "../ui/Modal.vue";
import Avatar from "../ui/Avatar.vue";
import FormField from "./FormField.vue";
import {
  EMPLOYMENT_LABEL, MAX_IMAGE_BYTES, ROLE_LABEL, apiError, canManage, diff, grantableRoles,
  type Department, type EmploymentType, type Person,
} from "./org";

const props = defineProps<{ open: boolean; person?: Person | null }>();
const emit = defineEmits<{ close: []; saved: [person: Person] }>();

const { user } = useAuth();

const creating = computed(() => !props.person);
const isSelf = computed(() => !!props.person && props.person.id === user.value?.id);
const hrScope = computed(() =>
  creating.value ? !!user.value && grantableRoles(user.value.role).length > 0 : canManage(user.value, props.person!),
);
const roleEditable = computed(() => hrScope.value && !isSelf.value);
const roleOptions = computed<Role[]>(() => {
  const opts = user.value ? grantableRoles(user.value.role) : [];
  const cur = props.person?.role;
  return cur && !opts.includes(cur) ? [cur, ...opts] : opts;
});

const blank = () => ({
  first_name: "", last_name: "", email: "", password: "", role: "employee" as Role,
  department_id: null as number | null, designation: "", employment_type: "full_time" as EmploymentType,
  join_date: "", employee_code: "", date_of_birth: "", phone: "", address: "",
  emergency_contact_name: "", emergency_contact_phone: "", bio: "", skills: "",
});
const form = reactive(blank());
const photoFile = ref<File | null>(null);
const photoPreview = ref<string | null>(null);
const removePhoto = ref(false);
const saving = ref(false);
const error = ref("");
const fieldErrors = ref<Record<string, string>>({});
const departments = ref<Department[]>([]);
const created = ref<Person | null>(null);

function fromPerson(p: Person) {
  return {
    first_name: p.first_name, last_name: p.last_name, email: p.email, password: "", role: p.role,
    department_id: p.department?.id ?? null, designation: p.designation ?? "",
    employment_type: p.employment_type ?? "full_time", join_date: p.join_date ?? "",
    employee_code: p.employee_code ?? "", date_of_birth: p.date_of_birth ?? "", phone: p.phone ?? "",
    address: p.address ?? "", emergency_contact_name: p.emergency_contact_name ?? "",
    emergency_contact_phone: p.emergency_contact_phone ?? "", bio: p.bio ?? "", skills: (p.skills ?? []).join(", "),
  };
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    Object.assign(form, props.person ? fromPerson(props.person) : blank());
    photoFile.value = null;
    photoPreview.value = null;
    removePhoto.value = false;
    created.value = null;
    error.value = "";
    fieldErrors.value = {};
    if (hrScope.value && !departments.value.length) {
      try {
        departments.value = (await api.get<Department[]>("org/departments/")).data;
      } catch {
        /* the select falls back to the current department only */
      }
    }
  },
  { immediate: true },
);

const currentPhoto = computed(() =>
  photoPreview.value ?? (removePhoto.value ? null : (props.person?.photo ?? null)),
);

function onPhoto(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (!f) return;
  if (f.size > MAX_IMAGE_BYTES) {
    fieldErrors.value = { ...fieldErrors.value, photo: "Image must be 3 MB or smaller." };
    return;
  }
  delete fieldErrors.value.photo;
  photoFile.value = f;
  removePhoto.value = false;
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value);
  photoPreview.value = URL.createObjectURL(f);
}

function clearPhoto() {
  photoFile.value = null;
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value);
  photoPreview.value = null;
  removePhoto.value = true;
}

const SELF_KEYS = [
  "first_name", "last_name", "phone", "address", "emergency_contact_name", "emergency_contact_phone", "bio", "skills",
] as const;
const HR_KEYS = [
  "email", "role", "department_id", "designation", "employment_type", "join_date", "employee_code", "date_of_birth",
] as const;

function payloadFrom(src: ReturnType<typeof blank>) {
  const keys: string[] = [...SELF_KEYS, ...(hrScope.value ? HR_KEYS : [])];
  const out: Record<string, unknown> = {};
  for (const k of keys) {
    if (k === "role" && !roleEditable.value) continue;
    const v = src[k as keyof typeof src];
    if (k === "skills") out.skills = String(v).split(",").map((s) => s.trim()).filter(Boolean);
    else if (k === "join_date" || k === "date_of_birth") out[k] = v || null;
    else if (typeof v === "string") out[k] = v.trim();
    else out[k] = v;
  }
  return out;
}

async function submit() {
  saving.value = true;
  error.value = "";
  fieldErrors.value = {};
  try {
    let saved: Person;
    const body = payloadFrom(form);
    if (creating.value) {
      if (form.password) body.password = form.password;
      // On a retry after a failed photo upload the person already exists: only re-send the photo.
      created.value ??= (await api.post<Person>("org/people/", body)).data;
      saved = created.value;
    } else {
      const p = props.person!;
      const url = isSelf.value ? "org/people/me/" : `org/people/${p.id}/`;
      const changes: Record<string, unknown> = diff(body, payloadFrom(fromPerson(p)));
      if (removePhoto.value && p.photo) changes.photo = null;
      if (form.password && !isSelf.value) changes.password = form.password;
      saved = Object.keys(changes).length ? (await api.patch<Person>(url, changes)).data : p;
    }
    if (photoFile.value) {
      const fd = new FormData();
      fd.append("photo", photoFile.value);
      const url = isSelf.value ? "org/people/me/" : `org/people/${saved.id}/`;
      saved = (await api.patch<Person>(url, fd)).data;
    }
    emit("saved", saved);
  } catch (e) {
    const err = apiError(e);
    error.value = created.value
      ? `${created.value.full_name || created.value.email} was added, but the photo was not uploaded: ${err.message} Pick another image and retry, or close to continue without it.`
      : err.message;
    fieldErrors.value = err.fields;
  } finally {
    saving.value = false;
  }
}

// Closing after a partial create still hands the new person to the parent.
function close() {
  if (created.value) emit("saved", created.value);
  else emit("close");
}

const title = computed(() =>
  creating.value ? "Add a person" : isSelf.value ? "Edit my profile" : `Edit ${props.person?.full_name || "profile"}`,
);
const describe = (id: string) => `${id}-msg`;
</script>

<template>
  <Modal :open="open" :title="title" width="max-w-2xl" @close="close">
    <form id="person-form" class="grid gap-6" novalidate @submit.prevent="submit">
      <p v-if="error" class="rounded-lg border border-rust/25 bg-rust/5 px-3 py-2 text-sm text-rust" role="alert">{{ error }}</p>

      <!-- Photo -->
      <section class="flex items-center gap-4">
        <Avatar :name="`${form.first_name} ${form.last_name}`.trim() || form.email || '?'" :photo="currentPhoto" :size="64" />
        <div class="grid gap-1.5">
          <div class="flex flex-wrap gap-2">
            <label class="btn-ghost btn-sm cursor-pointer focus-within:ring-2 focus-within:ring-flag/40">
              <input type="file" accept="image/*" class="sr-only" aria-describedby="pf-photo-msg" @change="onPhoto" />
              {{ currentPhoto ? "Replace photo" : "Upload photo" }}
            </label>
            <button v-if="currentPhoto" type="button" class="btn-ghost btn-sm" @click="clearPhoto">Remove</button>
          </div>
          <p id="pf-photo-msg" class="text-xs" :class="fieldErrors.photo ? 'text-rust' : 'text-ink/50'">
            {{ fieldErrors.photo ?? "JPG or PNG, up to 3 MB." }}
          </p>
        </div>
      </section>

      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="ledger-label mb-3 w-full border-b border-dashed border-ink/15 pb-2">Identity</legend>
        <FormField id="pf-first" label="First name" :error="fieldErrors.first_name">
          <input id="pf-first" v-model="form.first_name" class="input" autocomplete="given-name" :aria-describedby="describe('pf-first')" />
        </FormField>
        <FormField id="pf-last" label="Last name" :error="fieldErrors.last_name">
          <input id="pf-last" v-model="form.last_name" class="input" autocomplete="family-name" :aria-describedby="describe('pf-last')" />
        </FormField>
        <FormField v-if="hrScope" id="pf-email" label="Work email" :error="fieldErrors.email" class="sm:col-span-2">
          <input id="pf-email" v-model="form.email" type="email" required class="input" autocomplete="off" :aria-describedby="describe('pf-email')" />
        </FormField>
        <FormField
          v-if="creating || (hrScope && !isSelf)"
          id="pf-pass"
          :label="creating ? 'Initial password' : 'Reset password'"
          optional
          :error="fieldErrors.password"
          :hint="creating ? 'Leave blank and they cannot sign in until a password is set.' : 'Leave blank to keep their current password.'"
          class="sm:col-span-2"
        >
          <input id="pf-pass" v-model="form.password" type="password" class="input" autocomplete="new-password" :aria-describedby="describe('pf-pass')" />
        </FormField>
      </fieldset>

      <fieldset v-if="hrScope" class="grid gap-4 sm:grid-cols-2">
        <legend class="ledger-label mb-3 w-full border-b border-dashed border-ink/15 pb-2">Employment</legend>
        <FormField
          id="pf-role"
          label="Role"
          :error="fieldErrors.role"
          :hint="roleEditable ? undefined : isSelf ? 'You cannot change your own role.' : undefined"
        >
          <select id="pf-role" v-model="form.role" class="input" :disabled="!roleEditable" :aria-describedby="describe('pf-role')">
            <option v-for="r in roleOptions" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
            <option v-if="!roleOptions.includes(form.role)" :value="form.role">{{ ROLE_LABEL[form.role] }}</option>
          </select>
        </FormField>
        <FormField id="pf-dept" label="Department" :error="fieldErrors.department_id">
          <select id="pf-dept" v-model="form.department_id" class="input" :aria-describedby="describe('pf-dept')">
            <option :value="null">Unassigned</option>
            <option v-if="person?.department && !departments.length" :value="person.department.id">{{ person.department.name }}</option>
            <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </FormField>
        <FormField id="pf-desig" label="Designation" :error="fieldErrors.designation">
          <input id="pf-desig" v-model="form.designation" class="input" :aria-describedby="describe('pf-desig')" />
        </FormField>
        <FormField id="pf-type" label="Employment type" :error="fieldErrors.employment_type">
          <select id="pf-type" v-model="form.employment_type" class="input" :aria-describedby="describe('pf-type')">
            <option v-for="(label, k) in EMPLOYMENT_LABEL" :key="k" :value="k">{{ label }}</option>
          </select>
        </FormField>
        <FormField id="pf-code" label="Employee code" optional :error="fieldErrors.employee_code">
          <input id="pf-code" v-model="form.employee_code" class="input font-mono" :aria-describedby="describe('pf-code')" />
        </FormField>
        <FormField id="pf-join" label="Join date" optional :error="fieldErrors.join_date">
          <input id="pf-join" v-model="form.join_date" type="date" class="input" :aria-describedby="describe('pf-join')" />
        </FormField>
        <FormField id="pf-dob" label="Date of birth" optional :error="fieldErrors.date_of_birth">
          <input id="pf-dob" v-model="form.date_of_birth" type="date" class="input" :aria-describedby="describe('pf-dob')" />
        </FormField>
      </fieldset>

      <fieldset class="grid gap-4 sm:grid-cols-2">
        <legend class="ledger-label mb-3 w-full border-b border-dashed border-ink/15 pb-2">Contact &amp; emergency</legend>
        <FormField id="pf-phone" label="Phone" optional :error="fieldErrors.phone">
          <input id="pf-phone" v-model="form.phone" type="tel" class="input" autocomplete="tel" :aria-describedby="describe('pf-phone')" />
        </FormField>
        <FormField id="pf-addr" label="Address" optional :error="fieldErrors.address">
          <input id="pf-addr" v-model="form.address" class="input" autocomplete="street-address" :aria-describedby="describe('pf-addr')" />
        </FormField>
        <FormField id="pf-ecn" label="Emergency contact" optional :error="fieldErrors.emergency_contact_name">
          <input id="pf-ecn" v-model="form.emergency_contact_name" class="input" :aria-describedby="describe('pf-ecn')" />
        </FormField>
        <FormField id="pf-ecp" label="Emergency phone" optional :error="fieldErrors.emergency_contact_phone">
          <input id="pf-ecp" v-model="form.emergency_contact_phone" type="tel" class="input" :aria-describedby="describe('pf-ecp')" />
        </FormField>
      </fieldset>

      <fieldset class="grid gap-4">
        <legend class="ledger-label mb-3 w-full border-b border-dashed border-ink/15 pb-2">About</legend>
        <FormField id="pf-skills" label="Skills" optional :error="fieldErrors.skills" hint="Separate with commas, e.g. Django, QGIS, Field survey">
          <input id="pf-skills" v-model="form.skills" class="input" :aria-describedby="describe('pf-skills')" />
        </FormField>
        <FormField id="pf-bio" label="Bio" optional :error="fieldErrors.bio">
          <textarea id="pf-bio" v-model="form.bio" rows="4" class="input" :aria-describedby="describe('pf-bio')" />
        </FormField>
      </fieldset>
    </form>

    <template #footer>
      <button type="button" class="btn-ghost" @click="close">{{ created ? "Close" : "Cancel" }}</button>
      <button type="submit" form="person-form" class="btn-primary" :disabled="saving">
        {{ saving ? "Saving…" : creating ? "Add person" : "Save changes" }}
      </button>
    </template>
  </Modal>
</template>
