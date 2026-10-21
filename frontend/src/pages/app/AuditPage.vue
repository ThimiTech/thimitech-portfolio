<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '@/api/api'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import AuditDetail from '@/components/app/oversight/AuditDetail.vue'
import {
  label,
  type AuditEvent,
  type AuditOptions,
  type AuditPage,
} from '@/components/app/oversight/oversight'
import { timestamp } from '@/components/app/inventory/inventory'
const options = ref<AuditOptions | null>(null)
const result = ref<AuditPage | null>(null)
const selected = ref<AuditEvent | null>(null)
const busy = ref(false)
const error = ref('')
const page = ref(1)
const filters = ref({
  search: '',
  module: '',
  action: '',
  source: '',
  actor: '',
  start: '',
  end: '',
  request_id: '',
})
const applied = ref<Record<string, string>>({})
const pages = computed(() => Math.max(1, Math.ceil((result.value?.count ?? 0) / 25)))
async function load() {
  busy.value = true
  error.value = ''
  try {
    if (!options.value) options.value = (await api.get<AuditOptions>('audit/options/')).data
    result.value = (
      await api.get<AuditPage>('audit/events/', { params: { ...applied.value, page: page.value } })
    ).data
  } catch {
    result.value = null
    error.value = 'Could not load the audit trail. Check the filters and try again.'
  } finally {
    busy.value = false
  }
}
function apply() {
  page.value = 1
  applied.value = Object.fromEntries(Object.entries(filters.value).filter(([, v]) => v !== ''))
  void load()
}
function reset() {
  for (const key of Object.keys(filters.value) as (keyof typeof filters.value)[])
    filters.value[key] = ''
  apply()
}
function trace(id: string) {
  for (const key of Object.keys(filters.value) as (keyof typeof filters.value)[])
    filters.value[key] = ''
  filters.value.request_id = id
  selected.value = null
  apply()
}
function turn(delta: number) {
  page.value += delta
  void load()
}
onMounted(load)
</script>
<template>
  <div>
    <PageHeader
      eyebrow="Super admin · oversight"
      title="The record of change."
      description="Who changed what, and when. An append-only trail across Thimi Tech OS."
      ><template #actions
        ><RouterLink class="btn-ghost" to="/app/monitoring"
          >Organization overview ↗</RouterLink
        ></template
      ></PageHeader
    >
    <form class="border-y border-ink/15 py-5" @submit.prevent="apply">
      <fieldset :disabled="busy" class="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <legend class="sr-only">Filter audit events</legend>
        <label class="field sm:col-span-2"
          ><span class="ledger-label">Actor name, model, or record ID</span
          ><input
            v-model="filters.search"
            class="input"
            type="search"
            maxlength="100"
            placeholder="Search the ledger…"
        /></label>
        <label class="field"
          ><span class="ledger-label">Module</span
          ><select v-model="filters.module" class="input">
            <option value="">All modules</option>
            <option v-for="m in options?.modules" :key="m" :value="m">{{ label(m) }}</option>
          </select></label
        >
        <label class="field"
          ><span class="ledger-label">Action</span
          ><select v-model="filters.action" class="input">
            <option value="">All actions</option>
            <option v-for="a in options?.actions" :key="a" :value="a">{{ label(a) }}</option>
          </select></label
        >
        <label class="field"
          ><span class="ledger-label">From · NPT</span
          ><input
            v-model="filters.start"
            class="input"
            type="date"
            min="1900-01-01"
            max="2999-12-31"
        /></label>
        <label class="field"
          ><span class="ledger-label">Through · NPT</span
          ><input
            v-model="filters.end"
            class="input"
            type="date"
            :min="filters.start || '1900-01-01'"
            max="2999-12-31"
        /></label>
        <label class="field"
          ><span class="ledger-label">Source</span
          ><select v-model="filters.source" class="input">
            <option value="">All sources</option>
            <option v-for="s in options?.sources" :key="s" :value="s">{{ s }}</option>
          </select></label
        >
        <label class="field"
          ><span class="ledger-label">Actor ID</span
          ><input
            v-model="filters.actor"
            class="input"
            type="number"
            min="1"
            step="1"
            placeholder="Any actor"
        /></label>
        <label class="field sm:col-span-2 lg:col-span-3"
          ><span class="ledger-label">Request ID</span
          ><input
            v-model="filters.request_id"
            class="input font-mono text-xs"
            placeholder="UUID from an event or X-Request-ID"
            pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        /></label>
        <div class="flex items-end gap-2">
          <button class="btn-ink" type="submit">Apply filters</button
          ><button class="btn-ghost" type="button" @click="reset">Reset</button>
        </div>
      </fieldset>
    </form>
    <p class="my-4 text-xs text-ink/65">
      {{
        options?.capture_started_at
          ? `Capture began ${timestamp(options.capture_started_at)} NPT.`
          : 'Events appear as changes are made.'
      }}
      Earlier activity is not reconstructed. Sensitive values are redacted.
    </p>
    <div v-if="error" role="alert" class="panel p-6">
      <p>{{ error }}</p>
      <button class="btn-ghost mt-3" :disabled="busy" @click="load">Retry</button>
    </div>
    <p v-else-if="busy" role="status" class="py-12 text-sm text-ink/65">Reading audit events…</p>
    <template v-else-if="result">
      <p class="mb-3 font-mono text-xs text-ink/65" role="status">
        {{ result.count }} matching events · newest first
      </p>
      <p v-if="!result.results.length" class="panel p-8 text-sm text-ink/65">
        No events match these filters. Try another date range or reset the filters.
      </p>
      <div v-else class="panel overflow-x-auto">
        <table class="ledger-table">
          <caption class="sr-only">
            Audit events, newest first
          </caption>
          <thead>
            <tr>
              <th>Recorded · NPT</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Record</th>
              <th>Source</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in result.results" :key="e.id">
              <td class="whitespace-nowrap text-xs">{{ timestamp(e.timestamp) }}</td>
              <td>
                {{ e.actor_label
                }}<span class="mt-1 block text-xs text-ink/60">{{ label(e.actor_role) }}</span>
              </td>
              <td>
                <span class="font-mono text-xs">{{ e.action }}</span>
              </td>
              <td>
                <span class="font-mono text-xs">{{ e.target_model }}</span
                ><span class="mt-1 block text-xs text-ink/60">#{{ e.target_id }}</span>
              </td>
              <td class="text-xs">{{ e.source }}</td>
              <td>
                <button
                  class="btn-ghost btn-sm whitespace-nowrap"
                  :aria-label="`Inspect event ${e.id}`"
                  @click="selected = e"
                >
                  Inspect ↗
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav class="mt-5 flex items-center justify-between gap-3" aria-label="Audit pagination">
        <button class="btn-ghost btn-sm" :disabled="!result.previous" @click="turn(-1)">
          ← Previous
        </button>
        <p class="text-xs text-ink/65">Page {{ page }} of {{ pages }}</p>
        <button class="btn-ghost btn-sm" :disabled="!result.next" @click="turn(1)">Next →</button>
      </nav>
    </template>
    <AuditDetail :event="selected" @close="selected = null" @trace="trace" />
  </div>
</template>
