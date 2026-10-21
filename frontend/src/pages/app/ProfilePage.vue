<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import api from "@/api/api";
import { toast } from "@/components/app/ui/toast";
import { useAuth } from "@/stores/auth";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import Avatar from "@/components/app/ui/Avatar.vue";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import StatusPill from "@/components/app/ui/StatusPill.vue";
import RolePill from "@/components/app/org/RolePill.vue";
import InfoPanel from "@/components/app/org/InfoPanel.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import PersonFormModal from "@/components/app/org/PersonFormModal.vue";
import PasswordModal from "@/components/app/org/PasswordModal.vue";
import { EMPLOYMENT_LABEL, apiError, canManage, fmtDate, tenure, type InfoRow, type Person } from "@/components/app/org/org";
import axios from "axios";

const route = useRoute();
const { user, fetchMe } = useAuth();

const routeId = computed(() => (route.params.id ? Number(route.params.id) : null));
const isSelf = computed(() => routeId.value === null || routeId.value === user.value?.id);

const person = ref<Person | null>(null);
const loading = ref(true);
const error = ref("");
const notFound = ref(false);
const editOpen = ref(false);
const pwOpen = ref(false);

async function load() {
  loading.value = true;
  error.value = "";
  notFound.value = false;
  try {
    const url = isSelf.value ? "org/people/me/" : `org/people/${routeId.value}/`;
    person.value = (await api.get<Person>(url)).data;
  } catch (e) {
    if (axios.isAxiosError(e) && e.response?.status === 404) notFound.value = true;
    else error.value = apiError(e).message;
    person.value = null;
  } finally {
    loading.value = false;
  }
}
watch(
  () => route.fullPath,
  () => {
    if (route.name !== "app-person" && route.name !== "app-profile") return; // leaving the page
    load();
  },
  { immediate: true },
);

const canEdit = computed(() => !!person.value && (isSelf.value || canManage(user.value, person.value)));
const full = computed(() => person.value?.visibility === "full");

async function onSaved(p: Person) {
  person.value = p;
  editOpen.value = false;
  toast.success("Profile saved.");
  if (isSelf.value) await fetchMe(); // sidebar avatar + name
}

const contact = computed<InfoRow[]>(() => {
  const p = person.value!;
  const rows: InfoRow[] = [
    { label: "Email", value: p.email, href: `mailto:${p.email}` },
    { label: "Phone", value: p.phone, href: p.phone ? `tel:${p.phone}` : undefined, mono: true },
  ];
  if (full.value) rows.push({ label: "Address", value: p.address });
  return rows;
});

const employment = computed<InfoRow[]>(() => {
  const p = person.value!;
  const rows: InfoRow[] = [
    { label: "Department", value: p.department?.name },
    { label: "Designation", value: p.designation },
    { label: "Reports to", value: p.manager?.full_name, to: p.manager ? { name: "app-person", params: { id: p.manager.id } } : undefined },
    { label: "Joined", value: p.join_date ? fmtDate(p.join_date) : null, note: tenure(p.join_date), mono: true },
  ];
  if (full.value) {
    rows.unshift({ label: "Employee code", value: p.employee_code, mono: true });
    rows.push(
      { label: "Type", value: p.employment_type ? EMPLOYMENT_LABEL[p.employment_type] : null },
      { label: "Date of birth", value: p.date_of_birth ? fmtDate(p.date_of_birth) : null, mono: true },
    );
  }
  return rows;
});

const emergency = computed<InfoRow[]>(() => [
  { label: "Name", value: person.value?.emergency_contact_name },
  {
    label: "Phone",
    value: person.value?.emergency_contact_phone,
    href: person.value?.emergency_contact_phone ? `tel:${person.value.emergency_contact_phone}` : undefined,
    mono: true,
  },
]);
</script>

<template>
  <div>
    <PageHeader
      :eyebrow="isSelf ? 'B3 · My profile' : 'B1 · People'"
      :title="isSelf ? 'My profile' : 'Profile'"
      :description="isSelf ? 'How colleagues see you on the roster. Keep your contact details current.' : undefined"
    >
      <template #actions>
        <RouterLink v-if="!isSelf" :to="{ name: 'app-people' }" class="btn-ghost btn-sm">← All people</RouterLink>
        <button v-if="isSelf && !loading" type="button" class="btn-ghost btn-sm" @click="pwOpen = true">Change password</button>
        <button v-if="canEdit && !loading" type="button" class="btn-primary btn-sm" @click="editOpen = true">
          {{ isSelf ? "Edit my profile" : "Edit profile" }}
        </button>
      </template>
    </PageHeader>

    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />

    <div v-else-if="notFound" class="panel">
      <EmptyState title="No such person on the roster" hint="They may have left, or the link is out of date.">
        <RouterLink :to="{ name: 'app-people' }" class="btn-ghost btn-sm">Back to people</RouterLink>
      </EmptyState>
    </div>

    <!-- Skeleton -->
    <div v-else-if="loading && !person" class="space-y-5" aria-hidden="true">
      <div class="h-44 animate-pulse rounded-xl bg-ink/85" />
      <div class="grid gap-5 lg:grid-cols-2">
        <div v-for="i in 4" :key="i" class="panel h-40 animate-pulse border-dashed" />
      </div>
    </div>

    <template v-else-if="person">

      <!-- Header sheet -->
      <section class="keep-ink contour-bg rise relative overflow-hidden rounded-xl bg-ink px-5 py-6 text-paper sm:px-7 sm:py-7">
        <div class="flex flex-col gap-5 sm:flex-row sm:items-center">
          <Avatar :name="person.full_name || person.email" :photo="person.photo" :size="96" ring />
          <div class="min-w-0 flex-1">
            <p class="readout text-[11px] tracking-[0.14em] text-paper/45 uppercase">
              <span v-if="person.employee_code">{{ person.employee_code }} · </span>ID {{ String(person.id).padStart(4, "0") }}
            </p>
            <h2 class="mt-1 font-display text-3xl leading-tight font-medium tracking-tight break-words sm:text-4xl">
              {{ person.full_name || person.email }}
            </h2>
            <p class="mt-1 text-paper/70">
              {{ person.designation || (person.role === "guest" ? "Applicant" : "No designation yet") }}
              <span v-if="person.department" class="text-paper/45"> · {{ person.department.name }}</span>
            </p>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <span class="rounded-full bg-paper px-0.5 py-0.5"><RolePill :role="person.role" /></span>
              <span v-if="!person.is_active" class="rounded-full bg-paper"><StatusPill status="inactive" label="Inactive" /></span>
              <span v-if="isSelf" class="font-mono text-[10.5px] tracking-wide text-flag uppercase">◉ You are here</span>
            </div>
          </div>
        </div>
      </section>

      <p v-if="!full" class="mt-4 text-xs text-ink/50">
        <span aria-hidden="true">⌖</span> Personal details are visible only to {{ person.first_name || "them" }}, their manager and HR.
      </p>

      <div class="mt-5 grid gap-5 lg:grid-cols-2">
        <InfoPanel title="Contact" ref-code="§1" :rows="contact" />
        <InfoPanel title="Employment" ref-code="§2" :rows="employment" />
        <InfoPanel v-if="full" title="Emergency" ref-code="§3" :rows="emergency" />

        <InfoPanel title="Skills" ref-code="§4">
          <ul v-if="person.skills.length" class="flex flex-wrap gap-2" aria-label="Skills">
            <li
              v-for="(s, i) in person.skills"
              :key="i"
              class="rounded-md border border-dashed border-river/40 bg-panel/50 px-2.5 py-1 font-mono text-xs text-ink/80"
            >
              {{ s }}
            </li>
          </ul>
          <p v-else class="text-sm text-ink/40">No skills listed{{ isSelf ? " — add a few so colleagues know who to ask." : "." }}</p>
        </InfoPanel>

        <InfoPanel title="Bio" ref-code="§5" class="lg:col-span-2">
          <p v-if="person.bio" class="max-w-prose text-sm leading-relaxed whitespace-pre-line text-ink/80">{{ person.bio }}</p>
          <p v-else class="text-sm text-ink/40">No bio yet.</p>
        </InfoPanel>
      </div>

      <PersonFormModal v-if="canEdit" :open="editOpen" :person="person" @close="editOpen = false" @saved="onSaved" />
      <PasswordModal v-if="isSelf" :open="pwOpen" @close="pwOpen = false" @saved="pwOpen = false; toast.success('Password changed.')" />
    </template>
  </div>
</template>
