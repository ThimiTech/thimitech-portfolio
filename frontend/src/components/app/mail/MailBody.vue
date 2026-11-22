<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { mailDocument } from "./mail";

// Email HTML is someone else's markup: sanitized (mail.ts), then shown in an iframe with no scripts allowed and a
// CSP that blocks remote loads unless the reader asks for images. allow-same-origin only lets us measure its height.
const props = defineProps<{ html: string; images: boolean }>();
const frame = ref<HTMLIFrameElement | null>(null);
const height = ref(120);
const doc = computed(() => mailDocument(props.html, props.images));
let observer: ResizeObserver | null = null;

function measure() {
  const d = frame.value?.contentDocument;
  if (d?.documentElement) height.value = Math.max(80, d.documentElement.scrollHeight);
}
function onLoad() {
  observer?.disconnect();
  measure();
  const body = frame.value?.contentDocument?.body;
  if (body && typeof ResizeObserver !== "undefined") {
    observer = new ResizeObserver(measure);
    observer.observe(body);
  }
}
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <iframe
    ref="frame"
    :srcdoc="doc"
    title="Message body"
    sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
    referrerpolicy="no-referrer"
    class="block w-full rounded-lg border-0 bg-white"
    :style="{ height: `${height}px` }"
    @load="onLoad"
  />
</template>
