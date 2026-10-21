<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import api from "@/api/api";
import { toast } from "../../components/app/ui/toast";
import { useAuth } from "@/stores/auth";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import EmptyState from "../../components/app/ui/EmptyState.vue";
import NoticeCard from "../../components/app/notices/NoticeCard.vue";
import NoticeReader from "../../components/app/notices/NoticeReader.vue";
import NoticeReaders from "../../components/app/notices/NoticeReaders.vue";
import NoticeComposer from "../../components/app/notices/NoticeComposer.vue";
import { CATEGORIES, inAudience, type Category, type HttpError, type Notice, type NoticeStatus } from "../../components/app/notices/notices";

const { user, hasRole } = useAuth();
const canPost = computed(() => hasRole("manager"));

// ── filters ──────────────────────────────────────────────
const category = ref<Category | "">("");
const unreadOnly = ref(false);
const search = ref("");
const manage = ref(false);
const status = ref<NoticeStatus | "">("");
const hasFilters = computed(() => !!(category.value || unreadOnly.value || search.value.trim() || status.value));

function clearFilters() {
  category.value = "";
  unreadOnly.value = false;
  search.value = "";
  status.value = "";
}

// ── data ─────────────────────────────────────────────────
const notices = ref<Notice[]>([]);
const loading = ref(true);
const error = ref("");
const unread = ref<number | null>(null);
let seq = 0;

async function load() {
  const mine = ++seq;
  loading.value = true;
  error.value = "";
  const params: Record<string, string> = {};
  if (category.value) params.category = category.value;
  if (unreadOnly.value) params.unread = "1";
  if (search.value.trim()) params.search = search.value.trim();
  if (manage.value) {
    params.manage = "1";
    if (status.value) params.status = status.value;
  }
  try {
    const { data } = await api.get<Notice[]>("notices/", { params });
    if (mine === seq) notices.value = data;
  } catch (err) {
    const e = err as HttpError;
    if (mine === seq) error.value = e?.response?.data?.detail ?? "The notice board could not be loaded.";
  } finally {
    if (mine === seq) loading.value = false;
  }
}

async function loadUnread() {
  try {
    unread.value = (await api.get<{ unread: number }>("notices/unread-count/")).data.unread;
  } catch {
    unread.value = null;
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 300);
});
watch([category, unreadOnly, manage, status], load);
watch(manage, (on) => !on && (status.value = ""));

// Relative timestamps tick once a minute.
const now = ref(Date.now());
const clock = setInterval(() => (now.value = Date.now()), 60_000);

onMounted(() => {
  load();
  loadUnread();
});
onBeforeUnmount(() => {
  clearInterval(clock);
  clearTimeout(searchTimer);
});

const pinned = computed(() => notices.value.filter((n) => n.pinned));
const feed = computed(() => notices.value.filter((n) => !n.pinned));

const say = (msg: string) => toast.success(msg);

// ── reading ──────────────────────────────────────────────
const reading = ref<Notice | null>(null);

// Reads (and the unread counter) only cover live notices addressed to me; manage mode
// also lists notices for other departments, which must not be marked read.
const countsAsUnread = (n: Notice) =>
  !n.is_read && n.status === "published" && inAudience(n, user.value?.department?.id);

async function open(n: Notice) {
  reading.value = n;
  if (!countsAsUnread(n)) return;
  n.is_read = true; // optimistic
  if (unread.value) unread.value--;
  try {
    await api.post(`notices/${n.id}/read/`);
  } catch {
    n.is_read = false;
    loadUnread();
  }
}

const markingAll = ref(false);
async function markAllRead() {
  markingAll.value = true;
  const before = notices.value.filter(countsAsUnread);
  before.forEach((n) => (n.is_read = true));
  try {
    const { data } = await api.post<{ marked: number }>("notices/read-all/");
    unread.value = 0;
    say(data.marked ? `Marked ${data.marked} notice${data.marked === 1 ? "" : "s"} as read.` : "Already all caught up.");
  } catch {
    before.forEach((n) => (n.is_read = false));
    say("Could not mark notices as read. Try again.");
  } finally {
    markingAll.value = false;
  }
}

// ── authoring ────────────────────────────────────────────
const composerOpen = ref(false);
const editing = ref<Notice | null>(null);
const readersFor = ref<Notice | null>(null);

function compose(n: Notice | null = null) {
  editing.value = n;
  reading.value = null;
  composerOpen.value = true;
}

function onSaved(n: Notice, created: boolean) {
  composerOpen.value = false;
  editing.value = null;
  say(created ? (n.status === "scheduled" ? "Notice scheduled." : "Notice published.") : "Notice updated.");
  load();
}

function onDeleted(id: number) {
  reading.value = null;
  notices.value = notices.value.filter((n) => n.id !== id);
  say("Notice deleted.");
  loadUnread();
}

function showReaders(n: Notice) {
  reading.value = null;
  readersFor.value = n;
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="A5 · Notice board"
      title="Notice board"
      description="Announcements, policies and field bulletins from across Thimi Tech."
    >
      <template #actions>
        <span v-if="unread !== null" class="readout mr-1 text-xs text-ink/55" aria-live="polite">
          <span class="text-flag">{{ unread }}</span> unread
        </span>
        <button type="button" class="btn-ghost btn-sm" :disabled="markingAll || unread === 0" @click="markAllRead">
          Mark all read
        </button>
        <button
          v-if="canPost"
          type="button"
          class="btn-ghost btn-sm"
          :aria-pressed="manage"
          :class="manage && 'border-ink bg-ink text-paper hover:bg-river'"
          @click="manage = !manage"
        >
          Manage
        </button>
        <button v-if="canPost" type="button" class="btn-primary btn-sm" @click="compose()">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          New notice
        </button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="mb-6 grid gap-3">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label for="notice-search" class="sr-only">Search notices</label>
        <div class="relative sm:max-w-xs sm:flex-1">
          <svg viewBox="0 0 24 24" class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink/40" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
          </svg>
          <input id="notice-search" v-model="search" type="search" class="input pl-9" placeholder="Search title or body" />
        </div>
        <button
          type="button"
          class="btn-ghost btn-sm self-start sm:self-auto"
          :aria-pressed="unreadOnly"
          :class="unreadOnly && 'border-flag/50 bg-flag/10 text-flag hover:bg-flag/15'"
          @click="unreadOnly = !unreadOnly"
        >
          <span class="h-1.5 w-1.5 rounded-full" :class="unreadOnly ? 'bg-flag' : 'bg-ink/30'" aria-hidden="true" />
          Unread only
        </button>
        <div v-if="manage" class="field sm:ml-auto sm:w-44">
          <label for="notice-status" class="sr-only">Status</label>
          <select id="notice-status" v-model="status" class="input py-1.5 text-xs">
            <option value="">All statuses</option>
            <option value="published">Published</option>
            <option value="scheduled">Scheduled</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      <div class="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0" role="group" aria-label="Filter by category">
        <div class="flex w-max gap-1.5">
          <button
            v-for="c in [{ value: '', label: 'All' }, ...CATEGORIES]"
            :key="c.value"
            type="button"
            class="rounded-full border px-3 py-1 font-mono text-[11px] tracking-wide uppercase transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
            :class="category === c.value ? 'border-ink bg-ink text-paper' : 'border-ink/15 text-ink/60 hover:border-ink/30 hover:text-ink'"
            :aria-pressed="category === c.value"
            @click="category = c.value as Category | ''"
          >
            {{ c.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !notices.length" aria-busy="true" aria-label="Loading notices" class="grid gap-3">
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div v-for="i in 2" :key="i" class="h-36 rounded-xl border border-dashed border-ink/15 bg-panel/40 motion-safe:animate-pulse" />
      </div>
      <div v-for="i in 4" :key="`f${i}`" class="h-24 rounded-xl border border-dashed border-ink/15 bg-panel/30 motion-safe:animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="panel">
      <EmptyState title="Signal lost" :hint="error">
        <button type="button" class="btn-ghost btn-sm" @click="load">Retry</button>
      </EmptyState>
    </div>

    <!-- Empty -->
    <div v-else-if="!notices.length" class="panel">
      <EmptyState
        :title="hasFilters ? 'Nothing matches these filters' : manage ? 'No notices to manage' : 'The board is clear'"
        :hint="hasFilters ? 'Try another category or clear the search.' : 'New announcements will appear here.'"
      >
        <button v-if="hasFilters" type="button" class="btn-ghost btn-sm" @click="clearFilters">Clear filters</button>
        <button v-else-if="canPost" type="button" class="btn-primary btn-sm" @click="compose()">Post the first notice</button>
      </EmptyState>
    </div>

    <div v-else class="grid gap-8 transition-opacity" :class="loading && 'opacity-60'" :aria-busy="loading">
      <section v-if="pinned.length" aria-labelledby="pinned-h" class="rise">
        <h2 id="pinned-h" class="ledger-label mb-3 flex items-center gap-2">
          <span class="text-flag" aria-hidden="true">⚑</span> Pinned · {{ pinned.length }}
        </h2>
        <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <li v-for="n in pinned" :key="n.id">
            <NoticeCard :notice="n" pinned :manage="manage" :now="now" @open="open(n)" />
          </li>
        </ul>
      </section>

      <section v-if="feed.length" aria-labelledby="feed-h" class="rise" style="animation-delay: 60ms">
        <h2 id="feed-h" class="ledger-label mb-3">{{ manage ? "All notices you manage" : "Latest" }} · {{ feed.length }}</h2>
        <ul class="panel divide-y divide-dashed divide-ink/10 overflow-hidden">
          <li v-for="n in feed" :key="n.id">
            <NoticeCard :notice="n" :manage="manage" :now="now" @open="open(n)" />
          </li>
        </ul>
        <p v-if="notices.length >= 200" class="mt-3 text-center font-mono text-[11px] text-ink/45">
          Showing the latest 200 · narrow with search or filters
        </p>
      </section>
    </div>

    <NoticeReader :notice="reading" :now="now" @close="reading = null" @edit="compose" @readers="showReaders" @deleted="onDeleted" />
    <NoticeReaders :notice="readersFor" @close="readersFor = null" />
    <NoticeComposer :open="composerOpen" :notice="editing" @close="composerOpen = false" @saved="onSaved" />
  </div>
</template>
