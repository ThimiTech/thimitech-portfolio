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
  notes: string
}
export interface Payslip extends PayAmounts {
  id: number
  employee: number
  employee_name: string
  period: string
  status: string
  notes: string
  payment_reference: string
  issued_at: string | null
  paid_at: string | null
}
export interface Expense {
  id: number
  employee: number
  employee_name: string
  description: string
  date: string
  category: string
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
