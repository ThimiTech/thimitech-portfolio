<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '@/api/api'
import { errorMessage, type Project, type Column } from './pm'
const props = defineProps<{ project: Project }>()
const emit = defineEmits<{ saved: [] }>()
const form = reactive({
  name: props.project.name,
  description: props.project.description,
  start_date: props.project.start_date || '',
  due_date: props.project.due_date || '',
  members: [...props.project.members],
  archived: props.project.archived,
})
const people = ref<{ id: number; full_name: string; email: string }[]>([])
const error = ref('')
const message = ref('')
const busy = ref(false)
const peopleError = ref(false)
const boardName = ref('')
const columnName = ref('')
const columnBoard = ref(props.project.boards[0]?.id || 0)
const columnStatus = ref('backlog')
async function loadPeople() {
  peopleError.value = false
  try {
    people.value = (await api.get('org/people/')).data
  } catch {
    peopleError.value = true
  }
}
async function run(action: () => Promise<unknown>, success: string) {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await action()
    emit('saved')
    message.value = success
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
function save() {
  return run(
    () =>
      api.patch(`pm/projects/${props.project.id}/`, {
        ...form,
        start_date: form.start_date || null,
        due_date: form.due_date || null,
      }),
    'Project saved.',
  )
}
async function addBoard() {
  await run(
    () => api.post('pm/boards/', { project: props.project.id, name: boardName.value }),
    'Board added.',
  )
  if (!error.value) boardName.value = ''
}
async function addColumn() {
  await run(
    () =>
      api.post('pm/columns/', {
        board: columnBoard.value,
        name: columnName.value,
        status: columnStatus.value,
        position: props.project.boards.find((b) => b.id === columnBoard.value)?.columns.length || 0,
      }),
    'Column added.',
  )
  if (!error.value) columnName.value = ''
}
function renameColumn(column: Column, event: Event) {
  const name = (event.target as HTMLInputElement).value.trim()
  if (name && name !== column.name)
    run(() => api.patch(`pm/columns/${column.id}/`, { name }), 'Column renamed.')
}
onMounted(loadPeople)
</script>
<template>
  <div class="grid items-start gap-6 lg:grid-cols-2">
    <form class="panel grid gap-4 p-5" @submit.prevent="save">
      <h3 class="font-medium">Project & team</h3>
      <label class="field"
        ><span class="ledger-label">Project name</span
        ><input v-model="form.name" required maxlength="200" class="input"
      /></label>
      <label class="field"
        ><span class="ledger-label">Description</span
        ><textarea v-model="form.description" class="input" rows="3" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Start date</span
          ><input v-model="form.start_date" type="date" class="input" /></label
        ><label class="field"
          ><span class="ledger-label">Due date</span
          ><input v-model="form.due_date" type="date" :min="form.start_date" class="input"
        /></label>
      </div>
      <fieldset>
        <legend class="ledger-label mb-3">Project members</legend>
        <p v-if="peopleError" class="text-sm text-rust">
          Could not load staff.
          <button type="button" class="underline" @click="loadPeople">Retry</button>
        </p>
        <div class="grid max-h-52 gap-2 overflow-y-auto">
          <label v-for="p in people" :key="p.id" class="flex items-center gap-2 text-sm"
            ><input
              v-model="form.members"
              type="checkbox"
              :value="p.id"
              :disabled="p.id === project.lead"
              class="accent-ink"
            />{{ p.full_name || p.email }}
            <span v-if="p.id === project.lead" class="text-xs text-ink/60"
              >(project lead)</span
            ></label
          >
        </div>
      </fieldset>
      <label class="flex items-center gap-2 text-sm"
        ><input v-model="form.archived" type="checkbox" class="accent-ink" /> Archive project</label
      >
      <p class="text-xs text-ink/60">
        Archived projects remain accessible and keep their task history.
      </p>
      <button class="btn-ink justify-self-start" :disabled="busy">
        {{ busy ? 'Saving…' : 'Save project' }}
      </button>
    </form>
    <section class="panel grid gap-5 p-5">
      <h3 class="font-medium">Boards & workflow</h3>
      <div v-for="b in project.boards" :key="b.id">
        <h4 class="mb-3 text-sm font-medium">{{ b.name }}</h4>
        <div class="grid gap-2">
          <label
            v-for="c in b.columns"
            :key="c.id"
            class="grid grid-cols-[1fr_auto] items-center gap-2"
            ><span class="sr-only">Rename {{ c.name }}</span
            ><input
              :value="c.name"
              class="input"
              maxlength="80"
              :disabled="busy"
              @change="renameColumn(c, $event)"
            /><span class="w-16 text-right font-mono text-[10px] text-ink/60">{{
              c.status
            }}</span></label
          >
        </div>
      </div>
      <form class="grid gap-3 border-t border-ink/10 pt-4" @submit.prevent="addBoard">
        <label class="field"
          ><span class="ledger-label">New board</span
          ><input v-model="boardName" required maxlength="100" class="input" /></label
        ><button class="btn-ghost justify-self-start" :disabled="busy">Add board</button>
      </form>
      <form class="grid gap-3 border-t border-ink/10 pt-4" @submit.prevent="addColumn">
        <label class="field"
          ><span class="ledger-label">New column name</span
          ><input v-model="columnName" required maxlength="80" class="input" /></label
        ><label class="field"
          ><span class="ledger-label">Board</span
          ><select v-model="columnBoard" class="input" required>
            <option v-for="b in project.boards" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Workflow status</span
          ><select v-model="columnStatus" class="input">
            <option v-for="s in ['backlog', 'active', 'review', 'done']" :key="s">{{ s }}</option>
          </select></label
        ><button class="btn-ghost justify-self-start" :disabled="busy || !columnBoard">
          Add column
        </button>
      </form>
    </section>
    <p v-if="error" role="alert" class="text-sm text-rust lg:col-span-2">{{ error }}</p>
    <p v-if="message" role="status" class="text-sm text-moss lg:col-span-2">{{ message }}</p>
  </div>
</template>
