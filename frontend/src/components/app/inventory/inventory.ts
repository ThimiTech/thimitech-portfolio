export interface Category {
  id: number
  name: string
  description: string
}
export interface Asset {
  id: number
  tag: string
  name: string
  category: number
  category_name: string
  serial_number: string
  location: string
  purchase_date: string | null
  purchase_cost: string | null
  currency: string
  status: string
  notes: string
  assigned_to: { assignment: number; id: number; name: string; due_back: string | null } | null
}
export interface Assignment {
  id: number
  asset: number
  asset_name: string
  asset_tag: string
  employee: number
  employee_name: string
  assigned_at: string
  due_back: string | null
  notes: string
  returned_at: string | null
  return_note: string
  return_condition: string
}
export interface InventorySummary {
  total: number
  available: number
  assigned: number
  maintenance: number
  retired: number
  overdue: number
}
export function timestamp(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    timeZone: 'Asia/Kathmandu',
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}
/** GET inventory/my-assets/ — the signed-in employee's assignments, current first. */
export interface MyAssignment {
  id: number
  asset_name: string
  asset_tag: string
  category: string
  serial_number: string
  assigned_at: string
  due_back: string | null
  notes: string
  returned_at: string | null
  return_condition: string
}
