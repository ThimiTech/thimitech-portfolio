<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import Modal from "../ui/Modal.vue";
import {
  ATTACHMENT_ACCEPT,
  ATTACHMENT_MAX_BYTES,
  CATEGORIES,
  downloadAttachment,
  drfErrors,
  fromNptInput,
  toNptInput,
  type Audience,
  type Category,
  type Department,
  type HttpError,
  type Notice,
} from "./notices";

const props = defineProps<{ open: boolean; notice: Notice | null }>();
const emit = defineEmits<{ close: []; saved: [notice: Notice, created: boolean] }>();

const { user, hasRole } = useAuth();
const isHR = computed(() => hasRole("hr_admin"));

const form = reactive({
  title: "",
  body: "",
  category: "general" as Category,
  audience: "all" as Audience,
  department_id: "" as number | "",
  pinned: false,
  publish_at: "",
  expires_at: "",
  remove_attachment: false,
});
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const errors = ref<Record<string, string>>({});
const saving = ref(false);

const departments = ref<Department[]>([]);
const deptError = ref("");
async function loadDepartments() {
  if (departments.value.length) return;
  deptError.value = "";
  try {
    departments.value = (await api.get<Department[]>("org/departments/")).data;
  } catch {
    deptError.value = "Could not load departments.";
  }
}

// Managers may only post to departments they manage; HR may post anywhere.
const allowedDepts = computed(() =>
  isHR.value ? departments.value : departments.value.filter((d) => d.manager?.id === user.value?.id),
);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    const n = props.notice;
    errors.value = {};
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
    Object.assign(form, {
      title: n?.title ?? "",
      body: n?.body ?? "",
      category: n?.category ?? "general",
      audience: n?.audience ?? (isHR.value ? "all" : "department"),
      department_id: n?.department?.id ?? "",
      pinned: n?.pinned ?? false,
      publish_at: toNptInput(n?.publish_at ?? null),
      expires_at: toNptInput(n?.expires_at ?? null),
      remove_attachment: false,
    });
    loadDepartments().then(() => {
      if (form.audience === "department" && form.department_id === "" && allowedDepts.value.length === 1) {
        form.department_id = allowedDepts.value[0]!.id;
      }
    });
  },
);

function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] ?? null;
  delete errors.value.attachment;
  if (f && f.size > ATTACHMENT_MAX_BYTES) {
    errors.value.attachment = "Attachment must be 10 MB or smaller.";
    (e.target as HTMLInputElement).value = "";
    file.value = null;
    return;
  }
  file.value = f;
}

async function submit() {
  errors.value = {};
  if (form.publish_at && form.expires_at && form.expires_at <= form.publish_at) {
    errors.value.expires_at = "Expiry must be after the publish time.";
    return;
  }
  const fd = new FormData();
  fd.append("title", form.title.trim());
  fd.append("body", form.body);
  fd.append("category", form.category);
  fd.append("audience", form.audience);
  if (form.audience === "department") fd.append("department_id", String(form.department_id));
  if (isHR.value) fd.append("pinned", String(form.pinned));
  if (form.publish_at) fd.append("publish_at", fromNptInput(form.publish_at));
  fd.append("expires_at", form.expires_at ? fromNptInput(form.expires_at) : "");
  if (file.value) fd.append("attachment", file.value);
  else if (form.remove_attachment) fd.append("remove_attachment", "true");

  saving.value = true;
  try {
    const n = props.notice;
    const { data } = n ? await api.patch<Notice>(`notices/${n.id}/`, fd) : await api.post<Notice>("notices/", fd);
    emit("saved", data, !n);
  } catch (err) {
    const e = err as HttpError;
    const d = e?.response?.data;
    errors.value = d && typeof d === "object" ? drfErrors(d) : { detail: "Could not save. Check your connection and try again." };
  } finally {
    saving.value = false;
  }
}

const scheduled = computed(() => !!form.publish_at && new Date(fromNptInput(form.publish_at)).getTime() > Date.now());
// Mirrors views.email_urgent: each urgent notice is emailed once, when it is (or goes) live.
const urgentHint = computed(() =>
  props.notice
    ? "An urgent notice is emailed once. If this one hasn't been emailed and went live within the last day, it goes out within 5 minutes."
    : scheduled.value
      ? "Urgent: emailed to the audience within 5 minutes of going live."
      : "Urgent: emailed to the audience as soon as it's published.",
);

async function downloadCurrent() {
  if (!props.notice) return;
  delete errors.value.attachment;
  try {
    await downloadAttachment(props.notice);
  } catch {
    errors.value.attachment = "Could not download the current attachment.";
  }
}

const generalError = computed(() => errors.value.detail ?? errors.value.non_field_errors ?? "");
</script>

<template>
  <Modal :open="open" :title="notice ? 'Edit notice' : 'New notice'" width="max-w-2xl" @close="emit('close')">
    <form id="notice-form" class="grid gap-4" novalidate @submit.prevent="submit">
      <p v-if="generalError" role="alert" class="rounded-lg border border-rust/30 bg-rust/5 px-3 py-2 text-sm text-rust">
        {{ generalError }}
      </p>

      <div class="field">
        <label for="nc-title" class="ledger-label">Title</label>
        <input
          id="nc-title"
          v-model="form.title"
          class="input"
          maxlength="200"
          required
          :aria-invalid="!!errors.title"
          aria-describedby="nc-title-err"
        />
        <p v-if="errors.title" id="nc-title-err" class="text-xs text-rust">{{ errors.title }}</p>
      </div>

      <div class="field">
        <label for="nc-body" class="ledger-label">Body</label>
        <textarea
          id="nc-body"
          v-model="form.body"
          class="input min-h-36 resize-y"
          rows="6"
          required
          :aria-invalid="!!errors.body"
          aria-describedby="nc-body-err"
        />
        <p v-if="errors.body" id="nc-body-err" class="text-xs text-rust">{{ errors.body }}</p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="field">
          <label for="nc-cat" class="ledger-label">Category</label>
          <select id="nc-cat" v-model="form.category" class="input">
            <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
          <p v-if="form.category === 'urgent'" class="text-xs text-ink/55">{{ urgentHint }}</p>
          <p v-if="errors.category" class="text-xs text-rust">{{ errors.category }}</p>
        </div>

        <fieldset class="field">
          <legend class="ledger-label mb-1.5">Audience</legend>
          <div class="flex gap-4 py-1.5 text-sm">
            <label class="flex items-center gap-2" :class="!isHR && 'opacity-50'">
              <input v-model="form.audience" type="radio" value="all" class="accent-flag" :disabled="!isHR" />
              Everyone
            </label>
            <label class="flex items-center gap-2">
              <input v-model="form.audience" type="radio" value="department" class="accent-flag" />
              Department
            </label>
          </div>
          <p v-if="!isHR" class="text-xs text-ink/50">Managers post to departments they manage.</p>
          <p v-if="errors.audience" class="text-xs text-rust">{{ errors.audience }}</p>
        </fieldset>
      </div>

      <div v-if="form.audience === 'department'" class="field">
        <label for="nc-dept" class="ledger-label">Department</label>
        <select
          id="nc-dept"
          v-model="form.department_id"
          class="input"
          :aria-invalid="!!errors.department_id"
          aria-describedby="nc-dept-err"
        >
          <option value="" disabled>Choose a department</option>
          <option v-for="d in allowedDepts" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <p v-if="deptError" class="text-xs text-rust">
          {{ deptError }} <button type="button" class="underline" @click="loadDepartments">Retry</button>
        </p>
        <p v-else-if="!allowedDepts.length && departments.length" class="text-xs text-ink/55">
          You don't manage any department yet.
        </p>
        <p v-if="errors.department_id" id="nc-dept-err" class="text-xs text-rust">{{ errors.department_id }}</p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="field">
          <label for="nc-pub" class="ledger-label">Publish at (NPT)</label>
          <input id="nc-pub" v-model="form.publish_at" type="datetime-local" class="input font-mono" aria-describedby="nc-pub-hint" />
          <p id="nc-pub-hint" class="text-xs text-ink/50">Leave empty to publish now. A future time schedules it.</p>
          <p v-if="errors.publish_at" class="text-xs text-rust">{{ errors.publish_at }}</p>
        </div>
        <div class="field">
          <label for="nc-exp" class="ledger-label">Expires at (NPT)</label>
          <input
            id="nc-exp"
            v-model="form.expires_at"
            type="datetime-local"
            class="input font-mono"
            :min="form.publish_at || undefined"
            :aria-invalid="!!errors.expires_at"
            aria-describedby="nc-exp-err"
          />
          <p v-if="errors.expires_at" id="nc-exp-err" class="text-xs text-rust">{{ errors.expires_at }}</p>
          <p v-else class="text-xs text-ink/50">Optional. Hidden from the board after this.</p>
        </div>
      </div>

      <div class="field">
        <label for="nc-file" class="ledger-label">Attachment</label>
        <p v-if="notice?.attachment && !file" class="flex flex-wrap items-center gap-3 text-xs">
          <button
            type="button"
            class="font-mono text-river underline focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none"
            :class="form.remove_attachment && 'line-through opacity-60'"
            :aria-label="`Download current attachment ${notice.attachment_name ?? ''}`"
            @click="downloadCurrent"
          >
            {{ notice.attachment_name }}
          </button>
          <label class="flex items-center gap-1.5 text-ink/60">
            <input v-model="form.remove_attachment" type="checkbox" class="accent-rust" /> Remove
          </label>
        </p>
        <input
          id="nc-file"
          ref="fileInput"
          type="file"
          :accept="ATTACHMENT_ACCEPT"
          class="input file:mr-3 file:rounded-full file:border-0 file:bg-panel file:px-3 file:py-1 file:text-xs file:text-ink"
          aria-describedby="nc-file-hint"
          @change="onFile"
        />
        <p id="nc-file-hint" class="text-xs text-ink/50">PDF, image, DOCX or XLSX · up to 10 MB{{ notice?.attachment ? " · replaces the current file" : "" }}</p>
        <p v-if="errors.attachment" class="text-xs text-rust">{{ errors.attachment }}</p>
      </div>

      <label v-if="isHR" class="flex items-center gap-2 text-sm">
        <input v-model="form.pinned" type="checkbox" class="accent-flag" />
        Pin to the top of the board
      </label>
      <p v-if="errors.pinned" class="text-xs text-rust">{{ errors.pinned }}</p>
    </form>

    <template #footer>
      <button type="button" class="btn-ghost btn-sm" @click="emit('close')">Cancel</button>
      <button type="submit" form="notice-form" class="btn-primary btn-sm" :disabled="saving || !form.title.trim() || !form.body.trim()">
        {{ saving ? "Saving…" : notice ? "Save changes" : scheduled ? "Schedule" : "Publish" }}
      </button>
    </template>
  </Modal>
</template>
