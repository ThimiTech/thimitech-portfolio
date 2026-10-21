<script setup lang="ts">
// Edit the organization profile (hr_admin+) or the work policy (super_admin only).
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import FormField from "./FormField.vue";
import { MAX_IMAGE_BYTES, WEEKDAYS, WEEKDAYS_LONG, apiError, diff, hhmm, type Organization } from "./org";

const props = defineProps<{ open: boolean; mode: "profile" | "policy"; org: Organization }>();
const emit = defineEmits<{ close: []; saved: [org: Organization] }>();

const PROFILE_KEYS = ["name", "tagline", "about", "email", "phone", "address", "website", "github", "linkedin", "youtube", "founded"] as const;
type ProfileKey = (typeof PROFILE_KEYS)[number];

const profile = reactive<Record<ProfileKey, string>>(Object.fromEntries(PROFILE_KEYS.map((k) => [k, ""])) as Record<ProfileKey, string>);
const policy = reactive({ work_start: "", work_end: "", late_grace_minutes: 0, weekend_days: [] as number[] });
const logo = ref<File | null>(null);
const saving = ref(false);
const error = ref("");
const fe = ref<Record<string, string>>({});

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    for (const k of PROFILE_KEYS) profile[k] = props.org[k] ?? "";
    Object.assign(policy, {
      work_start: hhmm(props.org.work_start),
      work_end: hhmm(props.org.work_end),
      late_grace_minutes: props.org.late_grace_minutes,
      weekend_days: [...props.org.weekend_days],
    });
    logo.value = null;
    error.value = "";
    fe.value = {};
  },
  { immediate: true },
);

function onLogo(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0] ?? null;
  if (f && f.size > MAX_IMAGE_BYTES) {
    fe.value = { ...fe.value, logo: "Logo must be 3 MB or smaller." };
    return;
  }
  delete fe.value.logo;
  logo.value = f;
}

function toggleDay(d: number) {
  const s = new Set(policy.weekend_days);
  if (s.has(d)) s.delete(d);
  else s.add(d);
  policy.weekend_days = [...s].sort();
}

async function submit() {
  saving.value = true;
  error.value = "";
  fe.value = {};
  try {
    let body: Record<string, unknown>;
    if (props.mode === "profile") {
      const next = Object.fromEntries(PROFILE_KEYS.map((k) => [k, k === "founded" ? profile[k] || null : profile[k].trim()]));
      body = diff(next, props.org as unknown as Record<string, unknown>);
    } else {
      body = diff(
        { ...policy, late_grace_minutes: Number(policy.late_grace_minutes) },
        { ...props.org, work_start: hhmm(props.org.work_start), work_end: hhmm(props.org.work_end) },
      );
    }
    let saved = props.org;
    if (Object.keys(body).length) saved = (await api.patch<Organization>("org/organization/", body)).data;
    if (logo.value) {
      const fd = new FormData();
      fd.append("logo", logo.value);
      saved = (await api.patch<Organization>("org/organization/", fd)).data;
    }
    emit("saved", saved);
  } catch (e) {
    const err = apiError(e);
    error.value = err.message;
    fe.value = err.fields;
  } finally {
    saving.value = false;
  }
}

const LABELS: Record<ProfileKey, string> = {
  name: "Name", tagline: "Tagline", about: "About", email: "Email", phone: "Phone", address: "Address",
  website: "Website", github: "GitHub", linkedin: "LinkedIn", youtube: "YouTube", founded: "Founded",
};
const URL_KEYS = new Set<ProfileKey>(["website", "github", "linkedin", "youtube"]);
const inputType = (k: ProfileKey) => (k === "founded" ? "date" : k === "email" ? "email" : k === "phone" ? "tel" : URL_KEYS.has(k) ? "url" : "text");
const title = computed(() => (props.mode === "profile" ? "Edit organization profile" : "Edit work policy"));
</script>

<template>
  <Modal :open="open" :title="title" width="max-w-2xl" @close="emit('close')">
    <form id="org-form" class="grid gap-5" novalidate @submit.prevent="submit">
      <p v-if="error" class="rounded-lg border border-rust/25 bg-rust/5 px-3 py-2 text-sm text-rust" role="alert">{{ error }}</p>

      <template v-if="mode === 'profile'">
        <div class="grid gap-4 sm:grid-cols-2">
          <template v-for="k in PROFILE_KEYS" :key="k">
            <FormField
              :id="`org-${k}`"
              :label="LABELS[k]"
              :optional="k !== 'name'"
              :error="fe[k]"
              :class="k === 'about' || k === 'tagline' || k === 'address' ? 'sm:col-span-2' : ''"
            >
              <textarea v-if="k === 'about'" :id="`org-${k}`" v-model="profile[k]" rows="4" class="input" :aria-describedby="`org-${k}-msg`" />
              <input
                v-else
                :id="`org-${k}`"
                v-model="profile[k]"
                :type="inputType(k)"
                :placeholder="URL_KEYS.has(k) ? 'https://' : undefined"
                class="input"
                :aria-describedby="`org-${k}-msg`"
              />
            </FormField>
          </template>
          <FormField id="org-logo" label="Logo" optional :error="fe.logo" hint="Square image, up to 3 MB." class="sm:col-span-2">
            <input id="org-logo" type="file" accept="image/*" class="input file:mr-3 file:rounded-full file:border-0 file:bg-panel file:px-3 file:py-1 file:text-xs" aria-describedby="org-logo-msg" @change="onLogo" />
          </FormField>
        </div>
      </template>

      <template v-else>
        <div class="grid gap-4 sm:grid-cols-3">
          <FormField id="pol-start" label="Work starts" :error="fe.work_start">
            <input id="pol-start" v-model="policy.work_start" type="time" required class="input readout" aria-describedby="pol-start-msg" />
          </FormField>
          <FormField id="pol-end" label="Work ends" :error="fe.work_end">
            <input id="pol-end" v-model="policy.work_end" type="time" required class="input readout" aria-describedby="pol-end-msg" />
          </FormField>
          <FormField id="pol-grace" label="Late grace (min)" :error="fe.late_grace_minutes">
            <input id="pol-grace" v-model.number="policy.late_grace_minutes" type="number" min="0" max="240" class="input readout" aria-describedby="pol-grace-msg" />
          </FormField>
        </div>
        <fieldset>
          <legend class="ledger-label mb-2">Weekend days</legend>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(d, i) in WEEKDAYS"
              :key="d"
              type="button"
              class="min-w-12 rounded-lg border px-3 py-2 font-mono text-xs uppercase transition-colors focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none"
              :class="policy.weekend_days.includes(i) ? 'border-flag bg-flag/10 text-flag' : 'border-ink/15 text-ink/60 hover:bg-panel'"
              :aria-pressed="policy.weekend_days.includes(i)"
              :aria-label="WEEKDAYS_LONG[i]"
              @click="toggleDay(i)"
            >
              {{ d }}<span v-if="policy.weekend_days.includes(i)" aria-hidden="true"> ✕</span>
            </button>
          </div>
          <p class="mt-2 text-xs" :class="fe.weekend_days ? 'text-rust' : 'text-ink/50'">
            {{ fe.weekend_days ?? "Weekend days are skipped when counting leave and marking absentees." }}
          </p>
        </fieldset>
      </template>
    </form>

    <template #footer>
      <button type="button" class="btn-ghost" @click="emit('close')">Cancel</button>
      <button type="submit" form="org-form" class="btn-primary" :disabled="saving">{{ saving ? "Saving…" : "Save" }}</button>
    </template>
  </Modal>
</template>
