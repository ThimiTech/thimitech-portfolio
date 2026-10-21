<script setup lang="ts">
import { confirmDialog } from "../../components/app/ui/confirm";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/api";
import { toast } from "@/components/app/ui/toast";
import { useAuth, type Role } from "@/stores/auth";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import PersonCard from "@/components/app/org/PersonCard.vue";
import PersonFormModal from "@/components/app/org/PersonFormModal.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import { ROLES, ROLE_LABEL, apiError, canManage, type Department, type Person } from "@/components/app/org/org";

const { user, hasRole } = useAuth();
const router = useRouter();
const isHR = computed(() => hasRole("hr_admin"));

const filters = reactive({ search: "", department: "" as string, role: "" as "" | Role, guests: false, status: "" as "" | "true" | "false" });
const people = ref<Person[]>([]);
const departments = ref<Department[]>([]);
const loading = ref(true);
const error = ref("");
const busyId = ref<number | null>(null);
const createOpen = ref(false);

let ctrl: AbortController | null = null;
async function load() {
  ctrl?.abort();
  ctrl = new AbortController();
  loading.value = true;
  error.value = "";
  const params: Record<string, string> = {};
  if (filters.search.trim()) params.search = filters.search.trim();
  if (filters.department) params.department = filters.department;
  if (filters.role) params.role = filters.role;
  if (isHR.value && (filters.guests || filters.role === "guest")) params.include_guests = "1";
  if (isHR.value && filters.status) params.is_active = filters.status;
  try {
    people.value = (await api.get<Person[]>("org/people/", { params, signal: ctrl.signal })).data;
    loading.value = false;
  } catch (e) {
    if ((e as { code?: string }).code === "ERR_CANCELED") return;
    error.value = apiError(e).message;
    loading.value = false;
  }
}

let t: number | undefined;
watch(() => filters.search, () => {
  clearTimeout(t);
  t = window.setTimeout(load, 250);
});
watch(() => [filters.department, filters.role, filters.guests, filters.status], load);

onMounted(async () => {
  load();
  try {
    departments.value = (await api.get<Department[]>("org/departments/")).data;
  } catch {
    /* department filter just stays empty */
  }
});

const hasFilters = computed(() => !!(filters.search || filters.department || filters.role || filters.status));
function resetFilters() {
  Object.assign(filters, { search: "", department: "", role: "", status: "" });
}

const roleOptions = computed(() => ROLES.filter((r) => r !== "guest" || isHR.value));

// ---- HR actions (optimistic) ---------------------------------------------------
function replace(p: Person) {
  people.value = people.value.map((x) => (x.id === p.id ? p : x));
}

async function onboard(p: Person) {
  busyId.value = p.id;
  replace({ ...p, role: "employee" });
  try {
    replace((await api.patch<Person>(`org/people/${p.id}/`, { role: "employee" })).data);
    toast.success(`${p.full_name || p.email} is now an employee.`);
  } catch (e) {
    replace(p);
    toast.error(apiError(e).message);
  } finally {
    busyId.value = null;
  }
}

async function toggleActive(p: Person) {
  const action = p.is_active ? "deactivate" : "reactivate";
  if (p.is_active && !(await confirmDialog({ title: "Deactivate person", body: `Deactivate ${p.full_name || p.email}? They will no longer be able to sign in.`, confirmLabel: "Deactivate" }))) return;
  busyId.value = p.id;
  replace({ ...p, is_active: !p.is_active });
  try {
    replace((await api.post<Person>(`org/people/${p.id}/${action}/`)).data);
    toast.success(`${p.full_name || p.email} ${action}d.`);
  } catch (e) {
    replace(p);
    toast.error(apiError(e).message);
  } finally {
    busyId.value = null;
  }
}

function onCreated(p: Person) {
  createOpen.value = false;
  router.push({ name: "app-person", params: { id: p.id } });
}
</script>

<template>
  <div>
    <PageHeader eyebrow="B1 · People" title="People" description="Everyone on the Thimi Tech roster — find a colleague, their team and how to reach them.">
      <template v-if="isHR" #actions>
        <button type="button" class="btn-primary" @click="createOpen = true">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          Add person
        </button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <section class="panel mb-5 p-4" aria-label="Filter people">
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
        <div class="field">
          <label for="dir-search" class="ledger-label">Search</label>
          <input id="dir-search" v-model="filters.search" type="search" class="input" placeholder="Name, email or designation" autocomplete="off" />
        </div>
        <div class="field">
          <label for="dir-dept" class="ledger-label">Department</label>
          <select id="dir-dept" v-model="filters.department" class="input">
            <option value="">All departments</option>
            <option v-for="d in departments" :key="d.id" :value="String(d.id)">{{ d.name }}</option>
          </select>
        </div>
        <div class="field">
          <label for="dir-role" class="ledger-label">Role</label>
          <select id="dir-role" v-model="filters.role" class="input">
            <option value="">All roles</option>
            <option v-for="r in roleOptions" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
          </select>
        </div>
        <div v-if="isHR" class="field">
          <label for="dir-status" class="ledger-label">Status</label>
          <select id="dir-status" v-model="filters.status" class="input">
            <option value="">Active &amp; inactive</option>
            <option value="true">Active only</option>
            <option value="false">Inactive only</option>
          </select>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-dashed border-ink/10 pt-3">
        <label v-if="isHR" class="inline-flex cursor-pointer items-center gap-2 text-sm text-ink/70">
          <input v-model="filters.guests" type="checkbox" class="h-4 w-4 accent-flag" />
          Include applicants (guests) to onboard
        </label>
        <p class="readout text-xs text-ink/50" aria-live="polite">
          <template v-if="!loading">{{ String(people.length).padStart(2, "0") }} {{ people.length === 1 ? "person" : "people" }} plotted</template>
          <template v-else>surveying…</template>
        </p>
      </div>
    </section>

    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />

    <!-- Skeleton -->
    <ul v-else-if="loading && !people.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
      <li v-for="i in 6" :key="i" class="panel animate-pulse p-4">
        <div class="flex gap-3">
          <div class="h-12 w-12 rounded-full bg-panel" />
          <div class="flex-1 space-y-2 pt-1">
            <div class="h-3.5 w-2/3 rounded bg-panel" />
            <div class="h-3 w-1/2 rounded bg-panel/70" />
          </div>
        </div>
        <div class="mt-6 border-t border-dashed border-ink/10 pt-3"><div class="h-3 w-1/3 rounded bg-panel/70" /></div>
      </li>
    </ul>

    <div v-else-if="!people.length" class="panel">
      <EmptyState
        :title="hasFilters ? 'No one at these coordinates' : 'The roster is empty'"
        :hint="hasFilters ? 'Try a different name, department or role.' : isHR ? 'Add the first person to start the roster.' : undefined"
      >
        <button v-if="hasFilters" type="button" class="btn-ghost btn-sm" @click="resetFilters">Clear filters</button>
        <button v-else-if="isHR" type="button" class="btn-primary btn-sm" @click="createOpen = true">Add person</button>
      </EmptyState>
    </div>

    <ul v-else class="grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-3" :class="loading ? 'opacity-60' : ''" :aria-busy="loading">
      <li v-for="(p, i) in people" :key="p.id" class="rise" :style="{ animationDelay: `${Math.min(i, 12) * 30}ms` }">
        <PersonCard
          :person="p"
          :manage="canManage(user, p)"
          :is-self="p.id === user?.id"
          :busy="busyId === p.id"
          @onboard="onboard(p)"
          @toggle-active="toggleActive(p)"
        />
      </li>
    </ul>

    <PersonFormModal v-if="isHR" :open="createOpen" @close="createOpen = false" @saved="onCreated" />
  </div>
</template>
