<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/api'
import AssetDialog from '@/components/app/inventory/AssetDialog.vue'
import AssignmentDialog from '@/components/app/inventory/AssignmentDialog.vue'
import CategoriesPanel from '@/components/app/inventory/CategoriesPanel.vue'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import TabBar from '@/components/app/ui/TabBar.vue'
import DataTable, { type Column } from '@/components/app/ui/DataTable.vue'
import EmptyState from '@/components/app/ui/EmptyState.vue'
import StatusPill from '@/components/app/ui/StatusPill.vue'
import SkeletonBlock from '@/components/app/ui/SkeletonBlock.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import { useServerTable } from '@/components/app/ui/serverTable'
import {
  timestamp,
  type Asset,
  type Assignment,
  type Category,
  type InventorySummary,
} from '@/components/app/inventory/inventory'
import { type Staff } from '@/components/app/finance/finance'
const categories = ref<Category[]>([])
const staff = ref<Staff[]>([])
const summary = ref<InventorySummary | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const tab = ref('Assets')
const TABS = ['Assets', 'Assignments', 'Categories'].map((id) => ({ id, label: id }))
const status = ref('all')
const editor = ref(false)
const selected = ref<Asset | null>(null)
const assignmentAsset = ref<Asset | null>(null)
const assignmentMode = ref<'assign' | 'return'>('assign')
const historyAsset = ref<Asset | null>(null)
const STATUSES = ['available', 'assigned', 'maintenance', 'retired']

// Both registers are paged, searched and sorted on the server.
const assets = useServerTable<Asset>('inventory/assets/', {
  params: () => ({ status: status.value === 'all' ? undefined : status.value }),
})
const history = useServerTable<Assignment>('inventory/assignments/', {
  params: () => ({ asset: historyAsset.value?.id }),
})

const columns: Column<Asset>[] = [
  { key: 'tag', label: 'Tag', sortable: true, class: 'whitespace-nowrap' },
  { key: 'name', label: 'Asset', sortable: true, class: 'min-w-44' },
  { key: 'category_name', label: 'Category', sortable: true, orderBy: 'category__name' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'assigned_to', label: 'Assigned to', class: 'min-w-36' },
  { key: 'actions', label: 'Actions', srOnly: true, class: 'text-right' },
]
const historyColumns: Column<Assignment>[] = [
  { key: 'asset_tag', label: 'Asset', sortable: true, orderBy: 'asset__tag', class: 'min-w-36' },
  { key: 'employee_name', label: 'Staff member', sortable: true, orderBy: 'employee__first_name' },
  { key: 'assigned_at', label: 'Assigned (NPT)', sortable: true, class: 'min-w-36' },
  { key: 'due_back', label: 'Expected return', sortable: true },
  { key: 'returned_at', label: 'Returned (NPT)', sortable: true, class: 'min-w-36' },
  { key: 'condition', label: 'Condition / notes', class: 'min-w-48' },
]
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kathmandu' }).format(new Date())
async function load(initial = false) {
  if (initial) loading.value = true
  refreshing.value = true
  error.value = ''
  try {
    const [c, p, s] = await Promise.all([
      api.get<Category[]>('inventory/categories/'),
      api.get<Staff[]>('org/people/', { params: { is_active: true } }),
      api.get<InventorySummary>('inventory/summary/'),
      assets.load(),
      history.load(),
    ])
    categories.value = c.data
    staff.value = p.data
    summary.value = s.data
  } catch {
    error.value = 'Could not load inventory. Please try again.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}
function edit(asset?: Asset) {
  selected.value = asset || null
  editor.value = true
}
function assignment(asset: Asset, mode: 'assign' | 'return') {
  assignmentMode.value = mode
  assignmentAsset.value = asset
}
function showHistory(asset: Asset) {
  historyAsset.value = asset
  tab.value = 'Assignments'
}
onMounted(() => load(true))
</script>
<template>
  <div>
    <PageHeader
      eyebrow="Administration · Inventory"
      title="Inventory"
      description="The asset register, handovers, and the full return history."
    >
      <template #actions>
        <button
          v-if="tab === 'Assets'"
          class="btn-primary"
          :disabled="!categories.length"
          :title="categories.length ? undefined : 'Add a category first'"
          @click="edit()"
        >
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          Register asset
        </button>
      </template>
    </PageHeader>

    <dl v-if="summary" class="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div
        v-for="s in [
          { label: 'Total assets', value: summary.total },
          { label: 'Available', value: summary.available },
          { label: 'Assigned', value: summary.assigned },
          { label: 'Overdue returns', value: summary.overdue },
        ]"
        :key="s.label"
        class="panel p-4"
      >
        <dt class="ledger-label">{{ s.label }}</dt>
        <dd class="readout mt-1 font-display text-[28px]" :class="s.label === 'Overdue returns' && s.value ? 'text-flag' : ''">{{ s.value }}</dd>
      </div>
    </dl>

    <TabBar v-model="tab" :tabs="TABS" label="Inventory views" id-prefix="inv" class="mb-6" />

    <SkeletonBlock v-if="loading" :rows="5" height="h-12" label="Loading inventory" />
    <LoadError v-else-if="error" :message="error" :busy="refreshing" @retry="load(true)" />
    <div v-else :id="`inv-panel-${tab}`" role="tabpanel" :aria-labelledby="`inv-tab-${tab}`" :aria-busy="refreshing">
      <template v-if="tab === 'Assets'">
        <div v-if="!categories.length" class="panel">
          <EmptyState title="No asset categories yet" hint="Categories group your equipment (laptops, survey gear, vehicles). Add one to start registering assets.">
            <button class="btn-ghost btn-sm" @click="tab = 'Categories'">Manage categories</button>
          </EmptyState>
        </div>
        <template v-else>
          <LoadError v-if="assets.error.value" :message="assets.error.value" :busy="assets.loading.value" @retry="assets.load()" />
          <DataTable
            v-model:page="assets.page.value"
            v-model:search="assets.search.value"
            v-model:ordering="assets.ordering.value"
            :rows="assets.rows.value"
            :total="assets.total.value"
            :loading="assets.loading.value"
            :page-size="assets.pageSize"
            :columns="columns"
            :row-key="(a) => a.id"
            caption="Asset register"
            search-placeholder="Tag, name, serial, location, category…"
            empty-title="No assets in this view"
            empty-hint="Register equipment to begin tracking it, or change the status filter."
          >
            <template #toolbar>
              <label class="sr-only" for="inv-status">Asset status</label>
              <select id="inv-status" v-model="status" class="input w-auto capitalize">
                <option value="all">All statuses</option>
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
            </template>
            <template #cell-tag="{ row }"><span class="readout text-xs text-flag">{{ row.tag }}</span></template>
            <template #cell-name="{ row }">
              <span class="font-medium text-ink">{{ row.name }}</span>
              <span class="block text-xs text-ink/55">{{ row.serial_number || 'No serial' }} · {{ row.location || 'No location' }}</span>
            </template>
            <template #cell-status="{ row }"><StatusPill :status="row.status" /></template>
            <template #cell-assigned_to="{ row }">
              <template v-if="row.assigned_to">
                {{ row.assigned_to.name }}
                <span
                  v-if="row.assigned_to.due_back"
                  class="block text-xs"
                  :class="row.assigned_to.due_back < today ? 'text-rust' : 'text-ink/55'"
                >{{ row.assigned_to.due_back < today ? 'Overdue · ' : 'Return by ' }}{{ row.assigned_to.due_back }}</span>
              </template>
              <span v-else class="text-ink/40">—</span>
            </template>
            <template #cell-actions="{ row }">
              <div class="flex justify-end gap-1.5">
                <button
                  v-if="row.status === 'available'"
                  class="btn-ink btn-sm"
                  :aria-label="'Assign asset ' + row.tag"
                  @click="assignment(row, 'assign')"
                >Assign</button>
                <button
                  v-if="row.assigned_to"
                  class="btn-ink btn-sm"
                  :aria-label="'Return asset ' + row.tag"
                  @click="assignment(row, 'return')"
                >Return</button>
                <button class="btn-ghost btn-sm" :aria-label="'Edit asset ' + row.tag" @click="edit(row)">Edit</button>
                <button class="btn-ghost btn-sm" :aria-label="'Assignment history for ' + row.tag" @click="showHistory(row)">History</button>
              </div>
            </template>
          </DataTable>
        </template>
      </template>
      <section v-else-if="tab === 'Assignments'">
        <LoadError v-if="history.error.value" :message="history.error.value" :busy="history.loading.value" @retry="history.load()" />
        <DataTable
          v-model:page="history.page.value"
          v-model:search="history.search.value"
          v-model:ordering="history.ordering.value"
          :rows="history.rows.value"
          :total="history.total.value"
          :loading="history.loading.value"
          :page-size="history.pageSize"
          :columns="historyColumns"
          :row-key="(a) => a.id"
          caption="Assignment history"
          search-placeholder="Asset tag, name, or staff member…"
          empty-title="No assignments recorded"
          empty-hint="Handovers and returns appear here once an asset is assigned."
        >
          <template v-if="historyAsset" #toolbar>
            <span class="inline-flex items-center gap-2 rounded-full border border-ink/15 px-3 py-1 text-sm">
              Only {{ historyAsset.tag }} · {{ historyAsset.name }}
              <button type="button" class="rounded text-ink/50 hover:text-ink" :aria-label="'Show all assets, not just ' + historyAsset.tag" @click="historyAsset = null">✕</button>
            </span>
          </template>
          <template #cell-asset_tag="{ row }">
            <span class="readout text-xs text-flag">{{ row.asset_tag }}</span>
            <p class="mt-1 text-xs text-ink/60">{{ row.asset_name }}</p>
          </template>
          <template #cell-assigned_at="{ row }">{{ timestamp(row.assigned_at) }}</template>
          <template #cell-due_back="{ row }">{{ row.due_back || 'Open-ended' }}</template>
          <template #cell-returned_at="{ row }">
            <template v-if="row.returned_at">{{ timestamp(row.returned_at) }}</template>
            <StatusPill v-else status="assigned" label="Still assigned" />
          </template>
          <template #cell-condition="{ row }">
            {{ row.return_condition || 'On loan' }}
            <p v-if="row.notes" class="mt-1 text-xs text-ink/60">Handover: {{ row.notes }}</p>
            <p v-if="row.return_note" class="mt-1 text-xs text-ink/60">Return: {{ row.return_note }}</p>
          </template>
        </DataTable>
      </section>
      <CategoriesPanel v-else :categories="categories" @changed="load()" />
    </div>
    <AssetDialog
      :open="editor"
      :asset="selected"
      :categories="categories"
      @close="editor = false"
      @saved="load()"
    /><AssignmentDialog
      :asset="assignmentAsset"
      :staff="staff"
      :mode="assignmentMode"
      @close="assignmentAsset = null"
      @saved="load()"
    />
  </div>
</template>
