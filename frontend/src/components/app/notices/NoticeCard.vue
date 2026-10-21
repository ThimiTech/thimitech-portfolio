<script setup lang="ts">
import Avatar from "../ui/Avatar.vue";
import StatusPill from "../ui/StatusPill.vue";
import { CATEGORY_LABEL, fmtAbs, fmtRel, type Notice } from "./notices";

defineProps<{ notice: Notice; pinned?: boolean; manage?: boolean; now: number }>();
const emit = defineEmits<{ open: [] }>();
</script>

<template>
  <article
    class="group relative flex gap-3 transition-colors focus-within:bg-panel/40 hover:bg-panel/40"
    :class="pinned ? 'panel h-full overflow-hidden p-4 pt-5' : 'px-4 py-4 sm:px-5'"
  >
    <!-- Survey flag "pin" marker -->
    <svg
      v-if="pinned"
      viewBox="0 0 20 28"
      class="absolute top-0 right-4 h-7 w-5 text-flag"
      aria-hidden="true"
    >
      <path d="M4 0v28" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 2h13l-4 5 4 5H4z" fill="currentColor" />
    </svg>

    <!-- Unread rail -->
    <span class="mt-2 w-2 shrink-0" aria-hidden="true">
      <span v-if="!notice.is_read && notice.status === 'published'" class="block h-2 w-2 rounded-full bg-flag" />
    </span>

    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1.5" :class="pinned ? 'pr-6' : ''">
        <StatusPill :status="notice.category" :label="CATEGORY_LABEL[notice.category]" />
        <span
          v-if="notice.department"
          class="inline-flex items-center gap-1 rounded border border-dashed border-sky/40 px-1.5 py-px font-mono text-[10.5px] tracking-wide text-sky uppercase"
        >
          <span aria-hidden="true">⌖</span>{{ notice.department.name }}
        </span>
        <span v-else class="font-mono text-[10.5px] tracking-wide text-ink/40 uppercase">All staff</span>
        <StatusPill v-if="manage && notice.status !== 'published'" :status="notice.status" />
        <span
          v-if="!notice.is_read && notice.status === 'published'"
          class="font-mono text-[10.5px] tracking-wide text-flag uppercase"
        >Unread</span>
      </div>

      <h3 class="mt-2 font-display text-[17px] leading-snug text-ink" :class="notice.is_read ? 'font-normal' : 'font-semibold'">
        <button
          type="button"
          class="text-left outline-none after:absolute after:inset-0 after:rounded-xl after:content-[''] focus-visible:after:ring-2 focus-visible:after:ring-flag/40"
          @click="emit('open')"
        >
          {{ notice.title }}
        </button>
      </h3>

      <p class="mt-1 line-clamp-2 text-sm text-ink/60">{{ notice.body }}</p>

      <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-ink/60">
        <span v-if="notice.author" class="flex items-center gap-1.5">
          <Avatar :name="notice.author.full_name" :photo="notice.author.photo" :size="20" />
          <span class="text-ink/75">{{ notice.author.full_name }}</span>
        </span>
        <time :datetime="notice.publish_at" class="font-mono text-[11px] tabular-nums">
          <span class="text-ink/50">{{ fmtRel(notice.publish_at, now) }}</span>
          <span class="text-ink/35"> · {{ fmtAbs(notice.publish_at) }}</span>
        </time>
        <span v-if="notice.attachment" class="flex items-center gap-1 font-mono text-[11px] text-river">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="m21 11-8.6 8.6a5 5 0 0 1-7-7L14 4a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4L15.6 7" />
          </svg>
          <span>Attachment</span>
        </span>
        <span v-if="notice.read_count !== null" class="font-mono text-[11px] text-ink/45">
          {{ notice.read_count }} read
        </span>
      </div>
    </div>
  </article>
</template>
