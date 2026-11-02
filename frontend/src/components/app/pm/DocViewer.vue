<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Modal from '../ui/Modal.vue'
import MarkdownView from './MarkdownView.vue'
import { downloadDoc, fetchBlob, fileSize, previewKind, type Doc } from './pm'
const props = defineProps<{ doc: Doc | null }>()
const emit = defineEmits<{ close: []; wikilink: [target: string] }>()
const src = ref('')
const text = ref('')
const loading = ref(false)
const error = ref('')
const kind = computed(() => (props.doc ? previewKind(props.doc.extension) : null))
const csv = computed(() =>
  props.doc?.extension === 'csv'
    ? text.value
        .split(/\r?\n/)
        .filter(Boolean)
        .slice(0, 500)
        .map((l) => l.split(','))
    : null,
)
function clear() {
  if (src.value) URL.revokeObjectURL(src.value)
  src.value = ''
  text.value = ''
}
watch(
  () => props.doc,
  async (doc) => {
    clear()
    error.value = ''
    if (!doc || !kind.value) return
    loading.value = true
    try {
      const blob = await fetchBlob(doc.url)
      if (kind.value === 'markdown' || kind.value === 'text') text.value = await blob.text()
      else src.value = URL.createObjectURL(kind.value === 'pdf' ? new Blob([blob], { type: 'application/pdf' }) : blob)
    } catch {
      error.value = 'Could not load this document.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
onBeforeUnmount(clear)
</script>
<template>
  <Modal :open="!!doc" :title="doc?.title || ''" width="max-w-5xl" @close="emit('close')">
    <template v-if="doc">
      <div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink/60">
        <span class="font-mono uppercase">{{ doc.extension }} · {{ fileSize(doc.size) }}</span>
        <span>{{ doc.folder || 'Unfiled' }}</span>
        <span>Uploaded by {{ doc.uploaded_by_name }}</span>
        <span v-if="doc.public" class="text-moss">Public</span>
        <button class="btn-ghost btn-sm ml-auto" @click="downloadDoc(doc)">Download</button>
      </div>
      <p v-if="doc.description" class="mb-4 text-sm text-ink/70">{{ doc.description }}</p>
      <div v-if="loading" class="h-[60vh] rounded-lg bg-panel/70 motion-safe:animate-pulse" aria-busy="true" />
      <p v-else-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <iframe v-else-if="kind === 'pdf'" :src="src" :title="doc.title" class="h-[70vh] w-full rounded-lg border border-ink/10 bg-paper" />
      <img v-else-if="kind === 'image'" :src="src" :alt="doc.title" class="mx-auto max-h-[70vh] rounded-lg object-contain" />
      <div v-else-if="kind === 'markdown'" class="max-h-[70vh] overflow-y-auto rounded-lg border border-ink/10 bg-paper p-6">
        <MarkdownView :source="text" @wikilink="emit('wikilink', $event)" />
      </div>
      <div v-else-if="csv" class="max-h-[70vh] overflow-auto rounded-lg border border-ink/10">
        <table class="ledger-table">
          <thead><tr><th v-for="(h, i) in csv[0]" :key="i">{{ h }}</th></tr></thead>
          <tbody><tr v-for="(r, i) in csv.slice(1)" :key="i"><td v-for="(c, j) in r" :key="j">{{ c }}</td></tr></tbody>
        </table>
      </div>
      <pre v-else-if="kind === 'text'" class="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-lg bg-panel/60 p-5 font-mono text-xs">{{ text }}</pre>
      <div v-else class="grid place-items-center rounded-lg border border-dashed border-ink/20 p-12 text-center text-sm text-ink/60">
        <div>
          <p>{{ doc.extension.toUpperCase() }} files can't be previewed in the browser.</p>
          <button class="btn-ink mt-4" @click="downloadDoc(doc)">Download {{ doc.file }}</button>
        </div>
      </div>
    </template>
  </Modal>
</template>
