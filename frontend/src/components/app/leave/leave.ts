// Types + small helpers for the Leave module (mirrors apps/leave serializers).
import { isAxiosError } from "axios";
import api from "@/api/api";
import { confirmDialog } from "../ui/confirm";

export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface LeaveType {
  id: number;
  name: string;
  code: string;
  annual_quota: number;
  is_paid: boolean;
  color: string;
  is_active: boolean;
}

export type LeaveTypeRef = Pick<LeaveType, "id" | "name" | "code" | "color" | "is_paid">;

export interface PersonRef {
  id: number;
  full_name: string;
  email?: string;
}

export interface Balance {
  leave_type: LeaveTypeRef;
  quota: number;
  used: number;
  pending: number;
  /** quota - used; null when the type has no fixed quota. */
  remaining: number | null;
}

export interface BalancesResponse {
  year: number;
  user: PersonRef;
  balances: Balance[];
}

export interface LeaveRequest {
  id: number;
  user: PersonRef;
  leave_type: LeaveTypeRef;
  start_date: string;
  end_date: string;
  half_day: boolean;
  days: number;
  reason: string;
  status: LeaveStatus;
  approver: PersonRef | null;
  decision_note: string;
  decided_at: string | null;
  created_at: string;
  designated_approver: PersonRef | null;
  can_decide: boolean;
  can_cancel: boolean;
}

export interface Holiday {
  id: number;
  name: string;
  date: string;
  is_optional: boolean;
}

export const STATUSES: LeaveStatus[] = ["pending", "approved", "rejected", "cancelled"];

const TZ = "Asia/Kathmandu";

/** Today's date in Nepal time as YYYY-MM-DD. */
export function todayNPT(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date());
}

export const currentYear = () => Number(todayNPT().slice(0, 4));

function toUTC(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d!));
}

const dayFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", timeZone: "UTC" });
const dayYearFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
const stampFmt = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: TZ,
});

export const fmtDay = (iso: string) => dayYearFmt.format(toUTC(iso));
export const fmtStamp = (iso: string) => stampFmt.format(new Date(iso));

/** "25 Oct → 27 Oct 2026", or a single date. */
export function fmtRange(start: string, end: string): string {
  if (start === end) return fmtDay(start);
  const sameYear = start.slice(0, 4) === end.slice(0, 4);
  return `${sameYear ? dayFmt.format(toUTC(start)) : fmtDay(start)} → ${fmtDay(end)}`;
}

/** 3 -> "3", 0.5 -> "0.5", 1.25 -> "1.25" */
export const fmtDays = (n: number) => String(Math.round(n * 100) / 100);

export const plural = (n: number, word: string) => `${fmtDays(n)} ${word}${n === 1 ? "" : "s"}`;

/**
 * Approximate working days in [start, end] — mirrors calendar_app.utils.working_days.
 * weekendDays are Python weekday ints (Mon=0 … Sun=6). The server's count is authoritative.
 */
export function countWorkingDays(start: string, end: string, weekendDays: number[], holidays: Set<string>): number {
  const a = toUTC(start);
  const b = toUTC(end);
  let n = 0;
  for (let d = a; d <= b; d = new Date(d.getTime() + 86_400_000)) {
    const py = (d.getUTCDay() + 6) % 7;
    if (!weekendDays.includes(py) && !holidays.has(d.toISOString().slice(0, 10))) n++;
  }
  return n;
}

/** Field errors from a DRF 400 response, keyed by field ("non_field_errors" / "detail" included). */
export function fieldErrors(err: unknown): Record<string, string> {
  if (!isAxiosError(err) || !err.response?.data || typeof err.response.data !== "object") return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(err.response.data as Record<string, unknown>)) {
    out[k] = Array.isArray(v) ? v.join(" ") : String(v);
  }
  return out;
}

/** One human sentence for any request failure. */
export function errorMessage(err: unknown, fallback = "Something went wrong. Please try again."): string {
  if (isAxiosError(err) && !err.response) return "Can't reach the server. Check your connection and try again.";
  const fe = fieldErrors(err);
  return fe.detail || fe.non_field_errors || Object.values(fe)[0] || fallback;
}

/** Cancel after an in-app confirm. Returns the updated request, or null if the user backed out. */
export async function cancelRequest(r: LeaveRequest, mine: boolean): Promise<LeaveRequest | null> {
  const what = `${r.leave_type.name} leave (${fmtRange(r.start_date, r.end_date)})`;
  if (!(await confirmDialog({ title: "Cancel leave", body: mine ? `Cancel your ${what}?` : `Cancel ${r.user.full_name}'s ${what}?`, confirmLabel: "Cancel leave" }))) return null;
  const { data } = await api.post<LeaveRequest>(`leave/requests/${r.id}/cancel/`);
  return data;
}
