<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import Modal from "../ui/Modal.vue";
import { AUDIENCE_LABEL, npDate, npTime, parseError, type Audience, type CalendarEvent } from "./calendar";

interface Department { id: number; name: string; manager: { id: number; full_name: string } | null }
interface Person { id: number; full_name: string; role: string; is_active?: boolean; designation?: string; department: { id: number; name: string } | null }

const props = defineProps<{ open: boolean; eventId: number | null; defaultDate: string }>();
const emit = defineEmits<{ close: []; saved: [event: CalendarEvent] }>();

const { user, hasRole } = useAuth();
const isHR = computed(() => hasRole("hr_admin"));

// ── Reference data (loaded once, degrades gracefully) ──
const departments = ref<Department[]>([]);
const people = ref<Person[]>([]);
const peopleError = ref(false);
let refLoaded = false;

async function loadRefs() {
  if (refLoaded) return;
  refLoaded = true; // blocks concurrent re-entry; reset below on failure so the next open retries
  peopleError.value = false;
  const [d, p] = await Promise.allSettled([api.get<Department[]>("org/departments/"), api.get<Person[]>("org/people/")]);
  const depOk = d.status === "fulfilled" && Array.isArray(d.value.data);
  const peopleOk = p.status === "fulfilled" && Array.isArray(p.value.data);
  if (depOk) departments.value = d.value.data;
  if (peopleOk) people.value = p.value.data.filter((x) => x.role !== "guest" && x.is_active !== false);
  else peopleError.value = true;
  if (!depOk || !peopleOk) refLoaded = false;
}

const allowedDepartments = computed(() =>
  isHR.value ? departments.value : departments.value.filter((d) => d.manager?.id === user.value?.id),
);

const audienceOptions = computed<Audience[]>(() => {
  const opts: Audience[] = isHR.value ? ["organization", "department", "private"] : hasRole("manager") && allowedDepartments.value.length ? ["department", "private"] : ["private"];
  // Keep an existing event's audience selectable even if the role list no longer offers it.
  if (!opts.includes(form.audience)) opts.push(form.audience);
  return opts;
});

// ── Form ──
const blank = () => ({
  title: "",
  description: "",
  location: "",
  all_day: false,
  start_date: props.defaultDate,
  start_time: "10:00",
  end_date: props.defaultDate,
  end_time: "11:00",
  audience: (isHR.value ? "organization" : "private") as Audience,
  department: null as number | null,
  attendees: [] as number[],
});
const form = reactive(blank());
const errors = ref<Record<string, string>>({});
const detail = ref("");
const loading = ref(false);
const loadError = ref("");
const saving = ref(false);
const search = ref("");

async function init() {
  Object.assign(form, blank());
  errors.value = {};
  detail.value = "";
  loadError.value = "";
  search.value = "";
  void loadRefs();
  if (props.eventId == null) return;
  loading.value = true;
  try {
    const { data } = await api.get<CalendarEvent>(`calendar/events/${props.eventId}/`);
    Object.assign(form, {
      title: data.title,
      description: data.description,
      location: data.location,
      all_day: data.all_day,
      start_date: npDate(data.start),
      start_time: npTime(data.start),
      end_date: npDate(data.end),
      end_time: npTime(data.end),
      audience: data.audience,
      department: data.department,
      attendees: [...data.attendees],
    });
    // Attendees the people list might not include (e.g. directory unavailable).
    for (const a of data.attendees_detail)
      if (!people.value.some((p) => p.id === a.id)) extraNames.value[a.id] = a.full_name;
  } catch (e) {
    loadError.value = parseError(e).detail || "Couldn't load this event.";
  } finally {
    loading.value = false;
  }
}
const extraNames = ref<Record<number, string>>({});

watch(
  () => props.open,
  (o) => o && init(),
  { immediate: true },
);
watch(
  () => form.start_date,
  (s, old) => {
    // Keep end in step when the start date moves forward past it.
    if (form.end_date === old || form.end_date < s) form.end_date = s;
  },
  // sync: during hydration end_date is assigned right after start_date and must win.
  { flush: "sync" },
);
watch(
  () => form.audience,
  (a) => {
    if (a === "department" && form.department == null && allowedDepartments.value.length === 1)
      form.department = allowedDepartments.value[0]!.id;
  },
);

const filteredPeople = computed(() => {
  const q = search.value.trim().toLowerCase();
  return q ? people.value.filter((p) => p.full_name.toLowerCase().includes(q) || p.department?.name.toLowerCase().includes(q)) : people.value;
});
const nameOf = (id: number) => people.value.find((p) => p.id === id)?.full_name ?? extraNames.value[id] ?? `#${id}`;
function toggle(id: number) {
  const i = form.attendees.indexOf(id);
  if (i >= 0) form.attendees.splice(i, 1);
  else form.attendees.push(id);
}

const iso = (d: string, t: string) => `${d}T${t.length === 5 ? `${t}:00` : t}+05:45`;

async function submit() {
  errors.value = {};
  detail.value = "";
  const start = form.all_day ? iso(form.start_date, "00:00") : iso(form.start_date, form.start_time);
  const end = form.all_day ? iso(form.end_date, "23:59") : iso(form.end_date, form.end_time);
  if (!form.title.trim()) errors.value.title = "Give the event a title.";
  if (!form.start_date || !form.end_date) errors.value.start = "Pick a start and end.";
  else if (new Date(end) < new Date(start)) errors.value.end = "End must be the same as or after start.";
  if (form.audience === "department" && !form.department) errors.value.department = "Choose a department.";
  if (Object.keys(errors.value).length) return;

  const payload = {
    title: form.title.trim(),
    description: form.description,
    location: form.location,
    all_day: form.all_day,
    start,
    end,
    audience: form.audience,
    department: form.audience === "department" ? form.department : null,
    attendees: form.attendees,
  };
  saving.value = true;
  try {
    const { data } = props.eventId == null
      ? await api.post<CalendarEvent>("calendar/events/", payload)
      : await api.patch<CalendarEvent>(`calendar/events/${props.eventId}/`, payload);
    emit("saved", data);
  } catch (e) {
    const err = parseError(e);
    errors.value = err.fields;
    detail.value = err.detail;
  } finally {
    saving.value = false;
  }
}

const fid = (n: string) => `evt-${n}`;
</script>

<template>
  <Modal :open="open" :title="eventId == null ? 'New event' : 'Edit event'" width="max-w-xl" @close="emit('close')">
    <div v-if="loading" class="space-y-3" aria-busy="true" aria-label="Loading event">
      <div v-for="n in 4" :key="n" class="h-10 animate-pulse rounded-lg border border-dashed border-ink/15 bg-panel/40" />
    </div>
    <div v-else-if="loadError" class="text-sm text-rust" role="alert">
      {{ loadError }}
      <button type="button" class="btn-ghost btn-sm ml-2" @click="init">Retry</button>
    </div>

    <form v-else id="event-form" class="grid gap-4" novalidate @submit.prevent="submit">
      <p v-if="detail" class="rounded-lg border border-rust/30 bg-rust/10 px-3 py-2 text-sm text-rust" role="alert">{{ detail }}</p>

      <div class="field">
        <label :for="fid('title')" class="ledger-label">Title</label>
        <input :id="fid('title')" v-model="form.title" class="input" maxlength="200" required :aria-invalid="!!errors.title" :aria-describedby="errors.title ? fid('title-err') : undefined" />
        <p v-if="errors.title" :id="fid('title-err')" class="text-xs text-rust">{{ errors.title }}</p>
      </div>

      <label class="flex items-center gap-2 text-sm">
        <input v-model="form.all_day" type="checkbox" class="h-4 w-4 accent-flag" />
        All-day event
      </label>

      <fieldset class="grid gap-3 sm:grid-cols-2">
        <legend class="sr-only">When</legend>
        <div class="field">
          <label :for="fid('sd')" class="ledger-label">Starts</label>
          <div class="flex gap-2">
            <input :id="fid('sd')" v-model="form.start_date" type="date" class="input" required />
            <input v-if="!form.all_day" v-model="form.start_time" type="time" class="input w-28 shrink-0" aria-label="Start time" required />
          </div>
          <p v-if="errors.start" class="text-xs text-rust">{{ errors.start }}</p>
        </div>
        <div class="field">
          <label :for="fid('ed')" class="ledger-label">Ends</label>
          <div class="flex gap-2">
            <input :id="fid('ed')" v-model="form.end_date" type="date" class="input" :min="form.start_date" required />
            <input v-if="!form.all_day" v-model="form.end_time" type="time" class="input w-28 shrink-0" aria-label="End time" required />
          </div>
          <p v-if="errors.end" class="text-xs text-rust">{{ errors.end }}</p>
        </div>
      </fieldset>
      <p class="-mt-2 font-mono text-[10.5px] text-ink/45">Times are Nepal time (UTC+05:45).</p>

      <div class="field">
        <label :for="fid('loc')" class="ledger-label">Location <span class="normal-case tracking-normal text-ink/35">(optional)</span></label>
        <input :id="fid('loc')" v-model="form.location" class="input" maxlength="200" />
        <p v-if="errors.location" class="text-xs text-rust">{{ errors.location }}</p>
      </div>

      <div class="field">
        <label :for="fid('desc')" class="ledger-label">Notes <span class="normal-case tracking-normal text-ink/35">(optional)</span></label>
        <textarea :id="fid('desc')" v-model="form.description" class="input min-h-20" rows="3" />
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <div class="field">
          <label :for="fid('aud')" class="ledger-label">Audience</label>
          <select :id="fid('aud')" v-model="form.audience" class="input" :disabled="audienceOptions.length === 1">
            <option v-for="a in audienceOptions" :key="a" :value="a">{{ AUDIENCE_LABEL[a] }}</option>
          </select>
          <p v-if="errors.audience" class="text-xs text-rust">{{ errors.audience }}</p>
          <p v-else-if="audienceOptions.length === 1" class="text-xs text-ink/45">Private events are visible to you and your attendees.</p>
        </div>
        <div v-if="form.audience === 'department'" class="field">
          <label :for="fid('dept')" class="ledger-label">Department</label>
          <select :id="fid('dept')" v-model="form.department" class="input" :aria-invalid="!!errors.department">
            <option :value="null" disabled>Select…</option>
            <option v-for="d in allowedDepartments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <p v-if="errors.department" class="text-xs text-rust">{{ errors.department }}</p>
        </div>
      </div>

      <fieldset class="field">
        <legend class="ledger-label mb-1.5">Attendees <span class="normal-case tracking-normal text-ink/35">({{ form.attendees.length }} selected)</span></legend>
        <ul v-if="form.attendees.length" class="flex flex-wrap gap-1.5" aria-label="Selected attendees">
          <li v-for="id in form.attendees" :key="id">
            <button type="button" class="inline-flex items-center gap-1 rounded-full border border-ink/15 bg-panel/60 px-2 py-0.5 text-xs hover:border-rust/40 hover:text-rust" :aria-label="`Remove ${nameOf(id)}`" @click="toggle(id)">
              {{ nameOf(id) }} <span aria-hidden="true">×</span>
            </button>
          </li>
        </ul>
        <p v-if="peopleError" class="text-xs text-ink/50">The staff directory isn't available right now — attendees can be added later.</p>
        <template v-else>
          <input v-model="search" type="search" class="input" placeholder="Search people or departments" aria-label="Search attendees" />
          <div class="max-h-44 overflow-y-auto rounded-lg border border-dashed border-ink/15">
            <label v-for="p in filteredPeople" :key="p.id" class="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-panel/50">
              <input type="checkbox" class="h-4 w-4 accent-flag" :checked="form.attendees.includes(p.id)" @change="toggle(p.id)" />
              <span class="min-w-0 flex-1 truncate">{{ p.full_name }}</span>
              <span v-if="p.department" class="truncate font-mono text-[10.5px] text-ink/45">{{ p.department.name }}</span>
            </label>
            <p v-if="!filteredPeople.length" class="px-3 py-3 text-xs text-ink/50">{{ people.length ? "No matches." : "Loading people…" }}</p>
          </div>
        </template>
        <p v-if="errors.attendees" class="text-xs text-rust">{{ errors.attendees }}</p>
      </fieldset>
    </form>

    <template #footer>
      <button type="button" class="btn-ghost" @click="emit('close')">Cancel</button>
      <button type="submit" form="event-form" class="btn-primary" :disabled="saving || loading || !!loadError">
        {{ saving ? "Saving…" : eventId == null ? "Create event" : "Save changes" }}
      </button>
    </template>
  </Modal>
</template>
