<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { isAxiosError } from "axios";
import api from "@/api/api";
import PageHeader from "@/components/app/ui/PageHeader.vue";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import SkeletonBlock from "@/components/app/ui/SkeletonBlock.vue";
import LoadError from "@/components/app/org/LoadError.vue";
import MailBody from "@/components/app/mail/MailBody.vue";
import MailCompose from "@/components/app/mail/MailCompose.vue";
import { toast } from "@/components/app/ui/toast";
import { confirmDialog } from "@/components/app/ui/confirm";
import { errMsg } from "@/components/app/attendance/attendance";
import {
  displayName, fileSize, hasRemoteImages, longDate, shortDate,
  type ComposeMode, type Folder, type MailAttachment, type MailMessage, type MailStatus, type MailSummary,
} from "@/components/app/mail/mail";

const route = useRoute();
const router = useRouter();

const status = ref<MailStatus | null>(null);
const statusError = ref("");
const connecting = ref(false);

const folders = ref<Folder[]>([]);
const folderId = computed(() => String(route.query.folder || folders.value.find((f) => f.type === "Inbox")?.id || folders.value[0]?.id || ""));
const folder = computed(() => folders.value.find((f) => f.id === folderId.value) || null);
const inTrash = computed(() => !!open.value && folders.value.find((f) => f.id === open.value!.folder)?.type === "Trash");

const rows = ref<MailSummary[]>([]);
const next = ref<number | null>(null);
const listLoading = ref(false);
const listError = ref("");
const search = ref("");
const activeSearch = ref("");
const unreadOnly = ref(false);

const open = ref<MailMessage | null>(null);
const openId = ref("");
const reading = ref(false);
const showImages = ref(false);

const compose = ref<{ open: boolean; mode: ComposeMode; source: MailMessage | null }>({ open: false, mode: "new", source: null });

/** A 409 from any mail call means the mailbox is not (or no longer) connected: show the connect screen. */
function handle(e: unknown, fallback: string) {
  if (isAxiosError(e) && e.response?.status === 409) {
    loadStatus();
    return "";
  }
  return errMsg(e, fallback);
}
function fail(e: unknown, fallback: string) {
  const msg = handle(e, fallback);
  if (msg) toast.error(msg);
}

async function loadStatus() {
  statusError.value = "";
  try {
    status.value = (await api.get<MailStatus>("mail/status/")).data;
    if (status.value.connected && !folders.value.length) await loadFolders();
  } catch (e) {
    statusError.value = errMsg(e, "Couldn't load your mailbox.");
  }
}

async function connect() {
  connecting.value = true;
  try {
    window.location.assign((await api.get<{ url: string }>("mail/connect/")).data.url);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't start connecting to Zoho."));
    connecting.value = false;
  }
}

async function disconnect() {
  const ok = await confirmDialog({
    title: "Disconnect Zoho Mail?",
    body: "Your mail stays in Zoho. This site forgets its access until you connect again.",
    confirmLabel: "Disconnect",
    danger: true,
  });
  if (!ok) return;
  try {
    await api.post("mail/disconnect/");
    Object.assign(status.value!, { connected: false, needs_reconnect: false, email: "" });
    folders.value = [];
    rows.value = [];
    open.value = null;
  } catch (e) {
    toast.error(errMsg(e, "Couldn't disconnect."));
  }
}

async function loadFolders() {
  try {
    folders.value = (await api.get<Folder[]>("mail/folders/")).data;
    await loadList();
  } catch (e) {
    listError.value = handle(e, "Couldn't load your folders.");
  }
}

let listSeq = 0;
async function loadList(more = false) {
  if (!folderId.value && !activeSearch.value) return;
  const seq = ++listSeq;
  listLoading.value = true;
  listError.value = "";
  try {
    const params = activeSearch.value
      ? { q: activeSearch.value, start: more ? next.value : 1 }
      : { folder: folderId.value, start: more ? next.value : 1, unread: unreadOnly.value ? 1 : undefined };
    const { data } = await api.get<{ results: MailSummary[]; next: number | null }>("mail/messages/", { params });
    if (seq !== listSeq) return;
    rows.value = more ? [...rows.value, ...data.results] : data.results;
    next.value = data.next;
  } catch (e) {
    if (seq === listSeq) listError.value = handle(e, "Couldn't load messages.");
  } finally {
    if (seq === listSeq) listLoading.value = false;
  }
}

function pickFolder(id: string) {
  activeSearch.value = search.value = "";
  open.value = null;
  router.replace({ query: { ...route.query, folder: id } });
}
watch(folderId, () => loadList());
watch(unreadOnly, () => loadList());

function runSearch() {
  activeSearch.value = search.value.trim();
  open.value = null;
  loadList();
}

let readSeq = 0;
async function read(m: MailSummary) {
  const seq = ++readSeq;
  openId.value = m.id;
  reading.value = true;
  showImages.value = false;
  try {
    const { data } = await api.get<MailMessage>(`mail/messages/${m.id}/`, { params: { folder: m.folder || folderId.value, mark_read: 1 } });
    if (seq !== readSeq) return;
    open.value = { ...data, folder: data.folder || m.folder || folderId.value };
    m.unread = false;
  } catch (e) {
    if (seq === readSeq) {
      fail(e, "Couldn't open that message.");
      openId.value = "";
    }
  } finally {
    if (seq === readSeq) reading.value = false;
  }
}
function closeReader() {
  open.value = null;
  openId.value = "";
}

async function markUnread() {
  const m = open.value;
  if (!m) return;
  try {
    await api.post(`mail/messages/${m.id}/read/`, { read: false });
    const row = rows.value.find((r) => r.id === m.id);
    if (row) row.unread = true;
    closeReader();
  } catch (e) {
    fail(e, "Couldn't mark it unread.");
  }
}

async function remove() {
  const m = open.value;
  if (!m) return;
  const forGood = inTrash.value;
  if (forGood && !(await confirmDialog({ title: "Delete for good?", body: "This removes the message from Zoho Mail permanently.", confirmLabel: "Delete", danger: true })))
    return;
  try {
    await api.delete(`mail/messages/${m.id}/`, { params: { folder: m.folder } });
    rows.value = rows.value.filter((r) => r.id !== m.id);
    closeReader();
    toast.success(forGood ? "Deleted." : "Moved to Trash.");
  } catch (e) {
    fail(e, "Couldn't delete it.");
  }
}

async function download(a: MailAttachment) {
  const m = open.value;
  if (!m) return;
  try {
    const { data } = await api.get<Blob>(`mail/messages/${m.id}/attachments/${encodeURIComponent(a.id)}/`, {
      params: { folder: m.folder, name: a.name },
      responseType: "blob",
    });
    const url = URL.createObjectURL(data);
    const link = Object.assign(document.createElement("a"), { href: url, download: a.name || "attachment" });
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  } catch (e) {
    fail(e, "Couldn't download the attachment.");
  }
}

function startCompose(mode: ComposeMode) {
  compose.value = { open: true, mode, source: mode === "new" ? null : open.value };
}
function sent() {
  compose.value.open = false;
  if (folder.value?.type === "Sent") loadList();
}

const remote = computed(() => !!open.value && hasRemoteImages(open.value.content));
const folderLabel = (f: Folder) => f.path?.replace(/^\//, "") || f.name;

onMounted(loadStatus);
</script>

<template>
  <div>
    <PageHeader eyebrow="Work · Mail" title="Mail" :description="status?.connected ? `Your Zoho mailbox: ${status.email}` : 'Read and send your company email without leaving the workspace.'">
      <template v-if="status?.connected" #actions>
        <button type="button" class="btn-ghost" @click="disconnect">Disconnect</button>
        <button type="button" class="btn-primary" @click="startCompose('new')">New message</button>
      </template>
    </PageHeader>

    <LoadError v-if="statusError" :message="statusError" @retry="loadStatus" />
    <SkeletonBlock v-else-if="!status" :rows="4" height="h-16" />

    <div v-else-if="!status.configured" class="panel">
      <EmptyState title="Mail isn't set up yet" hint="An administrator needs to add the Zoho Mail API keys (ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET) on the server." />
    </div>

    <div v-else-if="!status.connected" class="panel">
      <EmptyState
        :title="status.needs_reconnect ? 'Your Zoho connection has expired' : 'Connect your Zoho mailbox'"
        :hint="status.needs_reconnect
          ? 'Zoho no longer accepts the saved access. Connect again to keep reading your mail here.'
          : 'Sign in with your @thimitech.com Zoho account and allow access. Your mail stays in Zoho; this site reads and sends it on your behalf.'"
      >
        <button type="button" class="btn-primary" :disabled="connecting" @click="connect">{{ connecting ? "Opening Zoho…" : status.needs_reconnect ? "Reconnect" : "Connect Zoho Mail" }}</button>
      </EmptyState>
    </div>

    <div v-else class="grid gap-4 lg:grid-cols-[200px_minmax(0,380px)_minmax(0,1fr)]">
      <!-- Folders -->
      <nav aria-label="Mail folders" class="panel h-fit p-2" :class="{ 'hidden lg:block': open || reading }">
        <ul class="flex gap-1 overflow-x-auto lg:flex-col">
          <li v-for="f in folders" :key="f.id">
            <button
              type="button"
              class="w-full truncate rounded-md px-3 py-1.5 text-left text-sm whitespace-nowrap"
              :class="f.id === folderId && !activeSearch ? 'bg-panel font-medium text-ink' : 'text-ink/70 hover:bg-panel/60 hover:text-ink'"
              :aria-current="f.id === folderId && !activeSearch ? 'page' : undefined"
              @click="pickFolder(f.id)"
            >{{ folderLabel(f) }}</button>
          </li>
        </ul>
      </nav>

      <!-- Message list -->
      <section class="panel flex min-h-[60vh] flex-col overflow-hidden" :class="{ 'hidden lg:flex': open || reading }" aria-label="Messages">
        <form class="flex gap-2 border-b border-dashed border-ink/15 p-3" role="search" @submit.prevent="runSearch">
          <label class="sr-only" for="mail-search">Search mail</label>
          <input id="mail-search" v-model="search" type="search" class="input min-w-0 flex-1" placeholder="Search all mail…" />
          <button type="submit" class="btn-ghost">Search</button>
        </form>
        <div class="flex items-center justify-between px-3 py-2 text-xs text-ink/60">
          <span v-if="activeSearch">Results for “{{ activeSearch }}” · <button type="button" class="text-river hover:text-flag" @click="search = ''; runSearch()">clear</button></span>
          <span v-else>{{ folder ? folderLabel(folder) : "" }}</span>
          <label v-if="!activeSearch" class="flex items-center gap-1.5"><input v-model="unreadOnly" type="checkbox" /> Unread only</label>
        </div>

        <LoadError v-if="listError" :message="listError" :busy="listLoading" @retry="loadList()" />
        <div v-else-if="listLoading && !rows.length" class="p-3"><SkeletonBlock :rows="6" height="h-14" /></div>
        <EmptyState v-else-if="!rows.length" :title="activeSearch ? 'Nothing matches' : 'No messages here'" />
        <ul v-else class="flex-1 divide-y divide-dashed divide-ink/10 overflow-y-auto">
          <li v-for="m in rows" :key="`${m.folder}:${m.id}`">
            <button
              type="button"
              class="block w-full px-3 py-2.5 text-left hover:bg-panel/60 focus-visible:bg-panel focus-visible:outline-none"
              :class="{ 'bg-panel': m.id === openId }"
              @click="read(m)"
            >
              <span class="flex items-baseline gap-2">
                <span v-if="m.unread" class="h-2 w-2 shrink-0 rounded-full bg-flag" aria-label="Unread" />
                <span class="min-w-0 flex-1 truncate text-sm" :class="m.unread ? 'font-semibold text-ink' : 'text-ink/80'">
                  {{ folder?.type === "Sent" || folder?.type === "Drafts" ? displayName(m.to, "(no recipient)") : m.sender || displayName(m.from) }}
                </span>
                <span v-if="m.has_attachments" class="text-ink/45" aria-label="Has attachments">📎</span>
                <span class="readout shrink-0 text-[11px] text-ink/50">{{ shortDate(m.received) }}</span>
              </span>
              <span class="block truncate text-sm" :class="m.unread ? 'text-ink' : 'text-ink/70'">{{ m.subject || "(no subject)" }}</span>
              <span class="block truncate text-xs text-ink/50">{{ m.summary }}</span>
            </button>
          </li>
          <li v-if="next" class="p-3 text-center">
            <button type="button" class="btn-ghost" :disabled="listLoading" @click="loadList(true)">{{ listLoading ? "Loading…" : "Load more" }}</button>
          </li>
        </ul>
      </section>

      <!-- Reader -->
      <article class="panel min-w-0 p-5" :class="{ 'hidden lg:block': !open && !reading }" aria-live="polite">
        <SkeletonBlock v-if="reading" :rows="5" height="h-8" label="Opening message" />
        <EmptyState v-else-if="!open" title="No message selected" hint="Pick a message from the list to read it here." />
        <template v-else>
          <button type="button" class="mb-3 text-sm text-river hover:text-flag lg:hidden" @click="closeReader">← Back to {{ folder ? folderLabel(folder) : "messages" }}</button>
          <h2 class="font-display text-xl leading-snug font-medium break-words text-ink">{{ open.subject || "(no subject)" }}</h2>
          <dl class="mt-3 grid gap-1 text-sm">
            <div class="flex gap-2"><dt class="w-10 shrink-0 text-ink/50">From</dt><dd class="min-w-0 break-words">{{ open.from }}</dd></div>
            <div v-if="open.to" class="flex gap-2"><dt class="w-10 shrink-0 text-ink/50">To</dt><dd class="min-w-0 break-words">{{ open.to }}</dd></div>
            <div v-if="open.cc" class="flex gap-2"><dt class="w-10 shrink-0 text-ink/50">Cc</dt><dd class="min-w-0 break-words">{{ open.cc }}</dd></div>
            <div class="flex gap-2"><dt class="w-10 shrink-0 text-ink/50">Date</dt><dd class="readout">{{ longDate(open.received) }}</dd></div>
          </dl>

          <div class="mt-4 flex flex-wrap gap-2">
            <button type="button" class="btn-primary" @click="startCompose('reply')">Reply</button>
            <button type="button" class="btn-ghost" @click="startCompose('replyall')">Reply all</button>
            <button type="button" class="btn-ghost" @click="startCompose('forward')">Forward</button>
            <button type="button" class="btn-ghost" @click="markUnread">Mark unread</button>
            <button type="button" class="btn-ghost text-flag" @click="remove">{{ inTrash ? "Delete for good" : "Delete" }}</button>
          </div>

          <ul v-if="open.attachments.length" class="mt-4 flex flex-wrap gap-2">
            <li v-for="a in open.attachments" :key="a.id">
              <button type="button" class="flex items-center gap-2 rounded-lg border border-ink/10 bg-panel px-3 py-1.5 text-xs hover:border-river" @click="download(a)">
                <span class="max-w-56 truncate">📎 {{ a.name }}</span><span class="text-ink/50">{{ fileSize(a.size) }}</span>
              </button>
            </li>
          </ul>

          <p v-if="remote && !showImages" class="mt-4 flex flex-wrap items-center gap-2 rounded-lg bg-panel px-3 py-2 text-xs text-ink/70">
            Images from the internet are hidden to protect your privacy.
            <button type="button" class="text-river hover:text-flag" @click="showImages = true">Show images</button>
          </p>
          <div class="mt-4 border-t border-dashed border-ink/15 pt-4">
            <MailBody :html="open.content" :images="showImages" />
          </div>
        </template>
      </article>
    </div>

    <MailCompose
      v-if="status?.connected"
      :open="compose.open"
      :mode="compose.mode"
      :source="compose.source"
      :status="status"
      @close="compose.open = false"
      @sent="sent"
    />
  </div>
</template>
