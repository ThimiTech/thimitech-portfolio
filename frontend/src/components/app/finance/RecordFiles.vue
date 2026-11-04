<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/api'
import DocViewer from '../pm/DocViewer.vue'
import { fileSize, errorMessage, type Doc } from '../pm/pm'
import { asDoc, fileBadge, uploadFile, type Browse, type DriveFile } from '../drive/drive'
import { toast } from '../ui/toast'

/** Files linked to one record (a bank line, claim, statement…), stored in the drive under `folder`. */
const props = defineProps<{ link: Record<string, number>; space?: 'finance' | 'company'; folder: string; fiscalYear?: string; readonly?: boolean }>()
const files = ref<DriveFile[]>([])
const busy = ref(false)
const viewing = ref<Doc | null>(null)
async function load() {
  files.value = (await api.get<Browse>('drive/browse/', { params: props.link })).data.files
}
onMounted(() => load().catch(() => {}))
async function add(e: Event) {
  const input = e.target as HTMLInputElement
  busy.value = true
  try {
    for (const f of Array.from(input.files || []))
      await uploadFile(f, { space: props.space || 'finance', relative_path: `${props.folder}/${f.name}`, fiscal_year: props.fiscalYear, ...props.link })
    await load()
  } catch (err) {
    toast.error(errorMessage(err))
  } finally {
    busy.value = false
    input.value = ''
  }
}
</script>

<template>
  <div>
    <ul v-if="files.length" class="grid gap-1.5">
      <li v-for="f in files" :key="f.id" class="flex items-center gap-2 rounded-lg border border-ink/10 px-2.5 py-1.5 text-sm">
        <span class="rounded bg-ink/[0.06] px-1.5 py-0.5 font-mono text-[10px]">{{ fileBadge(f.extension) }}</span>
        <button type="button" class="min-w-0 flex-1 truncate text-left hover:underline" @click="viewing = asDoc(f)">{{ f.name }}</button>
        <span class="text-xs text-ink/50">{{ fileSize(f.size) }}</span>
      </li>
    </ul>
    <p v-else class="text-xs text-ink/55">No files attached.</p>
    <label v-if="!readonly" class="btn-ghost btn-sm mt-2 inline-flex cursor-pointer">
      {{ busy ? 'Uploading…' : '+ Attach receipt / document' }}
      <input type="file" multiple class="sr-only" :disabled="busy" @change="add" />
    </label>
    <DocViewer :doc="viewing" @close="viewing = null" />
  </div>
</template>
