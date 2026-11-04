<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import api from '@/api/api'
import SkeletonBlock from '../ui/SkeletonBlock.vue'
import { toast } from '../ui/toast'
import { amount, dateLabel, downloadFrom, KIND_LABEL, saveBlob, type CategoryKind, type Overview, type PartyRow } from './finance'

const props = defineProps<{ fy: string }>()
const data = ref<Overview | null>(null)
const parties = ref<PartyRow[]>([])
const statement = ref<HTMLElement | null>(null)
const busy = ref('')
watch(() => props.fy, async () => {
  data.value = null
  const [o, p] = await Promise.all([
    api.get<Overview>('finance/reports/overview/', { params: { fy: props.fy } }),
    api.get<PartyRow[]>('finance/reports/parties/', { params: { fy: props.fy } }),
  ]).catch(() => [null, null])
  data.value = o?.data || null
  parties.value = p?.data || []
}, { immediate: true })

const sections = computed(() => {
  const d = data.value
  if (!d) return []
  const of = (k: string) => d.categories.filter((c) => c.kind === k)
  return (['income', 'payroll', 'expense', 'tax'] as CategoryKind[]).map((k) => ({
    kind: k, label: KIND_LABEL[k], rows: of(k), total: Number(k === 'income' ? d.kinds[k].in : d.kinds[k].out), sign: k === 'income' ? 1 : -1,
  }))
})
const transfers = computed(() => data.value?.categories.filter((c) => c.kind === 'transfer' || c.kind === 'uncategorized') || [])

const REGISTERS = [
  { what: 'ledger', label: 'Bank & cash ledger', hint: 'Every line with Miti, category, running balance' },
  { what: 'payroll', label: 'Payroll register', hint: 'Salary sheet for the whole year: SSF, TDS, net, bank' },
  { what: 'statutory', label: 'TDS & SSF schedule', hint: 'Withheld per month with due dates' },
  { what: 'claims', label: 'Staff claims', hint: 'Out-of-pocket spending and reimbursement status' },
  { what: 'invoices', label: 'Invoices', hint: 'Issued, paid and outstanding' },
  { what: 'categories', label: 'Category summary', hint: 'Totals per category' },
  { what: 'parties', label: 'Party ledger', hint: 'Money in/out per person or company' },
  { what: 'accounts', label: 'Accounts & reconciliation', hint: 'Opening/closing per account, statement match' },
]
async function dl(path: string, params: Record<string, string>, label: string) {
  busy.value = label
  try {
    await downloadFrom(path, { fy: props.fy, ...params })
  } catch {
    toast.error('Download failed.')
  } finally {
    busy.value = ''
  }
}
function word() {
  if (!statement.value) return
  const html = `<html><head><meta charset="utf-8"><style>body{font-family:Calibri,Arial,sans-serif;font-size:11pt}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;padding:4px 6px;text-align:left}.r{text-align:right}</style></head><body>${statement.value.innerHTML}</body></html>`
  saveBlob(new Blob(['﻿', html], { type: 'application/msword' }), `thimitech-statement-FY${props.fy.replace('/', '-')}.doc`)
}
const print = () => window.print()
</script>

<template>
  <SkeletonBlock v-if="!data" :rows="5" height="h-16" label="Loading reports" />
  <div v-else class="grid grid-cols-[minmax(0,1fr)] gap-8">
    <section class="grid gap-3">
      <div>
        <h2 class="text-lg font-medium">For the CA</h2>
        <p class="text-sm text-ink/60">One download with everything for FY {{ fy }}: an Excel workbook (one sheet per register), a summary with balances and reconciliation, and every document tagged to the year.</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="btn-ink" :disabled="!!busy" @click="dl('finance/export/audit-pack/', {}, 'pack')">{{ busy === 'pack' ? 'Preparing…' : 'Download audit pack (.zip)' }}</button>
        <button class="btn-ghost" :disabled="!!busy" @click="dl('finance/export/', { what: 'book', type: 'xlsx' }, 'book')">Complete workbook (Excel)</button>
        <RouterLink to="/app/drive?space=finance" class="btn-ghost">Share documents with the CA →</RouterLink>
      </div>
    </section>

    <section class="panel relative overflow-x-auto">
      <table class="ledger-table">
        <thead><tr><th>Register</th><th class="text-right">Download</th></tr></thead>
        <tbody>
          <tr v-for="r in REGISTERS" :key="r.what">
            <td><span class="block text-ink">{{ r.label }}</span><span class="text-xs text-ink/55">{{ r.hint }}</span></td>
            <td class="text-right whitespace-nowrap">
              <button class="btn-ghost btn-sm" :disabled="!!busy" @click="dl('finance/export/', { what: r.what, type: 'xlsx' }, r.what)">Excel</button>
              <button class="btn-ghost btn-sm ml-2" :disabled="!!busy" @click="dl('finance/export/', { what: r.what, type: 'csv' }, r.what)">CSV</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="fin-print">
      <div class="no-print mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-medium">Income and spending statement</h2>
        <div class="flex gap-2"><button class="btn-ghost btn-sm" @click="print">Print / PDF</button><button class="btn-ghost btn-sm" @click="word">Word</button></div>
      </div>
      <div ref="statement" class="panel p-6">
        <h3 class="font-display text-xl text-ink">Thimi Tech Pvt. Ltd.</h3>
        <p class="text-sm text-ink/60">Income and spending, FY {{ fy }} ({{ dateLabel(data.start) }} – {{ dateLabel(data.end) }}). Cash basis, NPR.</p>
        <table class="ledger-table mt-4">
          <tbody>
            <template v-for="s in sections" :key="s.kind">
              <tr><th colspan="2" class="pt-5">{{ s.label }}</th></tr>
              <tr v-for="c in s.rows" :key="c.name"><td class="pl-6">{{ c.name }}</td><td class="r readout text-right">{{ amount(s.kind === 'income' ? c.in : c.out) }}</td></tr>
              <tr class="font-medium"><td>Total {{ s.label.toLowerCase() }}</td><td class="r readout text-right">{{ amount(s.total) }}</td></tr>
            </template>
            <tr><th colspan="2" class="pt-5">Paid by staff (claims, not yet through the bank)</th></tr>
            <tr class="font-medium"><td>Total staff-paid spending</td><td class="r readout text-right">{{ amount(data.claims_spent) }}</td></tr>
            <tr class="text-base font-semibold"><td class="pt-4">Result (income − all spending)</td><td class="r readout pt-4 text-right">{{ amount(data.result) }}</td></tr>
          </tbody>
        </table>
        <template v-if="transfers.length">
          <h4 class="mt-6 font-medium text-ink">Loans, capital and transfers (not income or spending)</h4>
          <table class="ledger-table mt-2">
            <thead><tr><th>Category</th><th class="r text-right">In</th><th class="r text-right">Out</th></tr></thead>
            <tbody><tr v-for="c in transfers" :key="c.name"><td>{{ c.name }}</td><td class="r readout text-right">{{ amount(c.in) }}</td><td class="r readout text-right">{{ amount(c.out) }}</td></tr></tbody>
          </table>
        </template>
      </div>
    </section>

    <section>
      <h2 class="mb-1 text-lg font-medium">Who money moved with</h2>
      <p class="mb-3 text-sm text-ink/60">Per person or company, FY {{ fy }}. Useful for loans to/from directors and recurring vendors.</p>
      <div class="panel relative overflow-x-auto">
        <table class="ledger-table text-[13px]">
          <thead><tr><th>Party</th><th class="text-right">In</th><th class="text-right">Out</th><th class="text-right">Net</th><th>Lines</th><th>Categories</th></tr></thead>
          <tbody>
            <tr v-for="p in parties" :key="p.party">
              <td class="text-ink">{{ p.party }}</td>
              <td class="readout text-right">{{ Number(p.in) ? amount(p.in) : '' }}</td>
              <td class="readout text-right">{{ Number(p.out) ? amount(p.out) : '' }}</td>
              <td class="readout text-right">{{ amount(p.net) }}</td>
              <td>{{ p.entries }}</td>
              <td class="text-xs text-ink/60">{{ p.categories.join(', ') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style>
@media print {
  body * { visibility: hidden; }
  .fin-print, .fin-print * { visibility: visible; }
  .fin-print { position: absolute; inset: 0 auto auto 0; width: 100%; }
  .fin-print .no-print { display: none !important; }
}
</style>
