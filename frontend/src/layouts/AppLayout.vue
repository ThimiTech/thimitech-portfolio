<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { useAuth, ROLE_LABEL } from "../stores/auth";
import Avatar from "../components/app/ui/Avatar.vue";
import ConfirmHost from "../components/app/ui/ConfirmHost.vue";
import ToastHost from "../components/app/ui/ToastHost.vue";
import CommandPalette, { type Command } from "../components/app/ui/CommandPalette.vue";
import NotificationBell from "../components/app/ui/NotificationBell.vue";
import PasswordModal from "../components/app/org/PasswordModal.vue";
import { confirmState } from "../components/app/ui/confirm";
import { toast } from "../components/app/ui/toast";
import { useTheme } from "../components/app/ui/theme";
import { ICONS, activeItem, navFor } from "../components/app/nav";
import api from "../api/api";

const { user, logout, hasRole } = useAuth();
const route = useRoute();
const router = useRouter();
const { isDark, mode: themeMode, setMode, toggle } = useTheme();

// ── Theme: the user's saved preference wins (synced across devices); toggling saves it ──
watch(
  () => user.value?.theme,
  (t) => t && t !== themeMode.value && setMode(t),
  { immediate: true },
);
function toggleTheme() {
  toggle();
  if (user.value) user.value.theme = themeMode.value;
  api.patch("me/", { theme: themeMode.value }).catch(() => {}); // still applied locally if this fails
}

const groups = computed(() => navFor(hasRole));
const current = computed(() => activeItem(route.path));
const isActive = (to: string) => current.value?.item.to === to;

// ── Theme: scoped to the workspace so the public site never inherits it ──
watch(isDark, (d) => document.documentElement.classList.toggle("app-dark", d), { immediate: true });
onBeforeUnmount(() => document.documentElement.classList.remove("app-dark"));

// ── Sidebar: collapsible on desktop (remembered), drawer on mobile ──
const COLLAPSE_KEY = "thimi.sidebar.collapsed";
const collapsed = ref(false);
try {
  collapsed.value = localStorage.getItem(COLLAPSE_KEY) === "1";
} catch {
  /* storage blocked */
}
function toggleCollapsed() {
  collapsed.value = !collapsed.value;
  try {
    localStorage.setItem(COLLAPSE_KEY, collapsed.value ? "1" : "0");
  } catch {
    /* storage blocked */
  }
}
const drawer = ref(false);
const sidebar = ref<HTMLElement | null>(null);
watch(drawer, async (open) => {
  if (!open) return;
  await nextTick();
  sidebar.value?.querySelector<HTMLElement>("a[aria-current='page'], nav a")?.focus();
});

// ── Badges: one nav-counts call, on every route change and every minute while the tab is visible ──
interface NavCounts { leave_approvals: number; unread_notices: number; overdue_tasks: number; unread_notifications: number; attendance_corrections: number }
const badges = ref<Record<string, number>>({});
const unreadNotifications = ref(0);
const BADGE_LABEL: Record<string, string> = {
  "/app/leave": "leave requests to decide",
  "/app/notices": "unread notices",
  "/app/projects": "overdue tasks",
  "/app/attendance": "attendance corrections to decide",
};
async function refreshBadges() {
  try {
    const { data } = await api.get<NavCounts>("nav-counts/");
    badges.value = {
      "/app/leave": data.leave_approvals,
      "/app/notices": data.unread_notices,
      "/app/projects": data.overdue_tasks,
      "/app/attendance": data.attendance_corrections,
    };
    unreadNotifications.value = data.unread_notifications;
  } catch {
    /* keep the last known counts */
  }
}
const POLL_MS = 60_000;
let poll: number | undefined;
const pollIfVisible = () => document.visibilityState === "visible" && refreshBadges();

// ── Route changes: close overlays, refresh badges, move focus for screen readers ──
const main = ref<HTMLElement | null>(null);
const menuOpen = ref(false); // declared before the immediate watcher below, which writes it
let firstRoute = true;
watch(
  () => route.path,
  async () => {
    drawer.value = false;
    menuOpen.value = false;
    refreshBadges();
    if (firstRoute) return void (firstRoute = false);
    await nextTick();
    main.value?.focus({ preventScroll: true });
  },
  { immediate: true },
);

// ── Live Nepal clock ──
const now = ref(new Date());
let timer: number | undefined;
const tz = "Asia/Kathmandu";
const clock = computed(() =>
  new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hour12: false }).format(now.value),
);
const today = computed(() =>
  new Intl.DateTimeFormat("en-GB", { timeZone: tz, weekday: "short", day: "2-digit", month: "short" }).format(now.value),
);

// ── User menu ──
const menuRoot = ref<HTMLElement | null>(null);
const pwOpen = ref(false);
async function openMenu() {
  menuOpen.value = !menuOpen.value;
  if (!menuOpen.value) return;
  await nextTick();
  menuRoot.value?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
}
function onMenuKey(e: KeyboardEvent) {
  const items = [...(menuRoot.value?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? [])];
  const i = items.indexOf(document.activeElement as HTMLElement);
  if (e.key === "Escape") {
    menuOpen.value = false;
    menuRoot.value?.querySelector<HTMLElement>("[aria-haspopup]")?.focus();
  } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    items[(i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length]?.focus();
  }
}
function onDocClick(e: MouseEvent) {
  if (menuOpen.value && !menuRoot.value?.contains(e.target as Node)) menuOpen.value = false;
}
function changePassword() {
  menuOpen.value = false;
  pwOpen.value = true;
}
let signingOut = false;
function signOut() {
  signingOut = true;
  logout();
  router.push({ name: "login" });
}
// Session ended elsewhere (refresh token expired → api.ts logs out): back to sign-in, then here.
watch(user, (u) => {
  if (!u && !signingOut) router.push({ name: "login", query: { next: route.fullPath } });
});

// ── Command palette (Ctrl/Cmd+K) ──
const paletteOpen = ref(false);
const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
const commands = computed<Command[]>(() => [
  ...groups.value.flatMap((g) =>
    g.items.map((i) => ({ id: i.to, label: i.label, group: g.title, icon: ICONS[i.icon], keywords: i.keywords, to: i.to })),
  ),
  { id: "act-leave", label: "Apply for leave", group: "Action", icon: ICONS.leave, keywords: "request time off", to: "/app/leave?apply=1" },
  { id: "act-correction", label: "Request attendance correction", group: "Action", icon: ICONS.attendance, keywords: "missed punch fix check in out", to: "/app/attendance?tab=corrections&new=1" },
  { id: "act-theme", label: isDark.value ? "Switch to light mode" : "Switch to dark mode", group: "Action", keywords: "theme dark light appearance", run: toggleTheme },
  { id: "act-pw", label: "Change password", group: "Action", keywords: "security account", run: () => (pwOpen.value = true) },
  { id: "act-out", label: "Sign out", group: "Action", keywords: "logout log out", run: signOut },
]);
function runCommand(c: Command) {
  paletteOpen.value = false;
  if (c.to) router.push(c.to);
  else c.run?.();
}
function onGlobalKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    paletteOpen.value = !paletteOpen.value;
  } else if (e.key === "Escape" && drawer.value) drawer.value = false;
}

onMounted(() => {
  timer = window.setInterval(() => (now.value = new Date()), 15_000);
  poll = window.setInterval(pollIfVisible, POLL_MS);
  document.addEventListener("visibilitychange", pollIfVisible);
  document.addEventListener("keydown", onGlobalKey);
  document.addEventListener("click", onDocClick);
});
onBeforeUnmount(() => {
  clearInterval(timer);
  clearInterval(poll);
  document.removeEventListener("visibilitychange", pollIfVisible);
  document.removeEventListener("keydown", onGlobalKey);
  document.removeEventListener("click", onDocClick);
});
</script>

<template>
  <div class="min-h-dvh bg-paper font-body text-ink">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[10002] focus:rounded-md focus:bg-flag focus:px-3 focus:py-2 focus:text-sm focus:text-on-accent">
      Skip to content
    </a>

    <!-- Mobile overlay -->
    <div v-if="drawer" class="fixed inset-0 z-40 bg-scrim/50 backdrop-blur-[2px] lg:hidden" aria-hidden="true" @click="drawer = false" />

    <!-- Sidebar -->
    <aside
      id="app-sidebar"
      ref="sidebar"
      class="keep-ink contour-bg fixed inset-y-0 left-0 z-50 flex w-[252px] flex-col bg-ink text-paper transition-[transform,width] duration-200 motion-reduce:transition-none lg:translate-x-0"
      :class="[drawer ? 'translate-x-0' : '-translate-x-full', collapsed ? 'lg:w-[72px]' : '']"
      aria-label="Workspace navigation"
    >
      <!-- Brand -->
      <div class="flex items-center gap-2 px-4 pt-5 pb-4" :class="collapsed ? 'lg:justify-center lg:px-0' : ''">
        <RouterLink to="/app" class="flex min-w-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/60" aria-label="Thimitech OS — dashboard">
          <svg viewBox="0 0 24 24" class="h-6 w-6 shrink-0 text-flag" aria-hidden="true">
            <path fill="currentColor" d="M12 2C8 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3-7-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5Z" />
          </svg>
          <span :class="collapsed ? 'lg:hidden' : ''" class="font-display text-[19px] font-semibold tracking-tight">Thimitech</span>
          <span :class="collapsed ? 'lg:hidden' : ''" class="rounded border border-paper/20 px-1.5 py-px font-mono text-[9.5px] tracking-[0.18em] text-paper/60">OS</span>
        </RouterLink>
        <button type="button" class="ml-auto rounded-md p-1.5 text-paper/60 hover:bg-paper/10 hover:text-paper lg:hidden" aria-label="Close navigation" @click="drawer = false">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>

      <div class="mx-4 border-t border-dashed border-paper/15" />

      <!-- Nav -->
      <nav class="flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
        <div v-for="g in groups" :key="g.title" class="mb-5">
          <p class="mb-2 px-2 font-mono text-[10px] tracking-[0.18em] text-paper/40 uppercase" :class="collapsed ? 'lg:sr-only' : ''">{{ g.title }}</p>
          <ul class="grid gap-0.5">
            <li v-for="item in g.items" :key="item.to">
              <RouterLink
                :to="item.to"
                class="group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-[13.5px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/60"
                :class="[
                  isActive(item.to) ? 'bg-paper/[0.08] text-paper' : 'text-paper/65 hover:bg-paper/[0.05] hover:text-paper',
                  collapsed ? 'lg:justify-center lg:px-0' : '',
                ]"
                :aria-current="isActive(item.to) ? 'page' : undefined"
                :title="collapsed ? item.label : undefined"
              >
                <span v-if="isActive(item.to)" class="absolute top-1/2 -left-3 h-5 w-[3px] -translate-y-1/2 rounded-r bg-flag" aria-hidden="true" />
                <svg
                  viewBox="0 0 24 24"
                  class="h-[18px] w-[18px] shrink-0"
                  :class="isActive(item.to) ? 'text-flag' : 'text-paper/50 group-hover:text-paper/85'"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path :d="ICONS[item.icon]" />
                </svg>
                <span class="flex-1 truncate" :class="collapsed ? 'lg:sr-only' : ''">{{ item.label }}</span>
                <span
                  v-if="badges[item.to]"
                  class="readout min-w-[1.25rem] rounded-full bg-flag px-1.5 py-px text-center text-[10px] font-medium text-on-accent"
                  :class="collapsed ? 'lg:absolute lg:top-0.5 lg:right-1 lg:min-w-0 lg:px-1' : ''"
                  :aria-label="`${badges[item.to]} ${BADGE_LABEL[item.to]}`"
                >{{ badges[item.to]! > 99 ? "99+" : badges[item.to] }}</span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </nav>

      <div class="border-t border-dashed border-paper/15 p-3">
        <button
          type="button"
          class="hidden w-full items-center gap-3 rounded-lg px-2.5 py-2 text-[12.5px] text-paper/55 hover:bg-paper/[0.05] hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/60 lg:flex"
          :class="collapsed ? 'justify-center px-0' : ''"
          :aria-expanded="!collapsed"
          aria-controls="app-sidebar"
          :title="collapsed ? 'Expand sidebar' : undefined"
          @click="toggleCollapsed"
        >
          <svg viewBox="0 0 24 24" class="h-[18px] w-[18px] shrink-0 transition-transform" :class="collapsed ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 3v18M16 15l-3-3 3-3" />
          </svg>
          <span :class="collapsed ? 'sr-only' : ''">{{ collapsed ? "Expand sidebar" : "Collapse sidebar" }}</span>
        </button>
        <RouterLink
          to="/"
          class="flex items-center gap-3 rounded-lg px-2.5 py-2 text-[12.5px] text-paper/55 hover:bg-paper/[0.05] hover:text-paper focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/60"
          :class="collapsed ? 'lg:justify-center lg:px-0' : ''"
          :title="collapsed ? 'Public website' : undefined"
        >
          <svg viewBox="0 0 24 24" class="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" />
          </svg>
          <span :class="collapsed ? 'lg:sr-only' : ''">Public website</span>
        </RouterLink>
      </div>
    </aside>

    <!-- Main column -->
    <div class="transition-[padding] duration-200 motion-reduce:transition-none" :class="collapsed ? 'lg:pl-[72px]' : 'lg:pl-[252px]'">
      <header class="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-ink/10 bg-paper/85 px-3 backdrop-blur sm:gap-3 sm:px-6">
        <button
          type="button"
          class="rounded-md p-2 text-ink/70 hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40 lg:hidden"
          aria-label="Open navigation"
          aria-controls="app-sidebar"
          :aria-expanded="drawer"
          @click="drawer = true"
        >
          <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        </button>

        <!-- Breadcrumb -->
        <nav aria-label="Breadcrumb" class="min-w-0">
          <ol class="flex min-w-0 items-center gap-1.5 text-[13px]">
            <li class="hidden text-ink/45 sm:block">{{ current?.group.title ?? "Workspace" }}</li>
            <li class="hidden text-ink/25 sm:block" aria-hidden="true">/</li>
            <li v-if="current && route.path !== current.item.to && route.meta.title !== current.item.label" class="flex min-w-0 items-center gap-1.5">
              <RouterLink :to="current.item.to" class="truncate text-ink/55 hover:text-ink">{{ current.item.label }}</RouterLink>
              <span class="text-ink/25" aria-hidden="true">/</span>
            </li>
            <li class="truncate font-medium text-ink" aria-current="page">{{ route.meta.title ?? current?.item.label ?? "Workspace" }}</li>
          </ol>
        </nav>

        <div class="ml-auto flex items-center gap-1 sm:gap-2">
          <button
            type="button"
            class="flex items-center gap-2 rounded-lg border border-ink/12 bg-sheet/60 px-2.5 py-1.5 text-sm text-ink/55 transition hover:border-ink/25 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
            aria-label="Search pages (Ctrl+K)"
            aria-keyshortcuts="Control+K Meta+K"
            @click="paletteOpen = true"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
            <span class="hidden md:inline">Jump to…</span>
            <kbd class="hidden rounded border border-ink/15 px-1 font-mono text-[10px] text-ink/45 md:inline">{{ isMac ? "⌘" : "Ctrl" }} K</kbd>
          </button>

          <div class="hidden px-2 text-right xl:block" aria-label="Nepal time">
            <p class="readout text-[13px] leading-tight text-ink">{{ clock }} <span class="text-ink/40">NPT</span></p>
            <p class="font-mono text-[9.5px] tracking-[0.12em] text-ink/45 uppercase">{{ today }}</p>
          </div>

          <NotificationBell :unread="unreadNotifications" @changed="refreshBadges" />

          <button
            type="button"
            class="rounded-lg p-2 text-ink/60 hover:bg-panel hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
            :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            :title="isDark ? 'Light mode' : 'Dark mode'"
            @click="toggleTheme"
          >
            <svg v-if="isDark" viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
            </svg>
            <svg v-else viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
            </svg>
          </button>

          <!-- User menu -->
          <div v-if="user" ref="menuRoot" class="relative" @keydown="onMenuKey">
            <button
              type="button"
              class="flex items-center gap-2 rounded-full p-0.5 pr-1 hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40 sm:pr-2"
              aria-haspopup="menu"
              :aria-expanded="menuOpen"
              aria-controls="user-menu"
              :aria-label="`Account menu for ${user.full_name}`"
              @click.stop="openMenu"
            >
              <Avatar :name="user.full_name" :photo="user.photo" :size="30" />
              <svg viewBox="0 0 24 24" class="hidden h-3.5 w-3.5 text-ink/45 sm:block" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
            </button>
            <div
              v-if="menuOpen"
              id="user-menu"
              role="menu"
              aria-label="Account"
              class="rise absolute right-0 mt-2 w-60 overflow-hidden rounded-xl border border-ink/10 bg-sheet py-1 shadow-xl"
            >
              <div class="border-b border-dashed border-ink/15 px-4 py-3" role="presentation">
                <p class="truncate text-sm font-medium text-ink">{{ user.full_name }}</p>
                <p class="truncate text-xs text-ink/55">{{ user.email }}</p>
                <p class="mt-1 font-mono text-[10px] tracking-[0.12em] text-river uppercase">{{ ROLE_LABEL[user.role] }}</p>
              </div>
              <RouterLink to="/app/profile" role="menuitem" class="menu-item" @click="menuOpen = false">My profile</RouterLink>
              <button type="button" role="menuitem" class="menu-item" @click="changePassword">Change password</button>
              <button type="button" role="menuitem" class="menu-item" @click="menuOpen = false; paletteOpen = true">Jump to page…</button>
              <div class="my-1 border-t border-dashed border-ink/15" role="separator" />
              <button type="button" role="menuitem" class="menu-item menu-danger" @click="signOut">Sign out</button>
            </div>
          </div>
        </div>
      </header>

      <main id="main-content" ref="main" tabindex="-1" class="mx-auto w-full max-w-[1280px] px-4 py-6 outline-none sm:px-6 lg:px-8 lg:py-8">
        <RouterView v-slot="{ Component }">
          <component :is="Component" :key="route.path" class="rise" />
        </RouterView>
      </main>
    </div>

    <CommandPalette :open="paletteOpen" :commands="commands" @close="paletteOpen = false" @select="runCommand" />
    <PasswordModal :open="pwOpen" @close="pwOpen = false" @saved="pwOpen = false; toast.success('Password changed.')" />
    <ToastHost />
    <!-- mounted on demand so it teleports after (= above) any open Modal -->
    <ConfirmHost v-if="confirmState.open" />
  </div>
</template>

<style scoped>
@reference "../assets/Tailwind.css";
.menu-item {
  @apply block w-full px-4 py-2 text-left text-sm text-ink/80 hover:bg-panel hover:text-ink focus-visible:bg-panel focus-visible:outline-none;
}
.menu-danger {
  @apply text-rust hover:text-rust;
}
</style>
