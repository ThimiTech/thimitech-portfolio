// Types + tiny helpers for the notice board (mirrors apps/notices serializers).
import api from "@/api/api";

export type Category = "general" | "hr" | "policy" | "event" | "urgent";
export type Audience = "all" | "department";
export type NoticeStatus = "published" | "scheduled" | "expired";

export interface DeptRef {
  id: number;
  name: string;
}

export interface PersonRef {
  id: number;
  full_name: string;
  photo: string | null;
}

export interface Notice {
  id: number;
  title: string;
  body: string;
  category: Category;
  audience: Audience;
  department: DeptRef | null;
  pinned: boolean;
  publish_at: string;
  expires_at: string | null;
  /** Authenticated API URL (/api/notices/{id}/attachment/), never a public /media path. */
  attachment: string | null;
  attachment_name: string | null;
  author: PersonRef | null;
  status: NoticeStatus;
  is_read: boolean;
  read_count: number | null;
  can_edit: boolean;
  created_at: string;
  updated_at: string;
}

export interface Reader extends PersonRef {
  department: DeptRef | null;
  read_at: string | null;
}

export interface ReadersResponse {
  audience_count: number;
  read_count: number;
  read: Reader[];
  unread: Reader[];
}

/** Subset of GET /api/org/departments/ that the composer needs. */
export interface Department extends DeptRef {
  manager: { id: number; full_name: string } | null;
}

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "general", label: "General" },
  { value: "hr", label: "HR" },
  { value: "policy", label: "Policy" },
  { value: "event", label: "Event" },
  { value: "urgent", label: "Urgent" },
];

export const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label])) as Record<Category, string>;

export const ATTACHMENT_ACCEPT = ".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.xlsx";
export const ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024;

const TZ = "Asia/Kathmandu";

const absFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ,
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** "17 Oct 2026 · 10:59" in NPT, whatever the browser's zone. */
export function fmtAbs(iso: string): string {
  const p = Object.fromEntries(absFmt.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.day} ${p.month} ${p.year} · ${p.hour}:${p.minute}`;
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31536000],
  ["month", 2592000],
  ["week", 604800],
  ["day", 86400],
  ["hour", 3600],
  ["minute", 60],
];

/** "3 hours ago" / "in 2 days" / "just now". */
export function fmtRel(iso: string, now = Date.now()): string {
  const secs = (new Date(iso).getTime() - now) / 1000;
  for (const [unit, size] of STEPS) {
    if (Math.abs(secs) >= size) return rtf.format(Math.round(secs / size), unit);
  }
  return "just now";
}

const inputFmt = new Intl.DateTimeFormat("en-CA", {
  timeZone: TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** ISO -> "YYYY-MM-DDTHH:mm" NPT wall time for <input type="datetime-local">. */
export function toNptInput(iso: string | null): string {
  if (!iso) return "";
  const p = Object.fromEntries(inputFmt.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

/** datetime-local value (read as NPT wall time) -> ISO with +05:45. */
export function fromNptInput(v: string): string {
  return `${v}:00+05:45`;
}

/** Flatten a DRF error payload into {field: message}. */
export function drfErrors(data: unknown): Record<string, string> {
  if (!data || typeof data !== "object") return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
    out[k] = Array.isArray(v) ? v.join(" ") : String(v);
  }
  return out;
}

/**
 * The attachment endpoint needs the JWT header, so a plain <a href> would 401.
 * Fetch it as a blob and hand the browser a download (not blocked like window.open after await).
 */
export async function downloadAttachment(n: Pick<Notice, "id" | "attachment_name">): Promise<void> {
  const { data } = await api.get<Blob>(`notices/${n.id}/attachment/`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = url;
  a.download = n.attachment_name ?? "attachment";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Is the viewer in this notice's audience? (manage mode also lists notices addressed to others). */
export function inAudience(n: Pick<Notice, "audience" | "department">, deptId: number | null | undefined): boolean {
  return n.audience === "all" || (!!deptId && n.department?.id === deptId);
}

/** Shape of an axios error, as far as the notice views read it. */
export type HttpError = { response?: { status?: number; data?: { detail?: string } & Record<string, unknown> } } | undefined;
