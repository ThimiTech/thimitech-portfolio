<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from './pm'
const props = defineProps<{ source: string; empty?: string }>()
const emit = defineEmits<{ wikilink: [target: string] }>()
const html = computed(() => renderMarkdown(props.source))
function onClick(e: MouseEvent) {
  const a = (e.target as HTMLElement).closest('a')
  const href = a?.getAttribute('href') || ''
  if (href.startsWith('#wiki:')) {
    e.preventDefault()
    emit('wikilink', decodeURIComponent(href.slice(6)))
  }
}
</script>
<template>
  <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify in renderMarkdown -->
  <div v-if="source.trim()" class="md" @click="onClick" v-html="html" />
  <p v-else class="text-sm text-ink/50">{{ empty || 'Nothing written yet.' }}</p>
</template>
<style>
.md { line-height: 1.7; font-size: 0.9rem; overflow-wrap: anywhere; }
.md > * + * { margin-top: 0.75em; }
.md h1 { font-family: var(--font-display, inherit); font-size: 1.6rem; font-weight: 500; letter-spacing: -0.01em; }
.md h2 { font-family: var(--font-display, inherit); font-size: 1.25rem; font-weight: 500; margin-top: 1.4em; }
.md h3 { font-size: 1.05rem; font-weight: 600; margin-top: 1.2em; }
.md a { color: var(--color-river); text-decoration: underline; text-underline-offset: 2px; }
.md a[href^='#wiki:'] { color: var(--color-flag); text-decoration: none; border-bottom: 1px dashed currentColor; }
.md ul { list-style: disc; padding-left: 1.4em; }
.md ol { list-style: decimal; padding-left: 1.4em; }
.md li + li { margin-top: 0.2em; }
.md blockquote { border-left: 3px solid var(--color-contour); padding-left: 1em; color: color-mix(in srgb, var(--color-ink) 70%, transparent); }
.md code { font-family: ui-monospace, 'IBM Plex Mono', monospace; font-size: 0.85em; background: var(--color-panel); padding: 0.1em 0.35em; border-radius: 4px; }
.md pre { background: var(--color-panel); padding: 0.9em 1em; border-radius: 8px; overflow-x: auto; }
.md pre code { background: none; padding: 0; }
.md table { border-collapse: collapse; width: 100%; font-size: 0.85em; }
.md th, .md td { border: 1px solid color-mix(in srgb, var(--color-ink) 15%, transparent); padding: 0.4em 0.6em; text-align: left; }
.md img { max-width: 100%; border-radius: 8px; }
.md hr { border: 0; border-top: 1px dashed color-mix(in srgb, var(--color-ink) 20%, transparent); }
.md input[type='checkbox'] { margin-right: 0.4em; accent-color: var(--color-ink); }
</style>
