<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/api'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import AttendanceTrend from '@/components/app/oversight/AttendanceTrend.vue'
import ProjectHealth from '@/components/app/oversight/ProjectHealth.vue'
import { label, type Overview } from '@/components/app/oversight/oversight'
import { money } from '@/components/app/finance/finance'
import { timestamp } from '@/components/app/inventory/inventory'
const data = ref<Overview | null>(null)
const busy = ref(false)
const error = ref('')
const start = ref('')
const end = ref('')
const today = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Kathmandu',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}).format(new Date())
async function load() {
  busy.value = true
  error.value = ''
  try {
    const response = await api.get<Overview>('monitoring/overview/', {
      params: {
        ...(start.value ? { start: start.value } : {}),
        ...(end.value ? { end: end.value } : {}),
      },
    })
    data.value = response.data
    start.value = response.data.attendance_window.start
    end.value = response.data.attendance_window.end
  } catch {
    error.value =
      'Could not load monitoring. Choose an attendance window of up to 93 days, ending no later than today, and try again.'
  } finally {
    busy.value = false
  }
}
onMounted(load)
</script>
<template>
  <div :aria-busy="busy">
    <PageHeader
      eyebrow="Super admin · oversight"
      title="A view across Thimi Tech."
      description="People, delivery, and resources. A working picture of the organization."
      ><template #actions
        ><RouterLink class="btn-ghost" to="/app/audit">Audit trail ↗</RouterLink
        ><button class="btn-ink" :disabled="busy" @click="load">
          {{ busy ? 'Refreshing…' : 'Refresh overview' }}
        </button></template
      ></PageHeader
    >
    <div v-if="error" class="mb-6 border-l-2 border-rust bg-rust/5 p-4 text-sm" role="alert">
      {{ error
      }}<span v-if="data" class="mt-1 block">The last successful snapshot remains below.</span>
    </div>
    <p v-if="busy && !data" role="status" class="py-16 text-sm text-ink/65">
      Gathering the organization snapshot…
    </p>
    <template v-if="data">
      <div
        class="flex flex-wrap justify-between gap-2 border-t border-ink/15 pt-3 font-mono text-[10px] uppercase tracking-wider text-ink/65"
      >
        <p>Organization snapshot · {{ data.as_of }}</p>
        <p>Updated {{ timestamp(data.generated_at) }} NPT</p>
      </div>
      <dl class="grid grid-cols-2 gap-6 border-b border-ink/15 py-7 lg:grid-cols-4">
        <div>
          <dt class="ledger-label">Active staff</dt>
          <dd class="readout mt-3 text-4xl">{{ data.headcount.total }}</dd>
          <dd class="mt-2 text-xs text-ink/65">
            {{ data.headcount.joined_this_month }} joined this month
          </dd>
        </div>
        <div>
          <dt class="ledger-label">Attendance rate</dt>
          <dd class="readout mt-3 text-4xl">
            {{ data.attendance.rate === null ? '—' : `${data.attendance.rate}%` }}
          </dd>
          <dd class="mt-2 text-xs text-ink/65">
            {{ data.attendance.totals.attended }} / {{ data.attendance.totals.expected }} resolved
            working days
          </dd>
        </div>
        <div>
          <dt class="ledger-label">Overdue tasks</dt>
          <dd class="readout mt-3 text-4xl" :class="data.projects.overdue_tasks ? 'text-rust' : ''">
            {{ data.projects.overdue_tasks }}
          </dd>
          <dd class="mt-2 text-xs text-ink/65">
            Across {{ data.projects.active }} active projects
          </dd>
        </div>
        <div>
          <dt class="ledger-label">Paid leave remaining</dt>
          <dd class="readout mt-3 text-4xl">
            {{ Number(data.leave.remaining_paid_days)
            }}<span class="ml-1 text-base text-ink/60">days</span>
          </dd>
          <dd class="mt-2 text-xs text-ink/65">Capped paid quotas · {{ data.leave.year }}</dd>
        </div>
      </dl>
    </template>
    <section class="mt-8" aria-labelledby="attendance-title">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="ledger-label">01 / People & presence</p>
          <h2 id="attendance-title" class="mt-2 font-display text-xl">The attendance picture</h2>
        </div>
        <form class="flex flex-wrap items-end gap-3" @submit.prevent="load">
          <label class="field"
            ><span class="ledger-label">From</span
            ><input
              v-model="start"
              class="input"
              type="date"
              min="1900-01-01"
              :max="end || today"
              :disabled="busy"
              required /></label
          ><label class="field"
            ><span class="ledger-label">Through</span
            ><input
              v-model="end"
              class="input"
              type="date"
              :min="start || '1900-01-01'"
              :max="today"
              :disabled="busy"
              required /></label
          ><button class="btn-ghost" :disabled="busy" type="submit">Apply dates</button>
        </form>
      </div>
      <template v-if="data"
        ><p class="mt-3 text-xs text-ink/65">
          {{ data.attendance.roster_basis }}. {{ data.attendance_window.start }} —
          {{ data.attendance_window.end }}. Dates affect attendance only; the other sections show
          the current organization.
        </p>
        <AttendanceTrend :days="data.attendance.days" />
        <p class="mt-3 text-xs leading-relaxed text-ink/65">
          Rate = present + late / present + late + absent on working days. Today’s unchecked staff,
          leave, weekends, and holidays are excluded from the rate.
        </p></template
      >
    </section>
    <template v-if="data">
      <div class="mt-8 grid gap-8 border-y border-ink/15 py-7 lg:grid-cols-2">
        <section class="min-w-0" aria-labelledby="headcount-title">
          <div class="flex justify-between gap-3">
            <h2 id="headcount-title" class="font-display text-xl">Where the team sits</h2>
            <RouterLink to="/app/people" class="text-xs underline underline-offset-4"
              >People ↗</RouterLink
            >
          </div>
          <ul class="mt-5 space-y-4">
            <li v-for="d in data.headcount.by_department" :key="d.id">
              <div class="flex justify-between gap-3 text-sm">
                <span>{{ d.name }}</span
                ><span class="font-mono">{{ d.count }}</span>
              </div>
              <div class="mt-2 h-1 bg-ink/10" aria-hidden="true">
                <div
                  class="h-full bg-ink/65"
                  :style="{
                    width: `${data.headcount.total ? (d.count / data.headcount.total) * 100 : 0}%`,
                  }"
                />
              </div>
            </li>
          </ul>
          <p class="mt-4 text-xs text-ink/65">
            {{ data.headcount.unassigned }} without a department. Active staff include employees,
            managers, HR admins, and super admins.
          </p>
          <p class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink/65">
            <span v-for="r in data.headcount.by_role" :key="r.role"
              >{{ label(r.role) }} · {{ r.count }}</span
            >
          </p>
        </section>
        <section class="min-w-0" aria-labelledby="leave-title">
          <div class="flex justify-between gap-3">
            <h2 id="leave-title" class="font-display text-xl">
              Leave exposure · {{ data.leave.year }}
            </h2>
            <RouterLink to="/app/leave" class="text-xs underline underline-offset-4"
              >Leave ↗</RouterLink
            >
          </div>
          <p class="mt-3 text-xs text-ink/65">
            {{ data.leave.pending_requests }} pending requests ·
            {{ Number(data.leave.pending_paid_days) }} paid days requested this year
          </p>
          <div class="mt-4 overflow-x-auto">
            <table class="ledger-table">
              <thead>
                <tr>
                  <th>Paid type</th>
                  <th>Used</th>
                  <th>Pending</th>
                  <th>Remaining</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in data.leave.by_type" :key="t.id">
                  <th scope="row" class="text-left font-normal">{{ t.name }}</th>
                  <td>{{ Number(t.used_days) }}</td>
                  <td>{{ Number(t.pending_days) }}</td>
                  <td>{{ t.remaining_days === null ? 'Unlimited' : Number(t.remaining_days) }}</td>
                </tr>
                <tr v-if="!data.leave.by_type.length">
                  <td colspan="4">No active paid leave types.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="mt-3 text-xs text-ink/65">
            Days across current active staff. Pending requests do not reduce remaining quotas.
            Unlimited types are excluded from the remaining total. No cash-out value is assumed.
          </p>
        </section>
      </div>
      <section class="mt-8" aria-labelledby="projects-title">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p class="ledger-label">02 / Delivery</p>
            <h2 id="projects-title" class="mt-2 font-display text-xl">Project health</h2>
          </div>
          <p class="text-xs text-ink/65">
            {{ data.projects.total_tasks }} tasks · {{ data.projects.unassigned_tasks }} unfinished
            & unassigned · {{ data.projects.archived }} archived projects excluded
          </p>
        </div>
        <div class="mt-5"><ProjectHealth :projects="data.projects.by_project" /></div>
        <p class="mt-3 text-xs text-ink/65">
          At risk: an unfinished project past its due date, or any overdue unfinished task.
          Complete: every task is done. Unplanned: no tasks yet.
        </p>
      </section>
      <section class="mt-8 border-t border-ink/15 pt-7" aria-labelledby="finance-title">
        <div class="flex justify-between gap-3">
          <div>
            <p class="ledger-label">03 / Resources</p>
            <h2 id="finance-title" class="mt-2 font-display text-xl">Finance, by currency</h2>
          </div>
          <RouterLink to="/app/finance" class="self-end text-xs underline underline-offset-4"
            >Finance ↗</RouterLink
          >
        </div>
        <p class="mt-3 text-xs text-ink/65">
          All recorded periods. Currencies are kept separate. Approved expenses include paid claims;
          outstanding invoices are issued and unpaid.
        </p>
        <div class="mt-5 overflow-x-auto">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>Currency</th>
                <th>Payroll paid</th>
                <th>Expenses approved</th>
                <th>Invoices outstanding</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in data.finance.currencies" :key="c.currency">
                <th scope="row" class="text-left font-mono font-normal">{{ c.currency }}</th>
                <td class="whitespace-nowrap">{{ money(c.payroll_paid, c.currency) }}</td>
                <td class="whitespace-nowrap">{{ money(c.expenses_approved, c.currency) }}</td>
                <td class="whitespace-nowrap">{{ money(c.invoice_outstanding, c.currency) }}</td>
              </tr>
              <tr v-if="!data.finance.currencies.length">
                <td colspan="4">No finalized financial activity recorded yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="mt-3 text-xs text-ink/65">
          {{ data.finance.draft_payslips }} draft payslips ·
          {{ data.finance.submitted_expenses }} expenses awaiting a decision
        </p>
      </section>
      <div class="mt-8 grid gap-8 border-t border-ink/15 pt-7 lg:grid-cols-2">
        <section class="min-w-0" aria-labelledby="inventory-title">
          <div class="flex justify-between gap-3">
            <h2 id="inventory-title" class="font-display text-xl">Equipment in circulation</h2>
            <RouterLink to="/app/inventory" class="text-xs underline underline-offset-4"
              >Inventory ↗</RouterLink
            >
          </div>
          <dl class="mt-5 grid grid-cols-3 gap-5">
            <div
              v-for="s in [
                'total',
                'available',
                'assigned',
                'maintenance',
                'retired',
                'overdue',
              ] as const"
              :key="s"
            >
              <dt class="ledger-label">{{ s === 'overdue' ? 'Overdue returns' : s }}</dt>
              <dd class="readout mt-2 text-2xl">{{ data.inventory[s] }}</dd>
            </div>
          </dl>
        </section>
        <section class="min-w-0" aria-labelledby="audit-title">
          <div class="flex justify-between gap-3">
            <h2 id="audit-title" class="font-display text-xl">Recent changes</h2>
            <RouterLink to="/app/audit" class="text-xs underline underline-offset-4"
              >Audit trail ↗</RouterLink
            >
          </div>
          <p class="mt-3 text-xs text-ink/65">
            {{ data.audit.last_24h }} events in the last 24 hours.
          </p>
          <ul class="mt-4 divide-y divide-ink/10">
            <li v-for="e in data.audit.recent" :key="e.id" class="py-3 text-xs">
              <div class="flex flex-wrap justify-between gap-2">
                <span>{{ e.actor_label }} · {{ e.action }}</span
                ><time :datetime="e.timestamp" class="text-ink/60">{{
                  timestamp(e.timestamp)
                }}</time>
              </div>
              <p class="mt-1 font-mono text-[10px] text-ink/65">
                {{ e.target_model }} #{{ e.target_id }}
              </p>
            </li>
          </ul>
          <p v-if="!data.audit.recent.length" class="mt-4 text-sm text-ink/65">
            No changes captured yet.
          </p>
        </section>
      </div>
    </template>
  </div>
</template>
