<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import type { Browse, FolderRef, SpaceId } from './drive'

/** Pick a destination folder in a space by walking down from its root. */
const props = defineProps<{ open: boolean; space: SpaceId; exclude?: number }>()
const emit = defineEmits<{ close: []; pick: [folder: number | null] }>()
const here = ref<FolderRef | null>(null)
const folders = ref<FolderRef[]>([])
async function go(id: number | null) {
  const { data } = await api.get<Browse>('drive/browse/', { params: { space: props.space, folder: id ?? undefined } })
  here.value = data.folder
  folders.value = data.folders.filter((f) => f.id !== props.exclude)
}
watch(() => props.open, (o) => o && go(null))
</script>

<template>
  <Modal :open="open" title="Move to…" @close="emit('close')">
    <nav class="mb-3 flex flex-wrap items-center gap-1 text-sm" aria-label="Folder path">
      <button type="button" class="hover:underline" @click="go(null)">Top</button>
      <template v-for="p in here?.path || []" :key="p.id"><span class="text-ink/40">/</span><button type="button" class="hover:underline" @click="go(p.id)">{{ p.name }}</button></template>
    </nav>
    <ul class="max-h-72 divide-y divide-ink/10 overflow-y-auto rounded-lg border border-ink/10">
      <li v-for="f in folders" :key="f.id"><button type="button" class="w-full px-3 py-2 text-left text-sm hover:bg-panel/60" @click="go(f.id)">{{ f.name }} <span class="text-ink/40">›</span></button></li>
      <li v-if="!folders.length" class="px-3 py-2 text-sm text-ink/55">No subfolders.</li>
    </ul>
    <button class="btn-ink mt-4 w-full" @click="emit('pick', here?.id ?? null)">Move here{{ here ? ` (${here.name})` : ' (top level)' }}</button>
  </Modal>
</template>
