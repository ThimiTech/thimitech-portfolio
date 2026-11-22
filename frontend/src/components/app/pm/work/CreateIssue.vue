<script setup lang="ts">
/** The workspace's "Create" dialog (button in the header, or press C). */
import { computed, reactive, ref, watch } from 'vue'
import Modal from '../../ui/Modal.vue'
import { toast } from '../../ui/toast'
import type { ItemType } from '../plan'
import TypeIcon from './TypeIcon.vue'
import { PRIORITIES, PRIORITY_META, TYPE_META, parentOptions } from './meta'
import { useWorkspace } from './workspace'

const ws = useWorkspace()
const blank = () => ({
  type: 'story' as ItemType,
  title: '',
  description: '',
  parent: null as number | null,
  assignee: null as number | null,
  priority: 'medium',
  estimate: '' as string | number,
  sprint: null as number | null,
  labels: '',
  start_date: '',
  due_date: '',
})
const form = reactive(blank())
const another = ref(false)
const busy = ref(false)
const parents = computed(() => parentOptions(form.type, ws.tasks))
const container = computed(() => form.type === 'module' || form.type === 'epic')
watch(
  () => ws.creating.open,
  (open) => {
    if (!open) return
    Object.assign(form, blank(), Object.fromEntries(Object.entries(ws.creating.defaults).filter(([, v]) => v !== undefined)))
  },
)
watch(
  () => form.type,
  () => {
    if (form.parent && !parents.value.some((p) => p.id === form.parent)) form.parent = null
    if (form.type === 'module' || form.type === 'epic') form.sprint = null
  },
)
async function submit() {
  busy.value = true
  const made = await ws.create({
    ...form,
    title: form.title.trim(),
    estimate: form.estimate === '' ? null : Number(form.estimate),
    labels: form.labels.split(',').map((s) => s.trim()).filter(Boolean),
    start_date: form.start_date || null,
    due_date: form.due_date || null,
  })
  busy.value = false
  if (!made) return
  toast.success(`${made.key} created.`)
  if (another.value) Object.assign(form, { title: '', description: '', estimate: '' })
  else {
    ws.creating.open = false
    if (made.type === 'module' || made.type === 'epic') ws.go(made)
  }
}
</script>
<template>
  <Modal :open="ws.creating.open" title="Create issue" width="max-w-2xl" @close="ws.creating.open = false">
    <form class="grid grid-cols-1 gap-4" @submit.prevent="submit">
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="field">
          <span class="ledger-label">Issue type</span>
          <span class="relative">
            <TypeIcon :type="form.type" class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2" />
            <select v-model="form.type" class="input !pl-9">
              <option v-for="(m, k) in TYPE_META" :key="k" :value="k">{{ m.label }}</option>
            </select>
          </span>
        </label>
        <label v-if="form.type !== 'module'" class="field">
          <span class="ledger-label">Parent</span>
          <select v-model="form.parent" class="input">
            <option :value="null">None</option>
            <option v-for="p in parents" :key="p.id" :value="p.id">{{ TYPE_META[p.type].label }} · {{ p.key }} {{ p.title }}</option>
          </select>
        </label>
      </div>
      <label class="field">
        <span class="ledger-label">Summary <span class="text-rust" aria-hidden="true">*</span></span>
        <input v-model="form.title" class="input" required maxlength="200" />
      </label>
      <label class="field">
        <span class="ledger-label">Description</span>
        <textarea v-model="form.description" class="input" rows="4" placeholder="Markdown supported" />
      </label>
      <div class="grid gap-3 sm:grid-cols-3">
        <label class="field">
          <span class="ledger-label">Assignee</span>
          <select v-model="form.assignee" class="input">
            <option :value="null">Unassigned</option>
            <option v-for="p in ws.people" :key="p.id" :value="p.id">{{ p.name }}{{ p.id === ws.me ? ' (me)' : '' }}</option>
          </select>
        </label>
        <label class="field">
          <span class="ledger-label">Priority</span>
          <select v-model="form.priority" class="input">
            <option v-for="p in PRIORITIES" :key="p" :value="p">{{ PRIORITY_META[p]!.label }}</option>
          </select>
        </label>
        <label v-if="!container" class="field">
          <span class="ledger-label">Story points</span>
          <input v-model="form.estimate" class="input" type="number" min="0" max="999" />
        </label>
      </div>
      <div class="grid gap-3 sm:grid-cols-3">
        <label v-if="!container" class="field">
          <span class="ledger-label">Sprint</span>
          <select v-model="form.sprint" class="input">
            <option :value="null">Backlog</option>
            <option v-for="s in ws.openSprints" :key="s.id" :value="s.id">{{ s.name }}{{ s.status === 'active' ? ' (active)' : '' }}</option>
          </select>
        </label>
        <label class="field">
          <span class="ledger-label">Start date</span>
          <input v-model="form.start_date" class="input" type="date" />
        </label>
        <label class="field">
          <span class="ledger-label">Due date</span>
          <input v-model="form.due_date" class="input" type="date" :min="form.start_date" />
        </label>
      </div>
      <label class="field">
        <span class="ledger-label">Labels (comma separated)</span>
        <input v-model="form.labels" class="input" placeholder="e.g. backend, gis" />
      </label>
      <div class="flex flex-wrap items-center justify-end gap-3 border-t border-dashed border-ink/15 pt-4">
        <label class="mr-auto flex items-center gap-2 text-sm text-ink/70"><input v-model="another" type="checkbox" class="accent-ink" /> Create another</label>
        <button type="button" class="btn-ghost" @click="ws.creating.open = false">Cancel</button>
        <button class="btn-primary" :disabled="busy || !form.title.trim()">{{ busy ? 'Creating…' : 'Create' }}</button>
      </div>
    </form>
  </Modal>
</template>
