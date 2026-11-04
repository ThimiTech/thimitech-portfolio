import { ref, computed } from "vue";
import axios from "axios";
import api from "../api/api";

export type Role = "guest" | "employee" | "accountant" | "manager" | "hr_admin" | "super_admin";
/** A role, or "finance": HR/admin and above, or the accountant role (books, payroll, finance drive). */
export type Access = Role | "finance";

// Ascending privilege — mirrors backend User.RANK.
export const ROLE_RANK: Record<Role, number> = {
  guest: 0,
  employee: 1,
  accountant: 1, // staff-level elsewhere; finance access via hasRole("finance")
  manager: 2,
  hr_admin: 3,
  super_admin: 4,
};

export const ROLE_LABEL: Record<Role, string> = {
  guest: "Guest",
  employee: "Employee",
  accountant: "Accountant / CA",
  manager: "Manager",
  hr_admin: "HR / Admin",
  super_admin: "Super admin",
};

/** Security clearance (users) and classification (documents, notes, drive files…) — mirrors backend Clearance.
 *  You see an item only when your clearance is at least its level. */
export type Level = 1 | 2 | 3 | 4;
export const LEVEL_LABEL: Record<Level, string> = { 1: "Internal", 2: "Confidential", 3: "Restricted", 4: "Secret" };
export const LEVEL_HINT: Record<Level, string> = {
  1: "Everyone who can already open it",
  2: "Leads and above, e.g. estimates, client correspondence",
  3: "Contracts, agreements, HR and finance papers",
  4: "Owner and directors only",
};

export interface Me {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  clearance: Level;
  is_staff: boolean;
  department: { id: number; name: string } | null;
  designation: string;
  photo: string | null;
  theme: "system" | "light" | "dark";
}

const accessToken = ref<string | null>(localStorage.getItem("access_token"));
const userEmail = ref<string | null>(localStorage.getItem("user_email"));
const user = ref<Me | null>(null);
const loginOpen = ref(false);

export function useAuth() {
  const isLoggedIn = computed(() => !!accessToken.value);

  function setSession(access: string, refresh: string, email: string) {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    localStorage.setItem("user_email", email);
    accessToken.value = access;
    userEmail.value = email;
  }

  /** After a refresh; the server rotates refresh tokens, so store the new one when present. */
  function setAccess(access: string, refresh?: string) {
    localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
    accessToken.value = access;
  }

  function logout() {
    // Revoke the refresh token server-side (best effort; the local session ends regardless).
    const refresh = localStorage.getItem("refresh_token");
    if (refresh) axios.post("/api/token/blacklist/", { refresh }).catch(() => {});
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_email");
    accessToken.value = null;
    userEmail.value = null;
    user.value = null;
  }

  async function fetchMe(): Promise<Me | null> {
    if (!accessToken.value) return null;
    try {
      const { data } = await api.get<Me>("me/");
      user.value = data;
    } catch {
      user.value = null;
    }
    return user.value;
  }

  /** True when the loaded user's role is at least `min` ("finance": HR/admin+ or accountant). */
  function hasRole(min: Access): boolean {
    if (!user.value) return false;
    if (min === "finance") return user.value.role === "accountant" || ROLE_RANK[user.value.role] >= ROLE_RANK.hr_admin;
    return ROLE_RANK[user.value.role] >= ROLE_RANK[min];
  }

  function openLogin() {
    loginOpen.value = true;
  }

  function closeLogin() {
    loginOpen.value = false;
  }

  return {
    accessToken,
    userEmail,
    user,
    isLoggedIn,
    loginOpen,
    setSession,
    setAccess,
    logout,
    fetchMe,
    hasRole,
    openLogin,
    closeLogin,
  };
}
