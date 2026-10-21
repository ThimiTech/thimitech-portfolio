<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ status: string; label?: string }>();

// Map-legend palette: moss = good, contour = waiting, rust = bad, sky = informational
const TONE: Record<string, string> = {
  present: "moss", approved: "moss", active: "moss", published: "moss", read: "moss",
  late: "contour", pending: "contour", scheduled: "contour", optional: "contour",
  absent: "rust", rejected: "rust", urgent: "rust", expired: "rust",
  on_leave: "sky", remote: "sky", holiday: "sky", info: "sky", event: "sky", hr: "sky", policy: "sky",
  // projects / inventory / finance
  done: "moss", available: "moss", paid: "moss", returned: "moss",
  review: "contour", maintenance: "contour", submitted: "contour", draft: "contour", high: "contour",
  active_task: "sky", assigned: "sky", issued: "sky", in_progress: "sky",
  overdue: "rust", cancelled: "rust", void: "rust", lost: "rust",
};

const CLASSES: Record<string, string> = {
  moss: "border-moss/30 bg-moss/10 text-moss",
  contour: "border-contour/40 bg-contour/12 text-contour-ink",
  rust: "border-rust/30 bg-rust/10 text-rust",
  sky: "border-sky/30 bg-sky/10 text-sky",
  neutral: "border-ink/15 bg-ink/[0.04] text-ink/55",
};

const cls = computed(() => CLASSES[TONE[props.status] ?? "neutral"]);
const text = computed(() => props.label ?? props.status.replace(/_/g, " "));
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.08em] whitespace-nowrap"
    :class="cls"
  >
    <span class="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
    {{ text }}
  </span>
</template>
