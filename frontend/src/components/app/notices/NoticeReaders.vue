<script setup lang="ts">
import { computed, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "../ui/Modal.vue";
import Avatar from "../ui/Avatar.vue";
import EmptyState from "../ui/EmptyState.vue";
import { fmtAbs, type HttpError, type Notice, type ReadersResponse } from "./notices";

const props = defineProps<{ notice: Notice | null }>();
const emit = defineEmits<{ close: [] }>();

const data = ref<ReadersResponse | null>(null);
const loading = ref(false);
const error = ref("");
const tab = ref<"read" | "unread">("read");

async function load() {
  if (!props.notice) return;
  loading.value = true;
  error.value = "";
  data.value = null;
  try {
    data.value = (await api.get<ReadersResponse>(`notices/${props.notice.id}/readers/`)).data;
  } catch (err) {
    const e = err as HttpError;
    error.value = e?.response?.data?.detail ?? "Could not load readers.";
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.notice?.id,
  (id) => {
    tab.value = "read";
    if (id) load();
  },
);

const rows = computed(() => (data.value ? data.value[tab.value] : []));
const pct = computed(() =>
  data.value && data.value.audience_count ? Math.min(100, Math.round((data.value.read_count / data.value.audience_count) * 100)) : 0,
);
</script>

<template>
  <Modal :open="!!notice" :title="`Readers · ${notice?.title ?? ''}`" @close="emit('close')">
    <div v-if="loading" class="grid gap-3" aria-busy="true" aria-label="Loading readers">
      <div v-for="i in 4" :key="i" class="h-9 rounded-lg border border-dashed border-ink/15 bg-panel/40 motion-safe:animate-pulse" />
    </div>

    <div v-else-if="error" class="py-6 text-center">
      <p role="alert" class="text-sm text-rust">{{ error }}</p>
      <button type="button" class="btn-ghost btn-sm mt-3" @click="load">Retry</button>
    </div>

    <div v-else-if="data" class="grid gap-4">
      <div>
        <p class="ledger-label">Reach</p>
        <p class="mt-1 font-display text-3xl text-ink">
          {{ data.read_count }}<span class="text-lg text-ink/40"> / {{ data.audience_count }}</span>
        </p>
        <div
          class="mt-2 h-1.5 overflow-hidden rounded-full bg-panel"
          role="progressbar"
          :aria-valuenow="pct"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`${pct}% of the audience has read this notice`"
        >
          <div class="h-full bg-moss" :style="{ width: `${pct}%` }" />
        </div>
      </div>

      <div class="flex gap-1 border-b border-dashed border-ink/15" role="tablist" aria-label="Reader lists">
        <button
          v-for="t in (['read', 'unread'] as const)"
          :key="t"
          type="button"
          role="tab"
          :aria-selected="tab === t"
          class="-mb-px border-b-2 px-3 py-2 font-mono text-[11px] tracking-wide uppercase focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          :class="tab === t ? 'border-flag text-ink' : 'border-transparent text-ink/50 hover:text-ink'"
          @click="tab = t"
        >
          {{ t === "read" ? "Read" : "Not read" }} · {{ data[t].length }}
        </button>
      </div>

      <ul v-if="rows.length" class="grid max-h-[50vh] gap-0 overflow-y-auto" role="tabpanel">
        <li v-for="r in rows" :key="r.id" class="flex items-center gap-3 border-b border-dashed border-ink/10 py-2.5 last:border-0">
          <Avatar :name="r.full_name" :photo="r.photo" :size="28" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm text-ink">{{ r.full_name }}</p>
            <p class="truncate text-xs text-ink/50">{{ r.department?.name ?? "No department" }}</p>
          </div>
          <time v-if="r.read_at" :datetime="r.read_at" class="readout shrink-0 text-[11px] text-ink/50">{{ fmtAbs(r.read_at) }}</time>
        </li>
      </ul>
      <EmptyState v-else :title="tab === 'read' ? 'No one has read it yet' : 'Everyone has read it'" />
    </div>
  </Modal>
</template>
