<script setup lang="ts">
/** Create / edit / complete sprint dialogs, opened through `ws.openSprint(mode, sprint)`. */
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../../ui/Modal.vue'
import { dayNum, todayNPT, ymdOf } from '../pm'
import { categoryOf } from './meta'
import { useWorkspace } from './workspace'

const ws = useWorkspace()
const d = ws.sprintDialog
const form = reactive({ name: '', goal: '', start_date: '', end_date: '' })
const weeks = ref(2)
const carryTo = ref<number | null>(null)
const busy = ref(false)
const open = computed(() => d.mode === 'create' || d.mode === 'edit')
const sprintTasks = computed(() => (d.sprint ? ws.work.filter((t) => t.sprint === d.sprint!.id) : []))
const unfinished = computed(() => sprintTasks.value.filter((t) => categoryOf(t.status) !== 'done'))
const finished = computed(() => sprintTasks.value.length - unfinished.value.length)
const planned = computed(() => ws.sprints.filter((s) => s.status === 'planned'))
watch(
  () => d.mode,
  (mode) => {
    if (mode === 'create') {
      const last = ws.sprints[ws.sprints.length - 1]
      const start = last ? Math.max(dayNum(last.end_date) + 1, dayNum(todayNPT())) : dayNum(todayNPT())
      Object.assign(form, { name: `${ws.project?.key || ''} Sprint ${ws.sprints.length + 1}`.trim(), goal: '', start_date: ymdOf(start), end_date: ymdOf(start + 13) })
      weeks.value = 2
    } else if (mode === 'edit' && d.sprint) {
      const { name, goal, start_date, end_date } = d.sprint
      Object.assign(form, { name, goal, start_date, end_date })
      weeks.value = 0
    } else if (mode === 'complete') carryTo.value = null
  },
)
watch(weeks, (w) => {
  if (w && form.start_date) form.end_date = ymdOf(dayNum(form.start_date) + w * 7 - 1)
})
const close = () => Object.assign(d, { mode: null, sprint: null })
async function save() {
  busy.value = true
  const ok = await ws.sprintAction(
    () => (d.mode === 'edit' ? api.patch(`pm/sprints/${d.sprint!.id}/`, form) : api.post('pm/sprints/', { ...form, project: ws.project!.id })),
    d.mode === 'edit' ? 'Sprint updated.' : `${form.name} created.`,
  )
  busy.value = false
  if (ok) close()
}
async function complete() {
  busy.value = true
  const name = d.sprint!.name
  const ok = await ws.sprintAction(() => api.post(`pm/sprints/${d.sprint!.id}/complete/`, { carry_to: carryTo.value }), `${name} completed.`)
  busy.value = false
  if (ok) close()
}
</script>
<template>
  <Modal :open="open" :title="d.mode === 'edit' ? `Edit ${d.sprint?.name}` : 'Create sprint'" @close="close">
    <form class="grid grid-cols-1 gap-4" @submit.prevent="save">
      <label class="field"><span class="ledger-label">Sprint name</span><input v-model="form.name" required maxlength="120" class="input" /></label>
      <label class="field">
        <span class="ledger-label">Duration</span>
        <select v-model.number="weeks" class="input">
          <option :value="1">1 week</option>
          <option :value="2">2 weeks</option>
          <option :value="3">3 weeks</option>
          <option :value="4">4 weeks</option>
          <option :value="0">Custom</option>
        </select>
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"><span class="ledger-label">Start date</span><input v-model="form.start_date" type="date" required class="input" @change="weeks && (form.end_date = ymdOf(dayNum(form.start_date) + weeks * 7 - 1))" /></label>
        <label class="field"><span class="ledger-label">End date</span><input v-model="form.end_date" type="date" required :min="form.start_date" class="input" :disabled="!!weeks" /></label>
      </div>
      <label class="field"><span class="ledger-label">Sprint goal</span><textarea v-model="form.goal" rows="3" class="input" placeholder="What should this sprint deliver?" /></label>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn-ghost" @click="close">Cancel</button>
        <button class="btn-primary" :disabled="busy">{{ d.mode === 'edit' ? 'Update' : 'Create' }}</button>
      </div>
    </form>
  </Modal>
  <Modal :open="d.mode === 'complete'" :title="`Complete ${d.sprint?.name || 'sprint'}`" @close="close">
    <div class="grid grid-cols-1 gap-4 text-sm">
      <p>This sprint contains <strong>{{ finished }} completed</strong> and <strong>{{ unfinished.length }} open</strong> issue{{ unfinished.length === 1 ? '' : 's' }}.</p>
      <label v-if="unfinished.length" class="field">
        <span class="ledger-label">Move open issues to</span>
        <select v-model="carryTo" class="input">
          <option :value="null">Backlog</option>
          <option v-for="s in planned" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </label>
      <p v-else class="text-moss">Every issue is done. Nice work.</p>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn-ghost" @click="close">Cancel</button>
        <button class="btn-primary" :disabled="busy" @click="complete">Complete sprint</button>
      </div>
    </div>
  </Modal>
</template>
