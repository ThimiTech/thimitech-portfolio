<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/api'
import DocViewer from '@/components/app/pm/DocViewer.vue'
import { downloadDoc, fileSize, type Doc } from '@/components/app/pm/pm'
import { asDoc, BADGE_TONE, fileBadge } from '@/components/app/drive/drive'
import { dateLabel, saveBlob } from '@/components/app/finance/finance'

interface SharedFile { id: number; name: string; extension: string; size: number; path: string; fiscal_year: string; description: string; url: string }
const route = useRoute()
const token = String(route.params.token)
const data = ref<{ label: string; name: string; expires_at: string; files: SharedFile[] } | null>(null)
const error = ref('')
const viewing = ref<Doc | null>(null)
const zipping = ref(false)
onMounted(async () => {
  try {
    data.value = (await api.get(`drive/shared/${token}/`)).data
  } catch {
    error.value = 'This link has expired, was revoked, or never existed. Ask the sender for a new one.'
  }
})
const groups = computed(() => {
  const m = new Map<string, SharedFile[]>()
  for (const f of data.value?.files || []) m.set(f.path, [...(m.get(f.path) || []), f])
  return [...m.entries()].sort(([a], [b]) => a.localeCompare(b))
})
const total = computed(() => (data.value?.files || []).reduce((s, f) => s + f.size, 0))
async function zip() {
  zipping.value = true
  try {
    saveBlob((await api.get<Blob>(`drive/shared/${token}/zip/`, { responseType: 'blob' })).data, `${data.value?.name || 'shared'}.zip`)
  } finally {
    zipping.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-paper px-4 py-10 text-ink">
    <div class="mx-auto max-w-4xl">
      <p class="ledger-label">Thimi Tech Pvt. Ltd. · shared files</p>
      <p v-if="error" class="panel mt-6 p-6 text-sm text-rust">{{ error }}</p>
      <template v-else-if="data">
        <div class="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 class="font-display text-3xl font-medium">{{ data.name }}</h1>
            <p class="mt-1 text-sm text-ink/60">{{ data.label ? data.label + ' · ' : '' }}{{ data.files.length }} files · {{ fileSize(total) }} · available until {{ dateLabel(data.expires_at) }}</p>
          </div>
          <button v-if="data.files.length > 1" class="btn-ink" :disabled="zipping" @click="zip">{{ zipping ? 'Preparing…' : 'Download all (.zip)' }}</button>
        </div>
        <section v-for="[path, files] in groups" :key="path" class="mt-6">
          <h2 v-if="path" class="ledger-label mb-2">{{ path }}</h2>
          <ul class="panel divide-y divide-ink/10">
            <li v-for="f in files" :key="f.id" class="flex flex-wrap items-center gap-3 px-4 py-2.5">
              <span class="rounded px-1.5 py-0.5 font-mono text-[10px]" :class="BADGE_TONE[fileBadge(f.extension)] || 'bg-ink/[0.06]'">{{ fileBadge(f.extension) }}</span>
              <button type="button" class="min-w-0 flex-1 truncate text-left text-sm hover:underline" @click="viewing = asDoc(f)">{{ f.name }}</button>
              <span v-if="f.fiscal_year" class="font-mono text-[11px] text-ink/50">FY {{ f.fiscal_year }}</span>
              <span class="text-xs text-ink/50">{{ fileSize(f.size) }}</span>
              <button class="btn-ghost btn-sm" @click="downloadDoc(asDoc(f))">Download</button>
            </li>
          </ul>
        </section>
      </template>
      <p v-else class="mt-6 text-sm text-ink/60">Loading…</p>
    </div>
    <DocViewer :doc="viewing" @close="viewing = null" />
  </main>
</template>
