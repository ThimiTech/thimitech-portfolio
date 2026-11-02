<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/api'
import DataTable, { type Column } from '../ui/DataTable.vue'
import StatusPill from '../ui/StatusPill.vue'
import LoadError from '../org/LoadError.vue'
import { useServerTable } from '../ui/serverTable'
import { toast } from '../ui/toast'
import { errorMessage } from '../pm/pm'
import TransactionDialog from './TransactionDialog.vue'
import ImportDialog from './ImportDialog.vue'
import StatementsStrip from './StatementsStrip.vue'
import { amount, categoriesByKind, dateLabel, downloadFrom, lookups, loadLookups, type Txn } from './finance'

const props = defineProps<{ fy: string }>()
const route = useRoute()
const q = (k: string) => (typeof route.query[k] === 'string' ? (route.query[k] as string) : '')
const filters = reactive({ account: q('account'), category: q('category'), status: q('status'), direction: '', employee: q('employee'), project: q('project') })
const table = useServerTable<Txn>('finance/transactions/', {
  pageSize: 25,
  params: () => ({ fy: props.fy, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) }),
})
table.ordering.value = '-date'
onMounted(table.load)
watch(() => route.query, () => Object.assign(filters, { account: q('account'), category: q('category'), status: q('status') }))

const columns: Column<Txn>[] = [
  { key: 'pick', label: 'Select', srOnly: true, class: 'w-8' },
  { key: 'date', label: 'Date', sortable: true },
  { key: 'description', label: 'Description', class: 'min-w-64' },
  { key: 'category', label: 'Category', class: 'min-w-44' },
  { key: 'debit', label: 'Out', sortable: true, class: 'text-right' },
  { key: 'credit', label: 'In', sortable: true, class: 'text-right' },
  { key: 'balance', label: 'Balance', class: 'text-right' },
  { key: 'status', label: 'Status', sortable: true },
]
const groups = computed(() => categoriesByKind(lookups.categories))
const account = computed(() => lookups.accounts.find((a) => String(a.id) === filters.account))

// ---- quick review
async function patch(t: Txn, data: Partial<Txn>) {
  try {
    Object.assign(t, (await api.patch<Txn>(`finance/transactions/${t.id}/`, data)).data)
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
const picked = ref<Set<number>>(new Set())
const bulkCategory = ref<number | ''>('')
function toggle(id: number) {
  const s = new Set(picked.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  picked.value = s
}
const allOnPage = computed(() => table.rows.value.length > 0 && table.rows.value.every((r) => picked.value.has(r.id)))
function toggleAll() {
  picked.value = allOnPage.value ? new Set() : new Set(table.rows.value.map((r) => r.id))
}
async function bulk(change: Record<string, unknown>) {
  try {
    const { data } = await api.post<{ updated: number }>('finance/transactions/bulk/', { ids: [...picked.value], ...change })
    toast.success(`${data.updated} lines updated`)
    picked.value = new Set()
    bulkCategory.value = ''
    table.load()
  } catch (e) {
    toast.error(errorMessage(e))
  }
}

// ---- dialogs
const editing = ref<Txn | null>(null)
const creating = ref(false)
const importing = ref(false)
function changed() {
  table.load()
  loadLookups().catch(() => {})
}
function exportLedger(type: 'csv' | 'xlsx') {
  downloadFrom('finance/export/', { what: 'ledger', type, fy: props.fy }).catch(() => toast.error('Export failed.'))
}
</script>

<template>
  <section class="grid grid-cols-[minmax(0,1fr)] gap-4">
    <div class="flex flex-wrap gap-2" role="group" aria-label="Accounts">
      <button type="button" class="rounded-lg border px-3 py-2 text-left text-sm transition"
        :class="!filters.account ? 'border-ink bg-ink text-paper' : 'border-ink/15 hover:border-ink/30'" @click="filters.account = ''">
        All accounts
      </button>
      <button v-for="a in lookups.accounts" :key="a.id" type="button" class="rounded-lg border px-3 py-2 text-left transition"
        :class="filters.account === String(a.id) ? 'border-ink bg-ink text-paper' : 'border-ink/15 hover:border-ink/30'"
        :aria-pressed="filters.account === String(a.id)" @click="filters.account = String(a.id)">
        <span class="block text-sm">{{ a.name }}</span>
        <span class="readout block text-xs opacity-70">{{ a.currency }} {{ amount(a.balance) }}</span>
      </button>
    </div>

    <StatementsStrip v-if="account" :account="account" :fy="fy" @changed="changed" />

    <div class="flex flex-wrap items-center gap-2">
      <button class="btn-ink" @click="creating = true">+ Add entry</button>
      <button class="btn-ghost" @click="importing = true">Import statement (CSV / Excel)</button>
      <span class="flex-1" />
      <button class="btn-ghost btn-sm" @click="exportLedger('xlsx')">Excel</button>
      <button class="btn-ghost btn-sm" @click="exportLedger('csv')">CSV</button>
    </div>

    <div v-if="picked.size" class="flex flex-wrap items-center gap-2 rounded-lg border border-river/30 bg-river/5 px-4 py-2.5 text-sm" role="region" aria-label="Bulk actions">
      <span class="font-medium">{{ picked.size }} selected</span>
      <label class="sr-only" for="bulk-cat">Category for selected</label>
      <select id="bulk-cat" v-model="bulkCategory" class="input w-auto py-1.5">
        <option value="">Set category…</option>
        <optgroup v-for="g in groups" :key="g.kind" :label="g.label">
          <option v-for="c in g.items" :key="c.id" :value="c.id">{{ c.name }}</option>
        </optgroup>
      </select>
      <button class="btn-ghost btn-sm" :disabled="!bulkCategory" @click="bulk({ category: bulkCategory })">Apply</button>
      <button class="btn-ink btn-sm" @click="bulk({ status: 'confirmed' })">Mark checked</button>
      <button class="btn-ghost btn-sm" @click="picked = new Set()">Clear</button>
    </div>

    <LoadError v-if="table.error.value" :message="table.error.value" :busy="table.loading.value" @retry="table.load()" />
    <DataTable
      v-model:page="table.page.value"
      v-model:search="table.search.value"
      v-model:ordering="table.ordering.value"
      :rows="table.rows.value"
      :total="table.total.value"
      :loading="table.loading.value"
      :page-size="table.pageSize"
      :columns="columns"
      :row-key="(r) => r.id"
      :caption="`Ledger FY ${fy}`"
      search-placeholder="Description, party, reference, note…"
      empty-title="No lines in this view"
      empty-hint="Add an entry, import a statement, or change the filters."
    >
      <template #toolbar>
        <select v-model="filters.category" class="input w-auto" aria-label="Category">
          <option value="">All categories</option>
          <option value="none">Not categorised</option>
          <optgroup v-for="g in groups" :key="g.kind" :label="g.label">
            <option v-for="c in g.items" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
          </optgroup>
        </select>
        <select v-model="filters.status" class="input w-auto" aria-label="Status">
          <option value="">Any status</option>
          <option value="review">Needs review</option>
          <option value="confirmed">Checked</option>
        </select>
        <select v-model="filters.direction" class="input w-auto" aria-label="Direction">
          <option value="">In and out</option>
          <option value="in">Money in</option>
          <option value="out">Money out</option>
        </select>
        <button v-if="filters.employee || filters.project" class="btn-ghost btn-sm" @click="filters.employee = filters.project = ''">Clear person/project filter</button>
        <label class="flex items-center gap-1.5 text-xs text-ink/60"><input type="checkbox" class="accent-ink" :checked="allOnPage" @change="toggleAll" /> Select page</label>
      </template>
      <template #cell-pick="{ row }">
        <input type="checkbox" class="accent-ink" :checked="picked.has(row.id)" :aria-label="`Select ${row.description}`" @change="toggle(row.id)" />
      </template>
      <template #cell-date="{ row }">
        <span class="block whitespace-nowrap text-ink">{{ dateLabel(row.date) }}</span>
        <span class="readout block text-[11px] text-ink/50">{{ row.bs_date }} BS</span>
      </template>
      <template #cell-description="{ row }">
        <button type="button" class="text-left hover:underline" @click="editing = row">
          <span class="block text-ink">{{ row.party || row.description }}</span>
          <span v-if="row.party" class="block text-xs text-ink/55">{{ row.description }}</span>
        </button>
        <span class="mt-1 flex flex-wrap gap-1 text-[11px]">
          <span v-if="!filters.account" class="rounded bg-ink/[0.05] px-1.5 py-0.5 text-ink/60">{{ row.account_name }}</span>
          <span v-if="row.employee_name" class="rounded bg-sky/10 px-1.5 py-0.5 text-sky">{{ row.employee_name }}</span>
          <span v-if="row.project_name" class="rounded bg-moss/10 px-1.5 py-0.5 text-moss">Project · {{ row.project_name }}</span>
          <span v-if="row.payslip_label" class="rounded bg-ink/[0.05] px-1.5 py-0.5 text-ink/70">Payslip {{ row.payslip_label }}</span>
          <span v-if="row.invoice_number" class="rounded bg-ink/[0.05] px-1.5 py-0.5 text-ink/70">Invoice {{ row.invoice_number }}</span>
          <span v-if="row.files" class="rounded bg-ink/[0.05] px-1.5 py-0.5 text-ink/70">{{ row.files }} file{{ row.files > 1 ? "s" : "" }}</span>
        </span>
        <span v-if="row.note" class="mt-1 block max-w-md text-xs text-ink/55">{{ row.note }}</span>
      </template>
      <template #cell-category="{ row }">
        <select class="input py-1 text-xs" :class="!row.category && 'border-contour/60'" :value="row.category ?? ''" :aria-label="`Category for ${row.description}`"
          @change="patch(row, { category: ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null })">
          <option value="">— choose —</option>
          <optgroup v-for="g in groups" :key="g.kind" :label="g.label">
            <option v-for="c in g.items" :key="c.id" :value="c.id">{{ c.name }}</option>
          </optgroup>
        </select>
      </template>
      <template #cell-debit="{ row }"><span class="readout whitespace-nowrap text-chart-out">{{ Number(row.debit) ? amount(row.debit) : "" }}</span></template>
      <template #cell-credit="{ row }"><span class="readout whitespace-nowrap text-chart-in">{{ Number(row.credit) ? amount(row.credit) : "" }}</span></template>
      <template #cell-balance="{ row }"><span class="readout whitespace-nowrap text-ink/60">{{ row.balance === null ? '' : amount(row.balance) }}</span></template>
      <template #cell-status="{ row }">
        <div class="flex items-center gap-1.5">
          <StatusPill :status="row.status === 'review' ? 'pending' : 'approved'" :label="row.status === 'review' ? 'Review' : 'Checked'" />
          <button v-if="row.status === 'review'" type="button" class="btn-ghost btn-sm px-2" :aria-label="`Mark ${row.description} as checked`" @click="patch(row, { status: 'confirmed' })">✓</button>
        </div>
      </template>
    </DataTable>

    <TransactionDialog :open="creating || !!editing" :txn="editing" :default-account="filters.account ? Number(filters.account) : undefined"
      @close="creating = false; editing = null" @saved="changed" />
    <ImportDialog :open="importing" :default-account="filters.account ? Number(filters.account) : undefined" @close="importing = false" @imported="changed" />
  </section>
</template>
