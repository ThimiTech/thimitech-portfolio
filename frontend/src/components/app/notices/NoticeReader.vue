<script setup lang="ts">
import { ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import Avatar from "../ui/Avatar.vue";
import StatusPill from "../ui/StatusPill.vue";
import { CATEGORY_LABEL, downloadAttachment, fmtAbs, fmtRel, type HttpError, type Notice } from "./notices";

const props = defineProps<{ notice: Notice | null; now: number }>();
const emit = defineEmits<{ close: []; edit: [Notice]; readers: [Notice]; deleted: [number] }>();

const confirming = ref(false);
const deleting = ref(false);
const error = ref("");

watch(
  () => props.notice?.id,
  () => {
    confirming.value = false;
    error.value = "";
  },
);

const downloading = ref(false);
async function download() {
  const n = props.notice;
  if (!n) return;
  downloading.value = true;
  error.value = "";
  try {
    await downloadAttachment(n);
  } catch (err) {
    const e = err as HttpError;
    error.value = e?.response?.status === 404 ? "This attachment is no longer available." : "Could not download the attachment. Try again.";
  } finally {
    downloading.value = false;
  }
}

async function remove() {
  const n = props.notice;
  if (!n) return;
  deleting.value = true;
  error.value = "";
  try {
    await api.delete(`notices/${n.id}/`);
    emit("deleted", n.id);
  } catch (err) {
    const e = err as HttpError;
    error.value = e?.response?.data?.detail ?? "Could not delete this notice. Try again.";
  } finally {
    deleting.value = false;
    confirming.value = false;
  }
}
</script>

<template>
  <Modal :open="!!notice" :title="notice?.title ?? 'Notice'" width="max-w-2xl" @close="emit('close')">
    <article v-if="notice" class="grid gap-5">
      <div class="flex flex-wrap items-center gap-2">
        <StatusPill :status="notice.category" :label="CATEGORY_LABEL[notice.category]" />
        <StatusPill v-if="notice.status !== 'published'" :status="notice.status" />
        <span v-if="notice.pinned" class="font-mono text-[10.5px] tracking-wide text-flag uppercase">⚑ Pinned</span>
        <span class="font-mono text-[10.5px] tracking-wide text-ink/50 uppercase">
          {{ notice.department ? `⌖ ${notice.department.name}` : "All staff" }}
        </span>
      </div>

      <div class="flex items-center gap-3 border-y border-dashed border-ink/15 py-3">
        <Avatar v-if="notice.author" :name="notice.author.full_name" :photo="notice.author.photo" :size="36" />
        <div class="min-w-0">
          <p class="text-sm text-ink">{{ notice.author?.full_name ?? "Unknown author" }}</p>
          <p class="readout text-[11px] text-ink/50">
            <time :datetime="notice.publish_at">{{ fmtAbs(notice.publish_at) }} NPT</time>
            · {{ fmtRel(notice.publish_at, now) }}
          </p>
          <p v-if="notice.expires_at" class="readout text-[11px] text-ink/45">
            Expires <time :datetime="notice.expires_at">{{ fmtAbs(notice.expires_at) }}</time>
          </p>
        </div>
      </div>

      <div class="text-[15px] leading-relaxed whitespace-pre-line text-ink/85">{{ notice.body }}</div>

      <button
        v-if="notice.attachment"
        type="button"
        :disabled="downloading"
        :aria-busy="downloading"
        class="flex w-full items-center gap-3 rounded-lg border border-dashed border-ink/20 px-3 py-2.5 text-left text-sm text-river hover:border-river hover:bg-panel/50 focus-visible:ring-2 focus-visible:ring-flag/40 focus-visible:outline-none disabled:opacity-60"
        @click="download"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="m21 11-8.6 8.6a5 5 0 0 1-7-7L14 4a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4L15.6 7" />
        </svg>
        <span class="min-w-0 flex-1 truncate font-mono text-xs">{{ notice.attachment_name ?? "Attachment" }}</span>
        <span class="ledger-label shrink-0">{{ downloading ? "Fetching…" : "Download" }}</span>
      </button>

      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
    </article>

    <template v-if="notice?.can_edit" #footer>
      <div class="flex w-full flex-wrap items-center justify-between gap-2">
        <button type="button" class="btn-ghost btn-sm" @click="emit('readers', notice)">
          Readers<span v-if="notice.read_count !== null" class="readout text-ink/50">· {{ notice.read_count }}</span>
        </button>
        <div class="flex flex-wrap gap-2">
          <template v-if="confirming">
            <span class="self-center text-xs text-rust">Delete for everyone?</span>
            <button type="button" class="btn-ghost btn-sm" @click="confirming = false">Keep</button>
            <button type="button" class="btn-danger btn-sm" :disabled="deleting" @click="remove">
              {{ deleting ? "Deleting…" : "Yes, delete" }}
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn-danger btn-sm" @click="confirming = true">Delete</button>
            <button type="button" class="btn-ink btn-sm" @click="emit('edit', notice)">Edit</button>
          </template>
        </div>
      </div>
    </template>
  </Modal>
</template>
