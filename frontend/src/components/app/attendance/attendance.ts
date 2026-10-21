// Types + helpers for the Attendance module (mirrors apps/attendance views/serializers).
import { isAxiosError } from "axios";

export type RecordStatus = "present" | "late" | "absent" | "on_leave";
export type WorkMode = "office" | "remote";
export type DayKind = "working" | "weekend" | "holiday";
/** Statuses the team/register views can derive on top of stored ones. */
export type CellStatus = RecordStatus | "weekend" | "holiday" | "not_checked_in";

export interface AttendanceRecord {
  id: number;
  user: number;
  user_name: string;
  date: string;
  check_in: string | null;
  check_out: string | null;
  status: RecordStatus;
  work_mode: WorkMode;
  note: string;
  check_in_ip: string | null;
  check_out_ip: string | null;
  worked_minutes: number | null;
  created_at: string;
  updated_at: string;
}

export interface Policy {
  work_start: string;
  work_end: string;
  late_grace_minutes: number;
  weekend_days: number[]; // python weekday, 0 = Mon
  late_after: string;
}

export interface TodayResponse {
  date: string;
  server_time: string;
  record: AttendanceRecord | null;
  policy: Policy;
  is_working_day: boolean;
  day_kind: DayKind;
  holiday_name: string | null;
  on_leave: boolean;
  leave: { id: number; leave_type: string; start_date: string; end_date: string; half_day: boolean } | null;
  can_check_in: boolean;
  can_check_out: boolean;
}

export interface MonthSummary {
  present: number;
  late: number;
  absent: number;
  on_leave: number;
  worked_minutes_total: number;
  working_days_in_month: number;
  working_days_elapsed: number;
  attendance_rate: number | null;
}

/** One server-derived day of /me/ (same status rules as a register cell). null = upcoming / before joining. */
export interface MeDay {
  date: string;
  kind: DayKind;
  holiday_name: string | null;
  status: CellStatus | null;
}

export interface MeResponse {
  month: string;
  start: string;
  end: string;
  days: MeDay[];
  records: AttendanceRecord[];
  summary: MonthSummary;
}

export interface StaffRef {
  id: number;
  full_name: string;
  email: string;
  department: { id: number; name: string } | null;
  designation: string;
  photo: string | null;
}

export interface TeamMember {
  user: StaffRef;
  status: CellStatus;
  record: Pick<AttendanceRecord, "id" | "check_in" | "check_out" | "work_mode" | "worked_minutes" | "note"> | null;
}

export interface TeamResponse {
  date: string;
  day_kind: DayKind;
  holiday_name: string | null;
  counts: Partial<Record<CellStatus, number>>;
  members: TeamMember[];
}

export interface RegisterDay {
  date: string;
  weekday: number; // 0 = Mon
  kind: DayKind;
  holiday_name: string | null;
}

export interface RegisterRow {
  user: StaffRef;
  cells: (CellStatus | null)[];
  totals: { present: number; late: number; absent: number; on_leave: number; worked_minutes: number };
}

export interface RegisterResponse {
  month: string;
  days: RegisterDay[];
  rows: RegisterRow[];
}

export interface Department {
  id: number;
  name: string;
}

/* ───────── Status legend: color + letter, so color is never the only signal ───────── */

export const STATUS_META: Record<CellStatus, { letter: string; label: string; cell: string }> = {
  present: { letter: "P", label: "Present", cell: "bg-moss/85 text-paper" },
  late: { letter: "L", label: "Late", cell: "bg-contour text-ink" },
  absent: { letter: "A", label: "Absent", cell: "bg-rust/85 text-paper" },
  on_leave: { letter: "LV", label: "On leave", cell: "bg-sky/85 text-paper" },
  holiday: { letter: "H", label: "Holiday", cell: "bg-sky/12 text-sky border border-dashed border-sky/40" },
  weekend: { letter: "W", label: "Weekend", cell: "bg-panel text-ink/45" },
  not_checked_in: { letter: "–", label: "Not checked in", cell: "border border-dashed border-ink/25 text-ink/45" },
};

export const LEGEND: CellStatus[] = ["present", "late", "absent", "on_leave", "holiday", "weekend", "not_checked_in"];

/* ───────── Time + date helpers (always Nepal time) ───────── */

const TZ = "Asia/Kathmandu";

export function todayNPT(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date());
}

export const thisMonth = () => todayNPT().slice(0, 7);

/** "HH:MM" in NPT, or an em dash. */
export function fmtTime(iso: string | null | undefined, seconds = false): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    ...(seconds ? { second: "2-digit" } : {}),
    hour12: false,
  }).format(new Date(iso));
}

/** 485 -> "8h 05m". */
export function fmtMinutes(min: number | null | undefined): string {
  if (min == null) return "—";
  const m = Math.max(0, Math.round(min));
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`;
}

/** Elapsed ms -> "HH:MM:SS". */
export function fmtElapsed(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(Math.floor(s / 3600))}:${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
}

function utc(isoDate: string): Date {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d ?? 1));
}

/** "2026-10-05" -> "Mon 05 Oct". */
export function fmtDay(isoDate: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", day: "2-digit", month: "short" }): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...opts }).format(utc(isoDate));
}

export const fmtMonth = (ym: string) => fmtDay(ym, { month: "long", year: "numeric" });

export function shiftMonth(ym: string, delta: number): string {
  const d = utc(ym);
  d.setUTCMonth(d.getUTCMonth() + delta);
  return d.toISOString().slice(0, 7);
}

export function shiftDate(iso: string, delta: number): string {
  const d = utc(iso);
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
}

/** All YYYY-MM-DD dates of a month. */
export function monthDates(ym: string): string[] {
  const d = utc(ym);
  const out: string[] = [];
  while (d.toISOString().slice(0, 7) === ym) {
    out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** Python weekday (0 = Mon) for a date. */
export const pyWeekday = (iso: string) => (utc(iso).getUTCDay() + 6) % 7;

/** Combine a local NPT date + "HH:MM" into an ISO string with the +05:45 offset. */
export const toISO = (date: string, hhmm: string) => (hhmm ? `${date}T${hhmm}:00+05:45` : null);

/** Best human message out of a DRF error. */
export function errMsg(e: unknown, fallback = "Something went wrong. Please try again."): string {
  if (isAxiosError(e)) {
    const data = e.response?.data as unknown;
    if (data && typeof data === "object") {
      const d = data as Record<string, unknown>;
      if (typeof d.detail === "string") return d.detail;
      const first = Object.entries(d)[0];
      if (first) {
        const v = Array.isArray(first[1]) ? first[1][0] : first[1];
        if (typeof v === "string") return first[0] === "non_field_errors" ? v : `${first[0].replace(/_/g, " ")}: ${v}`;
      }
    }
    if (!e.response) return "Can't reach the server. Check your connection.";
  }
  return fallback;
}

/** attendance/corrections/ — a request to fix a past day's times (HH:MM:SS, Nepal time). */
export interface Correction {
  id: number;
  user: number;
  user_name: string;
  date: string;
  check_in: string;
  check_out: string | null;
  reason: string;
  status: "pending" | "approved" | "rejected";
  approver: number | null;
  approver_name: string | null;
  decision_note: string;
  decided_at: string | null;
  created_at: string;
  can_decide: boolean;
}
