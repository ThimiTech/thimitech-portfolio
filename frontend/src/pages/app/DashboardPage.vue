<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import EmptyState from "../../components/app/ui/EmptyState.vue";
import StatusPill from "../../components/app/ui/StatusPill.vue";
import Avatar from "../../components/app/ui/Avatar.vue";
import PunchCard from "../../components/app/attendance/PunchCard.vue";
import { errMsg, fmtDay, STATUS_META, type TodayResponse } from "../../components/app/attendance/attendance";
import { fmtDays, type Balance, type LeaveRequest } from "../../components/app/leave/leave";
import { CATEGORY_LABEL, fmtRel, type Notice } from "../../components/app/notices/notices";
import { KIND, itemKey, npDate, npTime, type FeedItem } from "../../components/app/calendar/calendar";
import { dateLabel, isOverdue, type Task } from "../../components/app/pm/pm";

type PulseKey = "present" | "late" | "absent" | "on_leave" | "not_checked_in";
type Counts = Record<PulseKey, number> & { total: number };

interface Dashboard {
  today: TodayResponse;
  leave: { year: number; balances: Balance[]; my_pending: number };
  approvals: { count: number; items: LeaveRequest[] };
  notices: { unread: number; items: Notice[] };
  my_tasks: { open: number; overdue: number; items: Task[] };
  upcoming: { days: number; items: FeedItem[] };
  celebrations: FeedItem[];
  team: { day_kind: string; counts: Counts; pending_leave: number } | null;
  /** manager: their team; hr_admin+: everyone; null for employees */
  on_leave_today: { id: number; full_name: string; photo: string | null }[] | null;
  org: {
    day_kind: string;
    attendance: Counts;
    pending_leave: number;
    headcount: { id: number; name: string; count: number }[];
    unassigned: number;
    total_staff: number;
  } | null;
}

const { user } = useAuth();
const data = ref<Dashboard | null>(null);
const loading = ref(true);
const error = ref("");

type CountKey =
  | "leave_approvals" | "attendance_corrections" | "overdue_tasks" | "new_applications"
  | "new_inquiries" | "finance_review" | "onboarding_open" | "unread_notices";
const counts = ref<Partial<Record<CountKey, number>>>({});

// Only things that need the reader to act, most urgent first. Zero counts are left out.
const ATTENTION: { key: CountKey; one: string; many: string; to: string }[] = [
  { key: "leave_approvals", one: "leave request to decide", many: "leave requests to decide", to: "/app/leave?tab=approvals" },
  { key: "attendance_corrections", one: "attendance correction to decide", many: "attendance corrections to decide", to: "/app/attendance?tab=corrections" },
  { key: "overdue_tasks", one: "overdue task", many: "overdue tasks", to: "/app/projects" },
  { key: "new_applications", one: "new job application", many: "new job applications", to: "/app/hiring" },
  { key: "new_inquiries", one: "new inquiry", many: "new inquiries", to: "/app/inquiries" },
  { key: "finance_review", one: "finance item to review", many: "finance items to review", to: "/app/finance" },
  { key: "onboarding_open", one: "onboarding step left", many: "onboarding steps left", to: "/app/profile" },
  { key: "unread_notices", one: "unread notice", many: "unread notices", to: "/app/notices" },
];
const attention = computed(() =>
  ATTENTION.map((a) => ({ ...a, n: counts.value[a.key] ?? 0 })).filter((a) => a.n > 0),
);

async function load() {
  error.value = "";
  api.get("nav-counts/").then((r) => (counts.value = r.data)).catch(() => {});
  try {
    data.value = (await api.get<Dashboard>("dashboard/")).data;
  } catch (e) {
    error.value = errMsg(e, "Couldn't load your dashboard.");
  } finally {
    loading.value = false;
  }
}
const TASK_STATUS: Record<string, { pill: string; label: string }> = {
  backlog: { pill: "neutral", label: "Backlog" },
  active: { pill: "in_progress", label: "In progress" },
  review: { pill: "review", label: "In review" },
};

onMounted(load);

// ── Greeting (Nepal time) ───────────────────────────────
const TZ = "Asia/Kathmandu";
const hour = Number(new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", hourCycle: "h23" }).format(new Date()));
const salutation = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
const firstName = computed(() => user.value?.first_name || user.value?.full_name || "there");
const dateLine = computed(() =>
  new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date()),
);
const dayNote = computed(() => {
  const t = data.value?.today;
  if (!t || t.is_working_day) return "";
  return t.day_kind === "holiday" ? t.holiday_name ?? "Public holiday" : "Weekend";
});

// ── Leave balances ──────────────────────────────────────
function balanceBar(b: Balance) {
  const max = Math.max(b.quota, b.used + b.pending, 1);
  return { used: (100 * b.used) / max, pending: (100 * b.pending) / max };
}

// ── Upcoming route: one station per day, items placed on max(start, today) ──
const stations = computed(() => {
  const d = data.value;
  if (!d) return [];
  const today = d.today.date;
  const map = new Map<string, FeedItem[]>();
  for (const i of d.upcoming.items) {
    const day = npDate(i.start) < today ? today : npDate(i.start);
    map.set(day, [...(map.get(day) ?? []), i]);
  }
  return [...map.entries()].slice(0, 8).map(([day, items]) => ({ day, offset: daysBetween(today, day), items }));
});
function daysBetween(a: string, b: string) {
  const t = (s: string) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
  return Math.round((t(b) - t(a)) / 86400000);
}
const stationLabel = (offset: number) => (offset === 0 ? "Today" : offset === 1 ? "Tomorrow" : `D+${offset}`);
function itemDetail(i: FeedItem) {
  if (i.kind === "event") return i.all_day ? "All day" : `${npTime(i.start)}–${npTime(i.end)}${i.meta.location ? ` · ${i.meta.location}` : ""}`;
  if (i.kind === "holiday") return i.meta.is_optional ? "Optional holiday" : "Public holiday";
  if (i.kind === "leave") return i.start === i.end ? (i.meta.half_day ? "Half day" : "1 day") : `Until ${fmtDay(i.end)}`;
  return KIND[i.kind].label;
}

// ── Pulse tiles (team = manager+, org = hr_admin+) ──────
const PULSE: PulseKey[] = ["present", "late", "absent", "on_leave", "not_checked_in"];
const FILL: Record<PulseKey, string> = {
  present: "fill-moss", late: "fill-contour", absent: "fill-rust", on_leave: "fill-sky", not_checked_in: "fill-ink/15",
};
function segments(c: Counts) {
  const total = PULSE.reduce((s, k) => s + c[k], 0);
  let x = 0;
  return PULSE.filter((k) => c[k]).map((k) => {
    const w = (100 * c[k]) / total;
    const seg = { key: k, x, w };
    x += w;
    return seg;
  });
}
const describe = (c: Counts) => PULSE.map((k) => `${STATUS_META[k].label} ${c[k]}`).join(", ");

// One pulse: the whole organization for HR, otherwise the departments this manager runs.
const pulse = computed(() => {
  const d = data.value;
  if (d?.org) return { title: "Who is in today", caption: "Everyone on staff", counts: d.org.attendance, dayKind: d.org.day_kind };
  if (d?.team) return { title: "Who is in today", caption: "Departments you manage", counts: d.team.counts, dayKind: d.team.day_kind };
  return null;
});

const delay = (i: number) => ({ animationDelay: `${i * 70}ms` });
</script>

<template>
  <div class="space-y-8">
    <PageHeader eyebrow="A1 · Field log" :title="`${salutation}, ${firstName}.`">
      <template #actions>
        <RouterLink to="/app/leave?apply=1" class="btn-ghost btn-sm">Apply for leave</RouterLink>
        <RouterLink to="/app/calendar" class="btn-ghost btn-sm">Open calendar</RouterLink>
      </template>
    </PageHeader>
    <p class="-mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] uppercase tracking-[0.14em] text-ink/50">
      <span>{{ dateLine }}</span>
      <span class="text-ink/25" aria-hidden="true">/</span>
      <span>NPT · UTC+05:45</span>
      <span v-if="dayNote" class="rounded-full border border-dashed border-sky/40 px-2 py-0.5 normal-case tracking-normal text-sky">{{ dayNote }}</span>
    </p>

    <PunchCard @changed="load" />

    <section v-if="!loading && !error" class="panel" aria-labelledby="attn-title">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-3 px-5 py-4">
        <h2 id="attn-title" class="ledger-label shrink-0">Needs your attention</h2>
        <p v-if="!attention.length" class="text-sm text-ink/60">Nothing is waiting on you.</p>
        <ul v-else class="flex flex-wrap gap-2">
          <li v-for="a in attention" :key="a.key">
            <RouterLink
              :to="a.to"
              class="inline-flex items-center gap-2 rounded-full border border-ink/15 py-1 pr-3 pl-1 text-sm transition-colors hover:border-flag/50 hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
            >
              <span class="readout min-w-6 rounded-full bg-flag px-1.5 text-center text-xs leading-6 text-on-accent">{{ a.n }}</span>
              {{ a.n === 1 ? a.one : a.many }}
            </RouterLink>
          </li>
        </ul>
      </div>
    </section>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-6 lg:grid-cols-3" aria-busy="true" aria-label="Loading dashboard">
      <div v-for="n in 3" :key="n" class="panel space-y-3 p-5">
        <div class="h-3 w-28 animate-pulse rounded bg-panel" />
        <div class="h-20 animate-pulse rounded-lg border border-dashed border-ink/15" />
        <div class="h-3 w-40 animate-pulse rounded bg-panel" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="panel flex flex-col items-start gap-3 p-6 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div>
        <p class="font-display text-lg">The field log didn't come through</p>
        <p class="mt-1 text-sm text-ink/60">{{ error }}</p>
      </div>
      <button type="button" class="btn-ghost btn-sm" @click="loading = true; load()">Retry</button>
    </div>

    <template v-else-if="data">
      <!-- Pulse (manager+) -->
      <section v-if="pulse" aria-label="Attendance today">
        <article v-for="p in [pulse]" :key="p.title" class="rise panel" aria-labelledby="pulse-title">
          <div class="panel-head">
            <div>
              <h2 id="pulse-title" class="font-display text-lg">{{ p.title }}</h2>
              <p class="ledger-label mt-0.5">{{ p.caption }}</p>
            </div>
            <RouterLink to="/app/attendance?tab=team" class="font-mono text-[11px] uppercase tracking-[0.12em] text-river hover:text-flag">Team board →</RouterLink>
          </div>
          <div class="panel-body">
            <p v-if="p.counts.total === 0" class="text-sm text-ink/55">Nobody on this roll yet.</p>
            <template v-else>
              <div class="flex items-baseline gap-2">
                <span class="readout font-display text-4xl text-ink">{{ p.counts.present + p.counts.late }}</span>
                <span class="readout text-sm text-ink/50">/ {{ p.counts.total }} in</span>
                <StatusPill v-if="p.dayKind !== 'working'" class="ml-auto" :status="p.dayKind === 'holiday' ? 'holiday' : 'weekend'" />
              </div>
              <svg viewBox="0 0 100 6" preserveAspectRatio="none" class="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-panel" role="img" :aria-label="describe(p.counts)">
                <rect v-for="s in segments(p.counts)" :key="s.key" :x="s.x" :width="s.w" y="0" height="6" :class="FILL[s.key]" />
              </svg>
              <dl class="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5">
                <div v-for="k in PULSE" :key="k" class="rounded-lg border border-dashed border-ink/12 px-2.5 py-2">
                  <dt class="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-ink/50">
                    <svg viewBox="0 0 6 6" class="h-1.5 w-1.5" aria-hidden="true"><rect width="6" height="6" rx="3" :class="FILL[k]" /></svg>
                    {{ STATUS_META[k].letter }}
                    <span class="sr-only">{{ STATUS_META[k].label }}</span>
                  </dt>
                  <dd class="readout mt-0.5 text-lg text-ink" :title="STATUS_META[k].label">{{ p.counts[k] }}</dd>
                </div>
              </dl>
              <p v-if="data.on_leave_today?.length" class="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-ink/60">
                <span class="ledger-label">On leave</span>
                <RouterLink
                  v-for="person in data.on_leave_today"
                  :key="person.id"
                  :to="`/app/people/${person.id}`"
                  class="inline-flex items-center gap-1.5 rounded-full hover:text-river focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
                >
                  <Avatar :name="person.full_name" :photo="person.photo" :size="22" />{{ person.full_name }}
                </RouterLink>
              </p>
            </template>
          </div>
        </article>
      </section>

      <div class="grid gap-6 lg:grid-cols-3">
        <!-- Left column -->
        <div class="space-y-6 lg:col-span-2">
          <!-- My tasks -->
          <section class="rise panel" :style="delay(3)" aria-labelledby="tasks-title">
            <div class="panel-head">
              <div>
                <h2 id="tasks-title" class="font-display text-lg">My tasks</h2>
                <p class="ledger-label mt-0.5">Assigned to you · soonest due first</p>
              </div>
              <RouterLink to="/app/projects" class="font-mono text-[11px] uppercase tracking-[0.12em] text-river hover:text-flag">Projects →</RouterLink>
            </div>
            <EmptyState v-if="!data.my_tasks.open" title="No open tasks" hint="Tasks assigned to you on any active project board show up here." />
            <ul v-else class="divide-y divide-dashed divide-ink/10">
              <li v-for="t in data.my_tasks.items" :key="t.id">
                <RouterLink :to="`/app/projects/${t.project}`" class="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-panel/40 focus-visible:bg-panel/40 focus-visible:outline-none">
                  <span class="readout shrink-0 text-[11px] text-flag">{{ t.key }}</span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm text-ink">{{ t.title }}</span>
                    <span class="block font-mono text-[10.5px]" :class="isOverdue(t) ? 'text-rust' : 'text-ink/45'">
                      {{ isOverdue(t) ? "Overdue · " : t.due_date ? "Due " : "" }}{{ dateLabel(t.due_date) }} · {{ t.priority }}
                    </span>
                  </span>
                  <StatusPill :status="TASK_STATUS[t.status]?.pill ?? t.status" :label="TASK_STATUS[t.status]?.label" />
                </RouterLink>
              </li>
              <li v-if="data.my_tasks.open > data.my_tasks.items.length" class="px-5 py-2.5 text-xs text-ink/55">
                + {{ data.my_tasks.open - data.my_tasks.items.length }} more across your projects
              </li>
            </ul>
          </section>

          <!-- Upcoming route -->
          <section class="rise panel" :style="delay(3)" aria-labelledby="route-title">
            <div class="panel-head">
              <div>
                <h2 id="route-title" class="font-display text-lg">The road ahead</h2>
                <p class="ledger-label mt-0.5">Next {{ data.upcoming.days }} days</p>
              </div>
              <RouterLink to="/app/calendar" class="font-mono text-[11px] uppercase tracking-[0.12em] text-river hover:text-flag">Calendar →</RouterLink>
            </div>
            <div class="panel-body">
              <EmptyState v-if="!stations.length" title="Clear terrain ahead" hint="No holidays, events or leave in the next two weeks." />
              <ol v-else class="relative ml-1.5 border-l border-dashed border-ink/20">
                <li v-for="s in stations" :key="s.day" class="relative pb-5 pl-6 last:pb-0">
                  <span class="absolute -left-[6px] top-1 h-[11px] w-[11px] rounded-full border-2 border-sheet"
                    :class="s.offset === 0 ? 'bg-flag' : 'bg-river'" aria-hidden="true" />
                  <p class="font-mono text-[10.5px] uppercase tracking-[0.14em]" :class="s.offset === 0 ? 'text-flag' : 'text-ink/50'">
                    {{ stationLabel(s.offset) }} · {{ fmtDay(s.day) }}
                  </p>
                  <ul class="mt-1.5 grid gap-1.5">
                    <li v-for="i in s.items" :key="itemKey(i)" class="flex min-w-0 items-start gap-2.5">
                      <span class="mt-0.5 shrink-0 rounded border px-1.5 py-px font-mono text-[9.5px] tracking-wider" :class="KIND[i.kind].chip">
                        {{ KIND[i.kind].prefix }}
                      </span>
                      <span class="min-w-0">
                        <span class="block truncate text-sm text-ink">{{ i.title }}</span>
                        <span class="block font-mono text-[10.5px] text-ink/45">{{ itemDetail(i) }}</span>
                      </span>
                    </li>
                  </ul>
                </li>
              </ol>
            </div>
          </section>
        </div>

        <!-- Right column -->
        <div class="space-y-6">
          <!-- Notices -->
          <section class="rise panel" :style="delay(5)" aria-labelledby="notice-title">
            <div class="panel-head">
              <h2 id="notice-title" class="font-display text-lg">Notice board</h2>
              <RouterLink to="/app/notices" class="font-mono text-[11px] uppercase tracking-[0.12em] text-river hover:text-flag">
                {{ data.notices.unread ? `${data.notices.unread} unread →` : "All notices →" }}
              </RouterLink>
            </div>
            <p v-if="!data.notices.items.length" class="panel-body text-sm text-ink/55">Nothing posted yet.</p>
            <ul v-else class="divide-y divide-dashed divide-ink/10">
              <li v-for="n in data.notices.items" :key="n.id">
                <RouterLink to="/app/notices" class="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-panel/40 focus-visible:bg-panel/40 focus-visible:outline-none">
                  <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full" :class="n.is_read ? 'border border-ink/20' : 'bg-flag'" aria-hidden="true" />
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm" :class="n.is_read ? 'text-ink/70' : 'font-medium text-ink'">
                      <span v-if="!n.is_read" class="sr-only">Unread: </span>{{ n.title }}
                    </span>
                    <span class="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[10.5px] text-ink/45">
                      <span>{{ fmtRel(n.publish_at) }}</span>
                      <span v-if="n.pinned">· pinned</span>
                    </span>
                  </span>
                  <StatusPill v-if="n.category !== 'general'" :status="n.category" :label="CATEGORY_LABEL[n.category]" />
                </RouterLink>
              </li>
            </ul>
          </section>

          <!-- Leave balances -->
          <section v-if="!pulse" class="rise panel" :style="delay(2)" aria-labelledby="bal-title">
            <div class="panel-head">
              <div>
                <h2 id="bal-title" class="font-display text-lg">Leave balance</h2>
                <p class="ledger-label mt-0.5">{{ data.leave.year }} · days remaining</p>
              </div>
              <RouterLink to="/app/leave" class="font-mono text-[11px] uppercase tracking-[0.12em] text-river hover:text-flag">
                {{ data.leave.my_pending ? `${data.leave.my_pending} pending →` : "My leave →" }}
              </RouterLink>
            </div>
            <div class="panel-body">
              <EmptyState v-if="!data.leave.balances.length" title="No leave types yet" hint="HR hasn't set up leave types." />
              <ul v-else class="grid gap-3">
                <li v-for="b in data.leave.balances" :key="b.leave_type.id" class="rounded-lg border border-ink/10 bg-paper/50 p-3.5">
                  <p class="flex items-center gap-2 text-sm font-medium">
                    <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: b.leave_type.color || 'var(--color-river)' }" aria-hidden="true" />
                    <span class="truncate">{{ b.leave_type.name }}</span>
                    <span v-if="!b.leave_type.is_paid" class="ml-auto font-mono text-[9.5px] uppercase tracking-wider text-ink/40">Unpaid</span>
                  </p>
                  <p class="mt-2 flex items-baseline gap-1.5">
                    <span class="readout font-display text-3xl text-ink">{{ b.remaining === null ? fmtDays(b.used) : fmtDays(b.remaining) }}</span>
                    <span class="readout text-xs text-ink/50">{{ b.remaining === null ? "used · no fixed quota" : `of ${fmtDays(b.quota)} left` }}</span>
                  </p>
                  <svg v-if="b.quota > 0" viewBox="0 0 100 4" preserveAspectRatio="none" class="mt-2.5 h-1.5 w-full rounded-full bg-panel" role="img"
                    :aria-label="`${fmtDays(b.used)} used, ${fmtDays(b.pending)} pending, of ${fmtDays(b.quota)}`">
                    <rect x="0" :width="balanceBar(b).used" height="4" class="fill-river" />
                    <rect :x="balanceBar(b).used" :width="balanceBar(b).pending" height="4" class="fill-contour/60" />
                  </svg>
                  <p v-if="b.pending" class="mt-1.5 font-mono text-[10px] text-ink/45">{{ fmtDays(b.pending) }} pending</p>
                </li>
              </ul>
            </div>
          </section>

        </div>
      </div>
    </template>
  </div>
</template>
