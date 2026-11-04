<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { toast } from '../ui/toast'
import { errorMessage } from '../pm/pm'
import { dateLabel } from '../finance/finance'
import type { ShareLink } from './drive'

/** Expiring read-only link for someone without an account (the CA, a bank, an auditor). */
const props = defineProps<{ target: { folder?: number; file?: number; name: string } | null }>()
const emit = defineEmits<{ close: [] }>()
const label = ref('')
const days = ref(14)
const links = ref<ShareLink[]>([])
const error = ref('')
const url = (t: string) => `${location.origin}/s/${t}`
async function load() {
  const all = (await api.get<ShareLink[]>('drive/share-links/')).data
  links.value = all.filter((l) => (props.target?.folder ? l.folder === props.target.folder : l.file === props.target?.file))
}
watch(() => props.target, (t) => {
  if (!t) return
  label.value = ''
  days.value = 14
  error.value = ''
  load().catch(() => {})
})
async function create() {
  try {
    const { data } = await api.post<ShareLink>('drive/share-links/', { ...(props.target!.folder ? { folder: props.target!.folder } : { file: props.target!.file }), label: label.value, days: days.value })
    await navigator.clipboard?.writeText(url(data.token)).catch(() => {})
    toast.success('Link created and copied')
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}
async function revoke(l: ShareLink) {
  await api.delete(`drive/share-links/${l.id}/`)
  await load()
}
function copy(l: ShareLink) {
  navigator.clipboard?.writeText(url(l.token)).then(() => toast.success('Link copied'), () => toast.error('Copy failed; select the link and copy it.'))
}
</script>

<template>
  <Modal :open="!!target" :title="target ? `Share “${target.name}”` : ''" @close="emit('close')">
    <div class="grid gap-4">
      <p class="text-sm text-ink/65">Anyone with the link can view and download {{ target?.folder ? 'this folder (and its subfolders)' : 'this file' }} until it expires. No sign-in needed. Revoke any time.</p>
      <form class="grid grid-cols-[1fr_auto_auto] items-end gap-2" @submit.prevent="create">
        <label class="field"><span class="ledger-label">For</span><input v-model="label" class="input" maxlength="120" placeholder="e.g. CA · FY 2081/82 audit" /></label>
        <label class="field"><span class="ledger-label">Days</span><input v-model.number="days" type="number" min="1" max="90" class="input w-20" /></label>
        <button class="btn-ink">Create link</button>
      </form>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <ul v-if="links.length" class="grid gap-2">
        <li v-for="l in links" :key="l.id" class="rounded-lg border border-ink/10 px-3 py-2 text-sm" :class="!l.active && 'opacity-50'">
          <div class="flex flex-wrap items-center gap-2">
            <span class="min-w-0 flex-1 truncate">{{ l.label || 'Untitled link' }}</span>
            <span class="text-xs text-ink/55">{{ l.revoked_at ? 'revoked' : l.active ? 'until ' + dateLabel(l.expires_at) : 'expired' }}</span>
            <button v-if="l.active" class="btn-ghost btn-sm" @click="copy(l)">Copy</button>
            <button v-if="l.active" class="btn-danger btn-sm" @click="revoke(l)">Revoke</button>
          </div>
          <code v-if="l.active" class="mt-1 block truncate text-[11px] text-ink/55">{{ url(l.token) }}</code>
        </li>
      </ul>
    </div>
  </Modal>
</template>
