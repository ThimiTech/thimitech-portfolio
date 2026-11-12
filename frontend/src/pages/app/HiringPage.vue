<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import api from "@/api/api";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import TabBar from "@/components/app/ui/TabBar.vue";
import Modal from "@/components/app/ui/Modal.vue";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import StatusPill from "@/components/app/ui/StatusPill.vue";
import SkeletonBlock from "@/components/app/ui/SkeletonBlock.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import { confirmDialog } from "@/components/app/ui/confirm";
import { toast } from "@/components/app/ui/toast";
import { useTabQuery } from "@/components/app/ui/crumb";
import { errMsg } from "@/components/app/attendance/attendance";

type Stage = "pending" | "shortlisted" | "interview" | "selected" | "rejected";
interface Application {
  id: number; job: number; job_title: string; applicant: number; applicant_role: string; name: string; email: string
  phone: string; address: string; cover_letter: string; cv_name: string; status: Stage; hr_notes: string; applied_at: string
}
interface Job {
  id: number; title: string; employment_type: string; description: string; is_active: boolean; display_order: number
  requirements: { id: number; text: string }[]; application_count: number; pending_count: number
}
interface Step { id: number; title: string; description: string; position: number; is_active: boolean }

const STAGES: { id: Stage; label: string }[] = [
  { id: "pending", label: "New" },
  { id: "shortlisted", label: "Shortlisted" },
  { id: "interview", label: "Interview" },
  { id: "selected", label: "Selected" },
  { id: "rejected", label: "Rejected" },
];
const EMPLOYMENT = [["full_time", "Full-time"], ["part_time", "Part-time"], ["contract", "Contract"], ["intern", "Intern"]] as const;

const route = useRoute();
const tab = useTabQuery(() => ["pipeline", "postings", "onboarding"], "pipeline");
const loading = ref(true);
const error = ref("");
const applications = ref<Application[]>([]);
const jobs = ref<Job[]>([]);
const steps = ref<Step[]>([]);
const departments = ref<{ id: number; name: string }[]>([]);
const jobFilter = ref<number | "">("");
const query = ref("");

const tabs = computed(() => [
  { id: "pipeline", label: "Pipeline", count: applications.value.filter((a) => a.status === "pending").length },
  { id: "postings", label: "Postings" },
  { id: "onboarding", label: "Onboarding checklist" },
]);

async function load() {
  error.value = "";
  try {
    const [a, j, s, d] = await Promise.all([
      api.get<Application[]>("hiring/applications/"),
      api.get<Job[]>("jobs/", { params: { manage: 1 } }),
      api.get<Step[]>("org/onboarding/steps/"),
      api.get<{ id: number; name: string }[]>("org/departments/"),
    ]);
    applications.value = a.data;
    jobs.value = j.data;
    steps.value = s.data;
    departments.value = d.data;
    const wanted = Number(route.query.application);
    const hit = wanted && a.data.find((x) => x.id === wanted);
    if (hit) open(hit);
  } catch (e) {
    error.value = errMsg(e, "Couldn't load hiring.");
  } finally {
    loading.value = false;
  }
}
onMounted(load);

// ── Pipeline ───────────────────────────────────────────
const visible = computed(() => {
  const q = query.value.trim().toLowerCase();
  return applications.value.filter(
    (a) => (jobFilter.value === "" || a.job === jobFilter.value) && (!q || `${a.name} ${a.email} ${a.job_title}`.toLowerCase().includes(q)),
  );
});
const column = (s: Stage) => visible.value.filter((a) => a.status === s);
const day = (iso: string) => new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kathmandu", day: "2-digit", month: "short" }).format(new Date(iso));

const current = ref<Application | null>(null);
const draft = reactive({ status: "pending" as Stage, hr_notes: "" });
const hireForm = reactive({ department: "" as number | "", designation: "", employment_type: "full_time", join_date: "" });
const hiring = ref(false);
const saving = ref(false);
const isStaff = computed(() => !!current.value && current.value.applicant_role !== "guest");

function open(a: Application) {
  current.value = a;
  hiring.value = false;
  Object.assign(draft, { status: a.status, hr_notes: a.hr_notes });
  Object.assign(hireForm, { department: "", designation: a.job_title, employment_type: "full_time", join_date: "" });
}
function replace(a: Application) {
  applications.value = applications.value.map((x) => (x.id === a.id ? a : x));
  current.value = null;
}
async function save() {
  if (!current.value) return;
  saving.value = true;
  try {
    replace((await api.patch<Application>(`hiring/applications/${current.value.id}/`, draft)).data);
    toast.success("Application updated.");
  } catch (e) {
    toast.error(errMsg(e, "Couldn't save the application."));
  } finally {
    saving.value = false;
  }
}
async function hire() {
  if (!current.value) return;
  saving.value = true;
  try {
    const body = Object.fromEntries(Object.entries(hireForm).filter(([, v]) => v !== ""));
    const name = current.value.name;
    replace((await api.post<Application>(`hiring/applications/${current.value.id}/hire/`, body)).data);
    toast.success(`${name} is now on staff. Their onboarding checklist has started.`);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't complete the hire."));
  } finally {
    saving.value = false;
  }
}
async function downloadCv(a: Application) {
  try {
    const { data } = await api.get<Blob>(`hiring/applications/${a.id}/cv/`, { responseType: "blob" });
    const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(data), download: a.cv_name || "cv" });
    link.click();
    URL.revokeObjectURL(link.href);
  } catch {
    toast.error("Couldn't download the CV.");
  }
}

// ── Postings ───────────────────────────────────────────
const jobOpen = ref(false);
const jobId = ref<number | null>(null);
const jobForm = reactive({ title: "", employment_type: "", description: "", requirements: "", is_active: true });
function editJob(j?: Job) {
  jobId.value = j?.id ?? null;
  Object.assign(jobForm, {
    title: j?.title ?? "",
    employment_type: j?.employment_type ?? "Full-time",
    description: j?.description ?? "",
    requirements: j?.requirements.map((r) => r.text).join("\n") ?? "",
    is_active: j?.is_active ?? true,
  });
  jobOpen.value = true;
}
async function saveJob() {
  saving.value = true;
  const { requirements, ...rest } = jobForm;
  const body = { ...rest, requirement_texts: requirements.split("\n") };
  try {
    const { data } = jobId.value ? await api.patch<Job>(`jobs/${jobId.value}/`, body) : await api.post<Job>("jobs/", body);
    jobs.value = jobId.value ? jobs.value.map((j) => (j.id === data.id ? data : j)) : [...jobs.value, data];
    jobOpen.value = false;
    toast.success(jobId.value ? "Posting saved." : "Posting published.");
  } catch (e) {
    toast.error(errMsg(e, "Couldn't save the posting."));
  } finally {
    saving.value = false;
  }
}
async function toggleJob(j: Job) {
  try {
    const { data } = await api.patch<Job>(`jobs/${j.id}/`, { is_active: !j.is_active });
    jobs.value = jobs.value.map((x) => (x.id === data.id ? data : x));
  } catch (e) {
    toast.error(errMsg(e, "Couldn't change the posting."));
  }
}
async function removeJob(j: Job) {
  if (!(await confirmDialog({ title: `Delete “${j.title}”?`, body: "The posting is removed from the public site for good.", confirmLabel: "Delete", danger: true }))) return;
  try {
    await api.delete(`jobs/${j.id}/`);
    jobs.value = jobs.value.filter((x) => x.id !== j.id);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't delete the posting."));
  }
}

// ── Onboarding template ────────────────────────────────
const newStep = reactive({ title: "", description: "" });
async function addStep() {
  if (!newStep.title.trim()) return;
  try {
    const position = Math.max(-1, ...steps.value.map((s) => s.position)) + 1;
    steps.value.push((await api.post<Step>("org/onboarding/steps/", { ...newStep, position })).data);
    Object.assign(newStep, { title: "", description: "" });
  } catch (e) {
    toast.error(errMsg(e, "Couldn't add the step."));
  }
}
async function patchStep(s: Step, change: Partial<Step>) {
  try {
    Object.assign(s, (await api.patch<Step>(`org/onboarding/steps/${s.id}/`, change)).data);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't save the step."));
  }
}
async function removeStep(s: Step) {
  if (!(await confirmDialog({ title: `Remove “${s.title}”?`, body: "Checklists already given to people keep this step.", confirmLabel: "Remove", danger: true }))) return;
  try {
    await api.delete(`org/onboarding/steps/${s.id}/`);
    steps.value = steps.value.filter((x) => x.id !== s.id);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't remove the step."));
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Admin · Hiring" title="Hiring" description="Postings on the public site, the applicants they bring in, and the checklist a new hire starts with.">
      <template #actions>
        <button v-if="tab === 'postings'" type="button" class="btn-primary" @click="editJob()">New posting</button>
      </template>
    </PageHeader>

    <TabBar v-model="tab" :tabs="tabs" label="Hiring views" id-prefix="hire" class="mb-6" />

    <SkeletonBlock v-if="loading" :rows="4" height="h-14" label="Loading hiring" />
    <LoadError v-else-if="error" :message="error" @retry="load" />

    <div v-else :id="`hire-panel-${tab}`" role="tabpanel" :aria-labelledby="`hire-tab-${tab}`">
      <!-- Pipeline -->
      <template v-if="tab === 'pipeline'">
        <div class="mb-4 flex flex-wrap items-center gap-3">
          <label class="min-w-0 flex-1 sm:max-w-xs">
            <span class="sr-only">Search applicants</span>
            <input v-model="query" type="search" class="input" placeholder="Name, email or role…" />
          </label>
          <label>
            <span class="sr-only">Posting</span>
            <select v-model="jobFilter" class="input w-auto">
              <option value="">All postings</option>
              <option v-for="j in jobs" :key="j.id" :value="j.id">{{ j.title }}</option>
            </select>
          </label>
        </div>

        <div v-if="!applications.length" class="panel">
          <EmptyState title="No applications yet" hint="Applications sent from the careers section of the public site land here." />
        </div>
        <div v-else class="relative overflow-x-auto pb-2">
          <div class="grid min-w-[980px] grid-cols-5 gap-3">
            <section v-for="s in STAGES" :key="s.id" :aria-label="`${s.label} applications`" class="rounded-xl border border-dashed border-ink/15 bg-panel/30 p-2">
              <h2 class="ledger-label flex items-center justify-between px-2 py-1.5">
                {{ s.label }} <span class="readout text-ink/70">{{ column(s.id).length }}</span>
              </h2>
              <ul class="grid gap-2">
                <li v-for="a in column(s.id)" :key="a.id">
                  <button type="button" class="panel w-full p-3 text-left transition-colors hover:border-river/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40" @click="open(a)">
                    <span class="block truncate text-sm font-medium text-ink">{{ a.name }}</span>
                    <span class="block truncate text-xs text-ink/60">{{ a.job_title }}</span>
                    <span class="mt-1.5 block font-mono text-[10.5px] text-ink/45">
                      {{ day(a.applied_at) }}<template v-if="a.applicant_role !== 'guest'"> · on staff</template>
                    </span>
                  </button>
                </li>
              </ul>
            </section>
          </div>
        </div>
      </template>

      <!-- Postings -->
      <template v-else-if="tab === 'postings'">
        <div v-if="!jobs.length" class="panel">
          <EmptyState title="No postings yet" hint="A posting appears in the careers section of the public site as soon as it is open.">
            <button type="button" class="btn-ghost btn-sm" @click="editJob()">Write the first one</button>
          </EmptyState>
        </div>
        <ul v-else class="grid gap-3">
          <li v-for="j in jobs" :key="j.id" class="panel flex flex-wrap items-center gap-x-4 gap-y-2 p-4">
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium text-ink">{{ j.title }}</p>
              <p class="text-xs text-ink/55">
                {{ j.employment_type }} · {{ j.application_count }} application{{ j.application_count === 1 ? "" : "s" }}
                <span v-if="j.pending_count" class="text-flag"> · {{ j.pending_count }} new</span>
              </p>
            </div>
            <StatusPill :status="j.is_active ? 'active' : 'closed'" :label="j.is_active ? 'Open' : 'Closed'" />
            <div class="flex gap-1.5">
              <button type="button" class="btn-ghost btn-sm" @click="toggleJob(j)">{{ j.is_active ? "Close" : "Reopen" }}</button>
              <button type="button" class="btn-ghost btn-sm" @click="editJob(j)">Edit</button>
              <button v-if="!j.application_count" type="button" class="btn-danger btn-sm" @click="removeJob(j)">Delete</button>
            </div>
          </li>
        </ul>
      </template>

      <!-- Onboarding template -->
      <template v-else>
        <p class="mb-4 max-w-2xl text-sm text-ink/60">
          Every new hire gets a copy of the active steps on their profile. Changing this list does not rewrite checklists people already have.
        </p>
        <ul class="panel divide-y divide-dashed divide-ink/10">
          <li v-for="s in steps" :key="s.id" class="flex flex-wrap items-start gap-3 px-4 py-3" :class="s.is_active ? '' : 'opacity-55'">
            <div class="grid min-w-0 flex-1 gap-1.5">
              <input :value="s.title" class="input" :aria-label="`Step title: ${s.title}`" @change="patchStep(s, { title: ($event.target as HTMLInputElement).value })" />
              <input :value="s.description" class="input text-xs" placeholder="What to do, or who to ask" :aria-label="`Details for ${s.title}`" @change="patchStep(s, { description: ($event.target as HTMLInputElement).value })" />
            </div>
            <button type="button" class="btn-ghost btn-sm" @click="patchStep(s, { is_active: !s.is_active })">{{ s.is_active ? "Pause" : "Use" }}</button>
            <button type="button" class="btn-danger btn-sm" @click="removeStep(s)">Remove</button>
          </li>
          <li>
            <form class="flex flex-wrap items-start gap-3 px-4 py-3" @submit.prevent="addStep">
              <div class="grid min-w-0 flex-1 gap-1.5">
                <input v-model="newStep.title" class="input" placeholder="New step" aria-label="New step title" maxlength="200" />
                <input v-model="newStep.description" class="input text-xs" placeholder="What to do, or who to ask" aria-label="New step details" />
              </div>
              <button type="submit" class="btn-ink btn-sm" :disabled="!newStep.title.trim()">Add step</button>
            </form>
          </li>
        </ul>
      </template>
    </div>

    <!-- Application -->
    <Modal :open="!!current" :title="current?.name ?? ''" width="max-w-2xl" @close="current = null">
      <template v-if="current">
        <p class="text-sm text-ink/60">
          Applied for <span class="font-medium text-ink">{{ current.job_title }}</span> on {{ day(current.applied_at) }}
        </p>
        <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div><dt class="ledger-label">Email</dt><dd><a :href="`mailto:${current.email}`" class="break-all text-river hover:text-flag">{{ current.email }}</a></dd></div>
          <div><dt class="ledger-label">Phone</dt><dd class="readout">{{ current.phone }}</dd></div>
          <div><dt class="ledger-label">Address</dt><dd>{{ current.address }}</dd></div>
        </dl>
        <div class="mt-4">
          <p class="ledger-label">Cover letter</p>
          <p class="mt-1 max-h-48 overflow-y-auto text-sm leading-relaxed whitespace-pre-line text-ink/80">{{ current.cover_letter || "None provided." }}</p>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" class="btn-ghost btn-sm" @click="downloadCv(current)">Download CV</button>
          <RouterLink v-if="isStaff" :to="`/app/people/${current.applicant}`" class="btn-ghost btn-sm">Open staff profile</RouterLink>
        </div>

        <div class="mt-5 grid gap-4 border-t border-dashed border-ink/15 pt-5 sm:grid-cols-[11rem_1fr]">
          <label class="field">
            <span class="ledger-label">Stage</span>
            <select v-model="draft.status" class="input">
              <option v-for="s in STAGES" :key="s.id" :value="s.id">{{ s.label }}</option>
            </select>
            <span class="text-xs text-ink/50">The applicant is emailed when the stage changes.</span>
          </label>
          <label class="field">
            <span class="ledger-label">Internal notes</span>
            <textarea v-model="draft.hr_notes" rows="3" class="input" placeholder="Only HR sees these." />
          </label>
        </div>

        <form v-if="hiring" class="mt-5 grid gap-4 rounded-lg border border-moss/30 bg-moss/5 p-4 sm:grid-cols-2" @submit.prevent="hire">
          <p class="text-sm text-ink/70 sm:col-span-2">
            Hiring gives {{ current.name }} staff access, fills their profile from this application and starts their onboarding checklist.
          </p>
          <label class="field">
            <span class="ledger-label">Designation</span>
            <input v-model="hireForm.designation" class="input" maxlength="120" />
          </label>
          <label class="field">
            <span class="ledger-label">Department</span>
            <select v-model="hireForm.department" class="input">
              <option value="">Not assigned yet</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="ledger-label">Employment type</span>
            <select v-model="hireForm.employment_type" class="input">
              <option v-for="[v, l] in EMPLOYMENT" :key="v" :value="v">{{ l }}</option>
            </select>
          </label>
          <label class="field">
            <span class="ledger-label">Join date</span>
            <input v-model="hireForm.join_date" type="date" class="input" />
          </label>
          <div class="flex gap-2 sm:col-span-2">
            <button type="submit" class="btn-primary btn-sm" :disabled="saving">Confirm hire</button>
            <button type="button" class="btn-ghost btn-sm" @click="hiring = false">Cancel</button>
          </div>
        </form>
      </template>
      <template #footer>
        <button v-if="current && !hiring && !isStaff && current.status !== 'rejected'" type="button" class="btn-ghost mr-auto" @click="hiring = true">Hire…</button>
        <button type="button" class="btn-ghost" @click="current = null">Close</button>
        <button type="button" class="btn-primary" :disabled="saving" @click="save">Save</button>
      </template>
    </Modal>

    <!-- Posting -->
    <Modal :open="jobOpen" :title="jobId ? 'Edit posting' : 'New posting'" width="max-w-2xl" @close="jobOpen = false">
      <form id="job-form" class="grid gap-4" @submit.prevent="saveJob">
        <div class="grid gap-4 sm:grid-cols-[1fr_12rem]">
          <label class="field"><span class="ledger-label">Title</span><input v-model="jobForm.title" class="input" required maxlength="200" /></label>
          <label class="field"><span class="ledger-label">Type</span><input v-model="jobForm.employment_type" class="input" required maxlength="100" placeholder="Full-time" /></label>
        </div>
        <label class="field"><span class="ledger-label">Description</span><textarea v-model="jobForm.description" rows="5" class="input" required /></label>
        <label class="field">
          <span class="ledger-label">Requirements</span>
          <textarea v-model="jobForm.requirements" rows="5" class="input" placeholder="One per line" />
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="jobForm.is_active" type="checkbox" class="h-4 w-4 accent-[var(--color-flag)]" /> Open for applications on the public site
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn-ghost" @click="jobOpen = false">Cancel</button>
        <button type="submit" form="job-form" class="btn-primary" :disabled="saving">{{ jobId ? "Save" : "Publish" }}</button>
      </template>
    </Modal>
  </div>
</template>
