import { reactive, ref, watch } from 'vue'
import api from '@/api/api'
export interface Staff {
  id: number
  full_name: string
  email: string
}
export interface PayAmounts {
  basic: string
  allowances: string
  deductions: string
  gross: string
  net: string
  currency: string
}
export interface Salary extends PayAmounts {
  id: number
  employee: number
  employee_name: string
  effective_from: string
  active: boolean
  ssf_enrolled: boolean
  bank_name: string
  bank_account: string
  pan: string
  notes: string
}
export interface Payslip extends PayAmounts {
  id: number
  employee: number
  employee_name: string
  employee_meta: { designation: string; join_date: string | null; pan: string; bank_name: string; bank_account: string; ssf_enrolled: boolean }
  bonus: string
  working_days: number | null
  days_worked: number | null
  ssf_employee: string
  ssf_employer: string
  tds: string
  earned: string
  total_deductions: string
  cost_to_company: string
  transaction_ids: number[]
  period: string
  status: string
  notes: string
  payment_reference: string
  issued_at: string | null
  paid_at: string | null
}
export interface FileRef {
  id: number
  name: string
  title: string
  extension: string
  size: number
  url: string
}
export interface Expense {
  id: number
  employee: number
  employee_name: string
  description: string
  date: string
  category: number | null
  category_name: string
  project: number | null
  project_name: string
  files: FileRef[]
  amount: string
  currency: string
  status: string
  notes: string
  decision_note: string
  payment_reference: string
}
export interface InvoiceLine {
  description: string
  quantity: string
  unit_price: string
  line_total?: string
}
export interface Invoice {
  id: number
  number: string
  client_name: string
  client_email: string
  project: number | null
  project_name: string
  issue_date: string
  due_date: string
  currency: string
  tax_amount: string
  subtotal: string
  total: string
  items: InvoiceLine[]
  notes: string
  status: string
  payment_reference: string
}
export interface FinanceSummary {
  currencies: {
    currency: string
    payroll_paid: string
    expenses_approved: string
    invoice_outstanding: string
  }[]
  draft_payslips: number
  submitted_expenses: number
}
export function money(value: string, currency = 'NPR') {
  try {
    return new Intl.NumberFormat('en-NP', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(Number(value))
  } catch {
    return `${currency} ${value}`
  }
}
export function staffName(staff: Staff) {
  return staff.full_name || staff.email
}
/** GET finance/my-payslips/ — the signed-in employee's issued/paid slips. */
export interface MyPayslip extends PayAmounts {
  fiscal_year: string
  bonus: string
  working_days: number | null
  days_worked: number | null
  earned: string
  ssf_employee: string
  ssf_employer: string
  tds: string
  total_deductions: string
  id: number
  employee_name: string
  employee_email: string
  designation: string
  department: string
  period: string
  status: 'issued' | 'paid'
  notes: string
  payment_reference: string
  issued_at: string | null
  paid_at: string | null
}
export function monthLabel(period: string) {
  return new Date(period + 'T00:00:00').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
}

// ---------------------------------------------------------------- books

export type CategoryKind = 'income' | 'expense' | 'payroll' | 'tax' | 'transfer'
export const KIND_LABEL: Record<CategoryKind | 'uncategorized', string> = {
  income: 'Income',
  expense: 'Operating expense',
  payroll: 'Payroll',
  tax: 'Tax & statutory',
  transfer: 'Transfer / loan / capital',
  uncategorized: 'Not categorised yet',
}
export interface Category {
  id: number
  name: string
  kind: CategoryKind
  description: string
  active: boolean
  entries?: number
}
export interface Account {
  id: number
  name: string
  kind: 'bank' | 'cash' | 'card' | 'wallet'
  institution: string
  number: string
  currency: string
  opening_balance: string
  opening_date: string
  active: boolean
  notes: string
  balance: string
  entries: number
}
export interface Txn {
  id: number
  account: number
  account_name: string
  currency: string
  date: string
  bs_date: string
  fiscal_year: string
  description: string
  reference: string
  party: string
  category: number | null
  category_name: string
  category_kind: CategoryKind | ''
  debit: string
  credit: string
  balance: string | null
  note: string
  status: 'review' | 'confirmed'
  employee: number | null
  employee_name: string
  project: number | null
  project_name: string
  payslip: number | null
  payslip_label: string
  expense: number | null
  expense_label: string
  invoice: number | null
  invoice_number: string
  files: number
}
export interface Statement {
  id: number
  account: number
  account_name: string
  start: string
  end: string
  opening_balance: string
  closing_balance: string
  notes: string
  files: FileRef[]
  reconciliation: { computed_opening: string; computed_closing: string; difference: string; reconciled: boolean; bs_start: string; bs_end: string }
}
export interface FiscalYear {
  name: string
  start: string
  end: string
  closed: boolean
  close: { id: number; notes: string; closed_by_name: string; closed_at: string } | null
}
export interface Money2 {
  in: string
  out: string
}
export interface Overview {
  fy: string
  start: string
  end: string
  currency: string
  cash: string
  accounts: { id: number; name: string; kind: string; currency: string; active: boolean; balance: string; fy_in: string; fy_out: string; entries: number }[]
  kinds: Record<CategoryKind | 'uncategorized', Money2>
  income: string
  spent: string
  claims_spent: string
  result: string
  months: { label: string; start: string; end: string; in: string; out: string; operating_out: string; payroll: string }[]
  categories: { id: number | null; name: string; kind: string; out: string; in: string; entries: number }[]
  payroll: { gross: string; net: string; ssf_employee: string; ssf_employer: string; tds: string; cost: string; slips: number }
  owed_to_staff: { employee: number; name: string; amount: string; claims: number }[]
  receivable: string
  claims_waiting: number
  to_review: number
  uncategorized: number
  monthly_burn: string
  runway_months: number | null
  statutory: Record<'tds' | 'ssf', { accrued: string; deposited: string; outstanding: string }>
}
export interface Statutory {
  fy: string
  months: { period: string; tds: string; ssf_employee: string; ssf_employer: string; ssf_total: string; tds_due: string; ssf_due: string }[]
  totals: Overview['statutory']
}
export interface PartyRow {
  party: string
  in: string
  out: string
  net: string
  entries: number
  last: string
  categories: string[]
}

/** The fiscal year chosen in the finance hub (remembered per browser). */
const FY_KEY = 'finance.fy'
function readFy() {
  try {
    return localStorage.getItem(FY_KEY) || ''
  } catch {
    return ''
  }
}
export const fiscalYear = ref<string>(readFy())
watch(fiscalYear, (v) => {
  try {
    localStorage.setItem(FY_KEY, v)
  } catch {
    /* storage blocked: the choice just isn't remembered */
  }
})

/** Nepali digit grouping without a currency symbol: 12,34,567.00 */
export function amount(value: string | number | null | undefined, decimals = 2) {
  return Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
/** 1.20 L / 3.40 Cr style for tight spaces (axis ticks). */
export function shortAmount(value: string | number) {
  const n = Math.abs(Number(value || 0))
  const sign = Number(value) < 0 ? '−' : ''
  if (n >= 1e7) return sign + (n / 1e7).toFixed(2) + ' Cr'
  if (n >= 1e5) return sign + (n / 1e5).toFixed(1) + ' L'
  if (n >= 1e3) return sign + (n / 1e3).toFixed(0) + 'k'
  return sign + n.toFixed(0)
}
export function dateLabel(iso: string | null | undefined) {
  return iso ? new Date(iso.slice(0, 10) + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
}

/** Download an authenticated file (export, zip) through the API client. */
export async function downloadFrom(path: string, params: Record<string, unknown> = {}, fallbackName = 'download') {
  const res = await api.get<Blob>(path, { params, responseType: 'blob' })
  const disposition = String(res.headers['content-disposition'] || '')
  saveBlob(res.data, /filename="?([^";]+)"?/.exec(disposition)?.[1] || fallbackName)
}
export function saveBlob(blob: Blob, name: string) {
  const href = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href, download: name })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

export interface Lookup {
  id: number
  name: string
}
/** Pick-lists shared by every finance panel; loaded once per page visit. */
export const lookups = reactive({
  staff: [] as Staff[],
  projects: [] as Lookup[],
  categories: [] as Category[],
  accounts: [] as Account[],
})
export async function loadLookups() {
  const [staff, projects, categories, accounts] = await Promise.all([
    api.get<Staff[]>('org/people/', { params: { is_active: true } }),
    api.get<Lookup[]>('finance/projects/'),
    api.get<Category[]>('finance/categories/'),
    api.get<Account[]>('finance/accounts/'),
  ])
  Object.assign(lookups, { staff: staff.data, projects: projects.data, categories: categories.data, accounts: accounts.data })
}
export const KINDS: CategoryKind[] = ['expense', 'payroll', 'tax', 'income', 'transfer']
export function categoriesByKind(list: Category[]) {
  return KINDS.map((k) => ({ kind: k, label: KIND_LABEL[k], items: list.filter((c) => c.kind === k && c.active) })).filter((g) => g.items.length)
}
