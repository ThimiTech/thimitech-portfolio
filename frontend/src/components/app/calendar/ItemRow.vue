<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import StatusPill from "../ui/StatusPill.vue";
import { AUDIENCE_LABEL, KIND, fmtDate, npDate, npTime, type FeedItem } from "./calendar";

const props = defineProps<{ item: FeedItem }>();
const emit = defineEmits<{ edit: [item: FeedItem]; delete: [item: FeedItem] }>();

const k = computed(() => KIND[props.item.kind]);

const when = computed(() => {
  const it = props.item;
  const short = (d: string) => fmtDate(d, { day: "2-digit", month: "short" });
  if (it.kind === "event") {
    const s = npDate(it.start), e = npDate(it.end);
    if (it.all_day) return s === e ? "All day" : `${short(s)} → ${short(e)} · all day`;
    return s === e ? `${npTime(it.start)}–${npTime(it.end)}` : `${short(s)} ${npTime(it.start)} → ${short(e)} ${npTime(it.end)}`;
  }
  if (it.start !== it.end) return `${short(it.start)} → ${short(it.end)}`;
  return "All day";
});

const person = computed(() => ("user" in props.item.meta ? props.item.meta.user : null));
</script>

<template>
  <article class="flex gap-3 py-3">
    <span class="mt-1 h-2 w-2 shrink-0 rounded-full" :class="k.dot" aria-hidden="true" />
    <div class="min-w-0 flex-1">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span class="rounded border px-1 font-mono text-[9.5px] tracking-wider" :class="k.chip">
          <span aria-hidden="true">{{ k.prefix }}</span><span class="sr-only">{{ k.label }}</span>
        </span>
        <span class="readout text-[11px] text-ink/55">{{ when }}</span>
      </div>
      <h3 class="mt-1 text-[14px] leading-snug font-medium text-ink">{{ item.title }}</h3>

      <!-- Kind-specific detail -->
      <div class="mt-1 space-y-1 text-[12.5px] text-ink/65">
        <template v-if="item.kind === 'holiday'">
          <StatusPill v-if="item.meta.is_optional" status="optional" label="Optional holiday" />
          <StatusPill v-else status="holiday" label="Public holiday" />
          <p v-if="item.meta.description">{{ item.meta.description }}</p>
        </template>

        <template v-else-if="item.kind === 'event'">
          <p class="flex flex-wrap items-center gap-x-2 gap-y-1">
            <StatusPill status="event" :label="AUDIENCE_LABEL[item.meta.audience]" />
            <span v-if="item.meta.department">{{ item.meta.department.name }}</span>
          </p>
          <p v-if="item.meta.location"><span class="ledger-label mr-1.5">At</span>{{ item.meta.location }}</p>
          <p v-if="item.meta.description" class="whitespace-pre-line">{{ item.meta.description }}</p>
          <p v-if="item.meta.created_by" class="text-ink/50">
            <span class="ledger-label mr-1.5">By</span>{{ item.meta.created_by.full_name }}
          </p>
        </template>

        <template v-else-if="item.kind === 'leave'">
          <p class="flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full" :style="{ background: item.meta.leave_type.color }" aria-hidden="true" />
              {{ item.meta.leave_type.name }}
            </span>
            <span class="readout text-ink/50">· {{ item.meta.days }} day{{ item.meta.days === "1.0" ? "" : "s" }}</span>
            <StatusPill v-if="item.meta.half_day" status="info" label="Half day" />
          </p>
        </template>

        <template v-else-if="item.kind === 'work_anniversary'">
          <p class="readout">{{ item.meta.years }} yr{{ item.meta.years === 1 ? "" : "s" }} at Thimi Tech</p>
        </template>

        <p v-if="person">
          <RouterLink
            :to="{ name: 'app-person', params: { id: person.id } }"
            class="text-river underline decoration-dashed underline-offset-2 hover:text-ink"
          >
            View {{ person.full_name }}'s profile
          </RouterLink>
        </p>
      </div>

      <div v-if="item.kind === 'event' && item.meta.can_edit" class="mt-2 flex gap-2">
        <button type="button" class="btn-ghost btn-sm" :aria-label="`Edit ${item.title}`" @click="emit('edit', item)">Edit</button>
        <button type="button" class="btn-danger btn-sm" :aria-label="`Delete ${item.title}`" @click="emit('delete', item)">Delete</button>
      </div>
    </div>
  </article>
</template>
