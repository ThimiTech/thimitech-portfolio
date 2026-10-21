<script setup lang="ts">
import { computed } from "vue";
defineOptions({ name: "UserAvatar" });

const props = withDefaults(
  defineProps<{ name: string; photo?: string | null; size?: number; ring?: boolean }>(),
  { photo: null, size: 32, ring: false },
);

const initials = computed(() =>
  props.name
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("") || "?",
);

// Deterministic earthy tint per name
const TINTS = ["#7a6a52", "#b08d5b", "#5d7a4f", "#4f6d7a", "#8a5a44", "#6b6450"];
const tint = computed(() => TINTS[[...props.name].reduce((a, c) => a + c.charCodeAt(0), 0) % TINTS.length]);
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-medium text-on-accent"
    :class="ring ? 'ring-2 ring-flag/70 ring-offset-2 ring-offset-ink' : ''"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.38)}px`, background: tint }"
    :title="name"
  >
    <img v-if="photo" :src="photo" :alt="name" class="h-full w-full object-cover" />
    <span v-else aria-hidden="true">{{ initials }}</span>
  </span>
</template>
