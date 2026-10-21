<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import api from "@/api/api";
import { fmtRel } from "../notices/notices";

export interface AppNotification {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string;
  read_at: string | null;
  created_at: string;
}

/** Top-bar inbox. The unread count comes from the layout's nav-counts poll; the list loads on open. */
const props = defineProps<{ unread: number }>();
const emit = defineEmits<{ changed: [] }>();
const router = useRouter();

const open = ref(false);
const items = ref<AppNotification[] | null>(null);
const error = ref("");
const root = ref<HTMLElement | null>(null);

async function load() {
  error.value = "";
  try {
    items.value = (await api.get<AppNotification[]>("notifications/")).data;
  } catch {
    error.value = "Couldn't load notifications.";
  }
}

async function toggle() {
  open.value = !open.value;
  if (!open.value) return;
  await load();
  await nextTick();
  root.value?.querySelector<HTMLElement>("[data-item], [data-focus]")?.focus();
}

async function select(n: AppNotification) {
  if (!n.read_at) {
    n.read_at = new Date().toISOString();
    api.post(`notifications/${n.id}/read/`).then(() => emit("changed")).catch(() => (n.read_at = null));
  }
  if (n.link) {
    open.value = false;
    router.push(n.link);
  }
}

async function readAll() {
  try {
    await api.post("notifications/read-all/");
    const now = new Date().toISOString();
    for (const n of items.value ?? []) n.read_at ??= now;
    emit("changed");
  } catch {
    error.value = "Couldn't mark them read. Try again.";
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && open.value) {
    open.value = false;
    root.value?.querySelector<HTMLElement>("[aria-haspopup]")?.focus();
  }
}
function onDocClick(e: MouseEvent) {
  if (open.value && !root.value?.contains(e.target as Node)) open.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocClick));

const label = () => (props.unread ? `Notifications, ${props.unread} unread` : "Notifications");
</script>

<template>
  <div ref="root" class="relative" @keydown="onKey">
    <button
      type="button"
      class="relative rounded-lg p-2 text-ink/60 hover:bg-panel hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
      aria-haspopup="dialog"
      :aria-expanded="open"
      aria-controls="notif-panel"
      :aria-label="label()"
      @click.stop="toggle"
    >
      <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      <span
        v-if="unread"
        class="readout absolute -top-0.5 -right-0.5 min-w-[1.1rem] rounded-full bg-flag px-1 text-center text-[10px] leading-[1.1rem] font-medium text-on-accent"
        aria-hidden="true"
      >{{ unread > 99 ? "99+" : unread }}</span>
    </button>

    <div
      v-if="open"
      id="notif-panel"
      role="dialog"
      aria-label="Notifications"
      class="rise absolute right-0 mt-2 w-[min(22rem,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-ink/10 bg-sheet shadow-xl"
    >
      <div class="flex items-center justify-between border-b border-dashed border-ink/15 px-4 py-2.5">
        <p class="text-sm font-medium text-ink">Notifications</p>
        <button
          v-if="items?.some((n) => !n.read_at)"
          type="button"
          data-focus
          class="rounded text-xs font-medium text-river hover:text-flag focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          @click="readAll"
        >Mark all read</button>
      </div>
      <p v-if="error" class="px-4 py-3 text-sm text-rust" role="alert">{{ error }}</p>
      <p v-else-if="items === null" class="px-4 py-6 text-center text-sm text-ink/50" aria-busy="true">Loading…</p>
      <p v-else-if="!items.length" class="px-4 py-8 text-center text-sm text-ink/55">You're all caught up.</p>
      <ul v-else class="max-h-[60vh] divide-y divide-dashed divide-ink/10 overflow-y-auto">
        <li v-for="n in items" :key="n.id">
          <button
            type="button"
            data-item
            class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-panel/50 focus-visible:bg-panel/50 focus-visible:outline-none"
            @click="select(n)"
          >
            <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full" :class="n.read_at ? 'border border-ink/20' : 'bg-flag'" aria-hidden="true" />
            <span class="min-w-0 flex-1">
              <span class="block text-sm" :class="n.read_at ? 'text-ink/70' : 'font-medium text-ink'">
                <span v-if="!n.read_at" class="sr-only">Unread: </span>{{ n.title }}
              </span>
              <span v-if="n.body" class="mt-0.5 line-clamp-2 block text-xs text-ink/55">{{ n.body }}</span>
              <span class="mt-0.5 block font-mono text-[10.5px] text-ink/45">{{ fmtRel(n.created_at) }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
