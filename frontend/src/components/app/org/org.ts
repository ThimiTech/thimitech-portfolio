// Types + helpers for the Org & staff profiles module (mirrors apps/org serializers).
import axios from "axios";
import type { RouteLocationRaw } from "vue-router";
import { ROLE_LABEL, ROLE_RANK, type Role } from "@/stores/auth";

export interface Ref {
  id: number;
  name: string;
}

export interface PersonBrief {
  id: number;
  full_name: string;
}

export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";

/** GET /api/org/people/. Sensitive keys are absent (not null) on the directory view. */
export interface Person {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  department: Ref | null;
  manager: PersonBrief | null;
  designation: string;
  join_date: string | null;
  phone: string;
  photo: string | null;
  bio: string;
  skills: string[];
  visibility: "full" | "directory";
  employee_code?: string;
  employment_type?: EmploymentType;
  date_of_birth?: string | null;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
}

export interface Department {
  id: number;
  name: string;
  description: string;
  parent: number | null;
  manager: PersonBrief | null;
  member_count: number;
  created_at: string;
}

export interface Member {
  id: number;
  full_name: string;
  designation: string;
  photo: string | null;
  role: Role;
}

export interface StructureNode {
  id: number;
  name: string;
  description: string;
  parent: number | null;
  manager: Member | null;
  members: Member[];
  children: StructureNode[];
}

export interface Structure {
  departments: StructureNode[];
  unassigned: Member[];
}

export interface Organization {
  name: string;
  tagline: string;
  about: string;
  logo: string | null;
  email: string;
  phone: string;
  address: string;
  website: string;
  github: string;
  linkedin: string;
  youtube: string;
  founded: string | null;
  work_start: string;
  work_end: string;
  late_grace_minutes: number;
  weekend_days: number[];
  updated_at: string;
}

export const ROLES: Role[] = ["guest", "employee", "manager", "hr_admin", "super_admin"];
export { ROLE_LABEL };

export const EMPLOYMENT_LABEL: Record<EmploymentType, string> = {
  full_time: "Full time",
  part_time: "Part time",
  contract: "Contract",
  intern: "Intern",
};

/** Python weekday order: 0 = Monday … 6 = Sunday. */
export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const WEEKDAYS_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// ---------------------------------------------------------------- role rules (mirror backend)

const rank = (r: Role) => ROLE_RANK[r];

/** Roles `actor` may assign to someone else. */
export function grantableRoles(actor: Role): Role[] {
  if (actor === "super_admin") return ROLES;
  if (actor === "hr_admin") return ["guest", "employee", "manager"];
  return [];
}

/** HR-level management of `target` (edit all fields, deactivate). Self is handled separately. */
export function canManage(actor: { id: number; role: Role } | null, target: { id: number; role: Role }): boolean {
  if (!actor || rank(actor.role) < rank("hr_admin")) return false;
  if (actor.id === target.id) return true;
  return actor.role === "super_admin" || rank(target.role) < rank("hr_admin");
}

// ---------------------------------------------------------------- errors

export interface ApiError {
  message: string;
  fields: Record<string, string>;
}

/** Normalise a DRF error ({detail} for 403, {field: [msg]} for 400) for display. */
export function apiError(e: unknown, fallback = "Something went wrong. Check your connection and try again."): ApiError {
  const fields: Record<string, string> = {};
  if (!axios.isAxiosError(e) || !e.response) return { message: fallback, fields };
  const data = e.response.data as unknown;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
      const msg = Array.isArray(v) ? v.map(String).join(" ") : typeof v === "string" ? v : "";
      if (msg) fields[k] = msg;
    }
  }
  const message =
    fields.detail ?? fields.non_field_errors ?? (Object.keys(fields).length ? "Please fix the highlighted fields." : fallback);
  delete fields.detail;
  delete fields.non_field_errors;
  return { message, fields };
}

// ---------------------------------------------------------------- formatting

/** 'YYYY-MM-DD' -> '15 Aug 2021' without timezone drift. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(y, m - 1, d));
}

/** Tenure like '3y 2m' from a join date. */
export function tenure(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m] = iso.split("-").map(Number);
  if (!y || !m) return "";
  const now = new Date();
  const months = (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - m);
  if (months < 1) return "new";
  const yy = Math.floor(months / 12);
  const mm = months % 12;
  return [yy ? `${yy}y` : "", mm ? `${mm}m` : ""].filter(Boolean).join(" ");
}

/** 'HH:MM:SS' -> 'HH:MM'. */
export const hhmm = (t: string | null | undefined) => (t ? t.slice(0, 5) : "—");

/** Only the keys whose value differs from `orig` (shallow; arrays compared by JSON). */
export function diff<T extends Record<string, unknown>>(next: T, orig: Partial<Record<keyof T, unknown>>): Partial<T> {
  const out: Partial<T> = {};
  for (const k of Object.keys(next) as (keyof T)[]) {
    const a = next[k];
    const b = orig[k] ?? (Array.isArray(a) ? [] : typeof a === "string" ? "" : null);
    if (JSON.stringify(a) !== JSON.stringify(b)) out[k] = a;
  }
  return out;
}

export const MAX_IMAGE_BYTES = 3 * 1024 * 1024;

/** One label/value line in an InfoPanel. */
export interface InfoRow {
  label: string;
  value: string | null | undefined;
  href?: string;
  to?: RouteLocationRaw;
  mono?: boolean;
  note?: string;
}
