import type { Access } from "@/stores/auth";

export interface NavItem {
  label: string;
  to: string;
  icon: keyof typeof ICONS;
  minRole?: Access;
  /** Extra words the command palette matches on. */
  keywords?: string;
}
export interface NavGroup {
  title: string;
  items: NavItem[];
}

// Lucide-style stroke icons (24×24 path data)
export const ICONS = {
  dashboard: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  attendance: "M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  leave: "M2 22 16 8M3.5 13.5C2 9 5 3 12 2c-1 7-7 10-8.5 11.5zM12 2c4 1 7 4 8 8-3 0-6-1-8-3",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  notices: "M3 11l18-8v18L3 13zM11.6 16.8a3 3 0 1 1-5.8-1.6",
  projects: "M9 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h5zM15 3h-3v11h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1zM21 3h-2v7h2z",
  people: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  organization: "M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  profile: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  finance: "M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
  inventory: "M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  monitoring: "M22 12h-4l-3 9L9 3l-3 9H2",
  audit: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4",
  hiring: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM19 8v6M22 11h-6",
  inquiries: "M22 12h-6l-2 3h-4l-2-3H2M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z",
  drive: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
} as const;

// Four groups. Personal pages (profile, pay, assets) live under the account menu, not here.
export const NAV: NavGroup[] = [
  {
    title: "",
    items: [{ label: "Dashboard", to: "/app", icon: "dashboard", keywords: "home overview" }],
  },
  {
    title: "Work",
    items: [
      { label: "Attendance", to: "/app/attendance", icon: "attendance", keywords: "check in punch clock" },
      { label: "Leave", to: "/app/leave", icon: "leave", keywords: "time off holiday request approvals" },
      { label: "Calendar", to: "/app/calendar", icon: "calendar", keywords: "events holidays schedule" },
      { label: "Projects", to: "/app/projects", icon: "projects", keywords: "tasks board jira kanban" },
    ],
  },
  {
    title: "Company",
    items: [
      { label: "Notice board", to: "/app/notices", icon: "notices", keywords: "announcements news" },
      { label: "Drive", to: "/app/drive", icon: "drive", keywords: "documents files folders letterhead logo stamp templates share" },
      { label: "People", to: "/app/people", icon: "people", keywords: "directory staff employees" },
      { label: "Organization", to: "/app/organization", icon: "organization", keywords: "departments structure chart" },
    ],
  },
  {
    title: "Admin",
    items: [
      { label: "Hiring", to: "/app/hiring", icon: "hiring", minRole: "hr_admin", keywords: "jobs applicants recruitment candidates cv onboarding postings" },
      { label: "Inquiries", to: "/app/inquiries", icon: "inquiries", minRole: "manager", keywords: "contact leads messages clients inbox" },
      { label: "Finance", to: "/app/finance", icon: "finance", minRole: "finance", keywords: "bank ledger statement salary payroll payslips ssf tds claims expenses invoices reports audit export ca" },
      { label: "Inventory", to: "/app/inventory", icon: "inventory", minRole: "hr_admin", keywords: "assets equipment" },
      { label: "Monitoring", to: "/app/monitoring", icon: "monitoring", minRole: "super_admin", keywords: "metrics trends health" },
      { label: "Audit trail", to: "/app/audit", icon: "audit", minRole: "super_admin", keywords: "log events history" },
    ],
  },
];

/** Personal pages: tabs of the "Me" area and entries in the account menu and command palette. */
export const ME: NavItem[] = [
  { label: "My profile", to: "/app/profile", icon: "profile", keywords: "account me settings onboarding" },
  { label: "My pay", to: "/app/my-pay", icon: "finance", keywords: "payslip salary payroll me print claims reimbursement ssf tds" },
  { label: "My assets", to: "/app/my-assets", icon: "inventory", keywords: "equipment laptop report issue me" },
];

/** Groups/items visible to a user, given a role check. */
export function navFor(hasRole: (r: Access) => boolean): NavGroup[] {
  return NAV.map((g) => ({ ...g, items: g.items.filter((i) => !i.minRole || hasRole(i.minRole)) })).filter((g) => g.items.length);
}

/** Deepest nav item whose path prefixes `path` ("/app" only matches exactly). */
export function activeItem(path: string): { group: NavGroup; item: NavItem } | null {
  for (const group of NAV)
    for (const item of group.items)
      if (item.to === "/app" ? path === "/app" || path === "/app/" : path === item.to || path.startsWith(item.to + "/")) return { group, item };
  return null;
}
