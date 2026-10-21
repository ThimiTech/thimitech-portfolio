import { isAxiosError } from "axios";

// ───────────── API payloads (/api/calendar/*) ─────────────

export type FeedKind = "holiday" | "event" | "leave" | "birthday" | "work_anniversary";
export type Audience = "organization" | "department" | "private";

export interface UserRef {
  id: number;
  full_name: string;
}

interface FeedBase {
  id: number;
  title: string;
  /** 'YYYY-MM-DD' for all kinds except event (ISO datetime, +05:45). */
  start: string;
  end: string;
  all_day: boolean;
  color: string;
}

export type FeedItem =
  | (FeedBase & { kind: "holiday"; meta: { is_optional: boolean; description: string } })
  | (FeedBase & {
      kind: "event";
      meta: {
        audience: Audience;
        location: string;
        description: string;
        department: { id: number; name: string } | null;
        created_by: UserRef | null;
        can_edit: boolean;
      };
    })
  | (FeedBase & {
      kind: "leave";
      meta: {
        user: UserRef;
        half_day: boolean;
        days: string;
        leave_type: { id: number; name: string; code: string; color: string };
      };
    })
  | (FeedBase & { kind: "birthday"; meta: { user: UserRef; month: number; day: number } })
  | (FeedBase & { kind: "work_anniversary"; meta: { user: UserRef; years: number; month: number; day: number } });

export interface Feed {
  start: string;
  end: string;
  /** Python weekday ints, Mon=0..Sun=6. */
  weekend_days: number[];
  items: FeedItem[];
}

export interface CalendarEvent {
  id: number;
  title: string;
  description: string;
  start: string;
  end: string;
  all_day: boolean;
  location: string;
  audience: Audience;
  department: number | null;
  department_name: string | null;
  attendees: number[];
  attendees_detail: UserRef[];
  created_by: UserRef | null;
  can_edit: boolean;
  created_at: string;
}

export interface Holiday {
  id: number;
  name: string;
  date: string;
  description: string;
  is_optional: boolean;
}

export interface BulkResult {
  created: Holiday[];
  skipped: { date: string; name: string; reason: string }[];
}

// ───────────── Presentation per kind (not colour-only: every chip carries a mono prefix) ─────────────

export const KIND: Record<FeedKind, { prefix: string; label: string; chip: string; dot: string }> = {
  holiday: { prefix: "HOL", label: "Holiday", chip: "border-rust/30 bg-rust/10 text-rust", dot: "bg-rust" },
  event: { prefix: "EVT", label: "Event", chip: "border-sky/30 bg-sky/10 text-sky", dot: "bg-sky" },
  leave: { prefix: "LV", label: "Leave", chip: "border-moss/30 bg-moss/10 text-moss", dot: "bg-moss" },
  birthday: { prefix: "BDAY", label: "Birthday", chip: "border-contour/40 bg-contour/15 text-contour-ink", dot: "bg-contour" },
  work_anniversary: { prefix: "ANNV", label: "Work anniversary", chip: "border-river/30 bg-river/10 text-river", dot: "bg-river" },
};

export const AUDIENCE_LABEL: Record<Audience, string> = {
  organization: "Whole organization",
  department: "Department",
  private: "Private",
};

export const itemKey = (i: FeedItem) => `${i.kind}-${i.id}`;

// ───────────── Dates — all "today" math is Nepal time; day arithmetic on UTC midnights ─────────────

export const TZ = "Asia/Kathmandu";

const ymdParts = new Intl.DateTimeFormat("en-US", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
const hmFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

/** Local Nepal date ('YYYY-MM-DD') of an instant. */
export function npDate(input: string | Date = new Date()): string {
  if (typeof input === "string" && input.length === 10) return input;
  const p = Object.fromEntries(ymdParts.formatToParts(new Date(input)).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}

/** Local Nepal 'HH:MM' of an ISO datetime. */
export const npTime = (iso: string) => hmFmt.format(new Date(iso));

export const todayNPT = () => npDate();

function toUTC(ymd: string): Date {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d!));
}

export function addDays(ymd: string, n: number): string {
  const d = toUTC(ymd);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** JS weekday, Sun=0..Sat=6. */
export const weekdayOf = (ymd: string) => toUTC(ymd).getUTCDay();

/** Backend weekend_days use Python weekday (Mon=0) — convert to JS (Sun=0). */
export const pyToJsWeekday = (py: number) => (py + 1) % 7;

export function fmtDate(ymd: string, opts: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...opts }).format(toUTC(ymd));
}

/** Sunday-first 6×7-or-less grid covering the given month (month is 0-based). */
export function monthGrid(year: number, month: number): string[] {
  const first = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10);
  const last = new Date(Date.UTC(year, month + 1, 0)).toISOString().slice(0, 10);
  const start = addDays(first, -weekdayOf(first));
  const end = addDays(last, 6 - weekdayOf(last));
  const days: string[] = [];
  for (let d = start; d <= end; d = addDays(d, 1)) days.push(d);
  return days;
}

/** Bucket feed items by every local day they cover, clipped to [from, to]. */
export function byDay(items: FeedItem[], from: string, to: string): Map<string, FeedItem[]> {
  const map = new Map<string, FeedItem[]>();
  for (const item of items) {
    let d = npDate(item.start);
    let end = npDate(item.end);
    if (end < d) end = d;
    if (d < from) d = from;
    if (end > to) end = to;
    for (; d <= end; d = addDays(d, 1)) {
      const list = map.get(d);
      if (list) list.push(item);
      else map.set(d, [item]);
    }
  }
  return map;
}

// ───────────── Errors ─────────────

export interface ApiError {
  detail: string;
  fields: Record<string, string>;
  /** Raw body, for endpoints with non-field shapes (e.g. bulk per-row errors). */
  data: unknown;
}

const flat = (v: unknown): string =>
  Array.isArray(v) ? v.map(flat).join(" ") : typeof v === "string" ? v : v && typeof v === "object" ? Object.values(v).map(flat).join(" ") : String(v);

export function parseError(e: unknown): ApiError {
  const out: ApiError = { detail: "", fields: {}, data: null };
  if (!isAxiosError(e)) return { ...out, detail: "Something went wrong." };
  const data = e.response?.data;
  out.data = data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    for (const [k, v] of Object.entries(data)) {
      if (k === "detail" || k === "non_field_errors") out.detail = flat(v);
      else out.fields[k] = flat(v);
    }
  }
  if (!out.detail && !Object.keys(out.fields).length) {
    const s = e.response?.status;
    out.detail = !s
      ? "Can't reach the server — check your connection."
      : s === 403
        ? "You don't have permission to do that."
        : `Request failed (${s}).`;
  }
  return out;
}
