<script setup lang="ts">
import { confirmDialog } from "../../components/app/ui/confirm";
import { computed, onMounted, ref } from "vue";
import api from "@/api/api";
import { toast } from "@/components/app/ui/toast";
import { useAuth } from "@/stores/auth";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import OrgChart from "@/components/app/org/OrgChart.vue";
import OrgEditModal from "@/components/app/org/OrgEditModal.vue";
import DepartmentList from "@/components/app/org/DepartmentList.vue";
import DepartmentModal from "@/components/app/org/DepartmentModal.vue";
import {
  WEEKDAYS, WEEKDAYS_LONG, apiError, fmtDate, hhmm,
  type Department, type Organization, type Structure,
} from "@/components/app/org/org";

const { user, hasRole } = useAuth();
const isHR = computed(() => hasRole("hr_admin"));
const isSuper = computed(() => hasRole("super_admin"));

const org = ref<Organization | null>(null);
const departments = ref<Department[]>([]);
const structure = ref<Structure | null>(null);
const loading = ref(true);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [o, d, s] = await Promise.all([
      api.get<Organization>("org/organization/"),
      api.get<Department[]>("org/departments/"),
      api.get<Structure>("org/structure/"),
    ]);
    org.value = o.data;
    departments.value = d.data;
    structure.value = s.data;
  } catch (e) {
    error.value = apiError(e).message;
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function reloadDepartments() {
  try {
    const [d, s] = await Promise.all([api.get<Department[]>("org/departments/"), api.get<Structure>("org/structure/")]);
    departments.value = d.data;
    structure.value = s.data;
  } catch (e) {
    toast.error(apiError(e).message);
  }
}

// ---- org edit
const editMode = ref<"profile" | "policy" | null>(null);
function onOrgSaved(o: Organization) {
  org.value = o;
  editMode.value = null;
  toast.success("Organization updated.");
}

// ---- departments
const deptOpen = ref(false);
const deptEditing = ref<Department | null>(null);
const deptBusy = ref<number | null>(null);

function openDept(d: Department | null) {
  deptEditing.value = d;
  deptOpen.value = true;
}
async function onDeptSaved(d: Department) {
  deptOpen.value = false;
  toast.success(`${d.name} saved.`);
  await reloadDepartments();
}
async function removeDept(d: Department) {
  const msg = `Delete ${d.name}? Its ${d.member_count} member(s) become unassigned and any sub-departments move to the top level.`;
  if (!(await confirmDialog({ title: "Delete department", body: msg, confirmLabel: "Delete" }))) return;
  deptBusy.value = d.id;
  const before = departments.value;
  departments.value = before.filter((x) => x.id !== d.id); // optimistic
  try {
    await api.delete(`org/departments/${d.id}/`);
    toast.success(`${d.name} deleted.`);
    await reloadDepartments();
  } catch (e) {
    departments.value = before;
    toast.error(apiError(e).message);
  } finally {
    deptBusy.value = null;
  }
}

// ---- readouts
const links = computed(() => {
  const o = org.value;
  if (!o) return [];
  return [
    { label: "Website", href: o.website },
    { label: "GitHub", href: o.github },
    { label: "LinkedIn", href: o.linkedin },
    { label: "YouTube", href: o.youtube },
  ].filter((l) => l.href);
});
const hostOf = (u: string) => u.replace(/^https?:\/\//, "").replace(/\/$/, "");
const workMinutes = computed(() => {
  if (!org.value) return 0;
  const toMin = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  return toMin(org.value.work_end) - toMin(org.value.work_start);
});
</script>

<template>
  <div>
    <PageHeader eyebrow="B2 · Organization" title="Organization" description="Who we are, how the working day is set, and how the teams fit together." />

    <LoadError v-if="error" :message="error" :busy="loading" @retry="load" />

    <!-- Skeleton -->
    <div v-else-if="loading && !org" class="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]" aria-hidden="true">
      <div class="h-64 animate-pulse rounded-xl bg-ink/85" />
      <div class="panel h-64 animate-pulse border-dashed" />
      <div class="panel h-72 animate-pulse border-dashed lg:col-span-2" />
    </div>

    <template v-else-if="org">

      <div class="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <!-- Profile -->
        <section class="keep-ink contour-bg rise relative overflow-hidden rounded-xl bg-ink p-5 text-paper sm:p-7" aria-labelledby="org-name">
          <div class="flex items-start gap-4">
            <span class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-paper/15 bg-ink-2">
              <img v-if="org.logo" :src="org.logo" :alt="`${org.name} logo`" class="h-full w-full object-contain" />
              <span v-else class="font-display text-2xl text-paper/80" aria-hidden="true">{{ org.name.slice(0, 1) }}</span>
            </span>
            <div class="min-w-0 flex-1">
              <h2 id="org-name" class="font-display text-2xl leading-tight font-medium tracking-tight sm:text-3xl">{{ org.name }}</h2>
              <p v-if="org.tagline" class="mt-1 text-sm text-paper/65">{{ org.tagline }}</p>
            </div>
            <button
              v-if="isHR"
              type="button"
              class="btn-sm btn border border-paper/20 text-paper hover:bg-paper/10"
              aria-label="Edit organization profile"
              @click="editMode = 'profile'"
            >
              Edit
            </button>
          </div>
          <p v-if="org.about" class="mt-5 max-w-prose text-sm leading-relaxed whitespace-pre-line text-paper/80">{{ org.about }}</p>

          <dl class="mt-6 grid gap-x-6 gap-y-3 border-t border-dashed border-paper/15 pt-5 text-sm sm:grid-cols-2">
            <div v-if="org.email">
              <dt class="font-mono text-[10.5px] tracking-[0.14em] text-paper/45 uppercase">Email</dt>
              <dd><a :href="`mailto:${org.email}`" class="hover:underline">{{ org.email }}</a></dd>
            </div>
            <div v-if="org.phone">
              <dt class="font-mono text-[10.5px] tracking-[0.14em] text-paper/45 uppercase">Phone</dt>
              <dd class="readout"><a :href="`tel:${org.phone}`" class="hover:underline">{{ org.phone }}</a></dd>
            </div>
            <div v-if="org.address">
              <dt class="font-mono text-[10.5px] tracking-[0.14em] text-paper/45 uppercase">Address</dt>
              <dd>{{ org.address }}</dd>
            </div>
            <div v-if="org.founded">
              <dt class="font-mono text-[10.5px] tracking-[0.14em] text-paper/45 uppercase">Founded</dt>
              <dd class="readout">{{ fmtDate(org.founded) }}</dd>
            </div>
          </dl>

          <ul v-if="links.length" class="mt-5 flex flex-wrap gap-2" aria-label="Links">
            <li v-for="l in links" :key="l.label">
              <a
                :href="l.href"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 rounded-full border border-paper/20 px-3 py-1 text-xs text-paper/85 hover:bg-paper/10 focus-visible:ring-2 focus-visible:ring-flag/50 focus-visible:outline-none"
              >
                <span class="font-mono text-[10px] tracking-wider text-paper/50 uppercase">{{ l.label }}</span>
                <span class="max-w-[14rem] truncate">{{ hostOf(l.href) }}</span>
                <span class="sr-only">(opens in a new tab)</span>
              </a>
            </li>
          </ul>
        </section>

        <!-- Work policy -->
        <section class="panel rise" aria-labelledby="policy-h">
          <div class="panel-head">
            <h2 id="policy-h" class="font-display text-base font-medium">Work policy</h2>
            <button v-if="isSuper" type="button" class="btn-ghost btn-sm" @click="editMode = 'policy'">Edit</button>
            <span v-else class="ledger-label text-ink/35">Set by owner</span>
          </div>
          <div class="panel-body grid gap-5">
            <div>
              <p class="ledger-label">Working hours · NPT</p>
              <p class="readout mt-1 font-display text-3xl text-ink">
                {{ hhmm(org.work_start) }}<span class="mx-2 text-ink/30" aria-label="to">—</span>{{ hhmm(org.work_end) }}
              </p>
              <p class="readout mt-0.5 text-xs text-ink/50">{{ Math.floor(workMinutes / 60) }}h {{ workMinutes % 60 }}m per day</p>
            </div>
            <div class="border-t border-dashed border-ink/10 pt-4">
              <p class="ledger-label">Late after</p>
              <p class="readout mt-1 text-sm text-ink">
                {{ org.late_grace_minutes }} min grace
                <span class="text-ink/45">— check-ins past work start + grace are marked late</span>
              </p>
            </div>
            <div class="border-t border-dashed border-ink/10 pt-4">
              <p class="ledger-label" id="weekend-l">Weekend</p>
              <ul class="mt-2 flex flex-wrap gap-1.5" aria-labelledby="weekend-l">
                <li
                  v-for="(d, i) in WEEKDAYS"
                  :key="d"
                  class="min-w-10 rounded-md border px-2 py-1.5 text-center font-mono text-[11px] uppercase"
                  :class="org.weekend_days.includes(i) ? 'border-river/50 bg-river/10 text-river line-through decoration-river/50' : 'border-ink/10 text-ink/60'"
                >
                  <span aria-hidden="true">{{ d }}</span>
                  <span class="sr-only">{{ WEEKDAYS_LONG[i] }}: {{ org.weekend_days.includes(i) ? "weekend" : "working day" }}</span>
                </li>
              </ul>
              <p v-if="!org.weekend_days.length" class="mt-2 text-xs text-ink/50">No weekend days set.</p>
            </div>
          </div>
        </section>
      </div>

      <div class="mt-5 grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <!-- Departments -->
        <section class="panel self-start" aria-labelledby="depts-h">
          <div class="panel-head">
            <h2 id="depts-h" class="font-display text-base font-medium">
              Departments <span class="readout ml-1 text-xs text-ink/40">{{ departments.length }}</span>
            </h2>
            <button v-if="isHR" type="button" class="btn-primary btn-sm" @click="openDept(null)">New department</button>
          </div>
          <DepartmentList
            v-if="departments.length"
            :departments="departments"
            :manage="isHR"
            :busy-id="deptBusy"
            @edit="openDept"
            @remove="removeDept"
          />
          <EmptyState v-else title="No departments yet" :hint="isHR ? 'Create the first one to start the org chart.' : 'Departments appear here once HR sets them up.'" />
        </section>

        <!-- Org chart -->
        <section class="panel" aria-labelledby="chart-h">
          <div class="panel-head">
            <h2 id="chart-h" class="font-display text-base font-medium">Org chart</h2>
            <span class="ledger-label">Active staff</span>
          </div>
          <div class="panel-body overflow-x-auto">
            <OrgChart
              v-if="structure && (structure.departments.length || structure.unassigned.length)"
              :structure="structure"
              :org-name="org.name"
              :me-id="user?.id"
            />
            <EmptyState v-else title="Nothing to chart yet" hint="Departments and their staff will appear here." />
          </div>
        </section>
      </div>

      <OrgEditModal v-if="editMode" :open="!!editMode" :mode="editMode" :org="org" @close="editMode = null" @saved="onOrgSaved" />
      <DepartmentModal
        v-if="isHR"
        :open="deptOpen"
        :department="deptEditing"
        :departments="departments"
        @close="deptOpen = false"
        @saved="onDeptSaved"
      />
    </template>
  </div>
</template>
