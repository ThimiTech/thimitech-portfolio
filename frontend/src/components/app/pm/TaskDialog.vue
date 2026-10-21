<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../ui/Modal.vue'
import { useAuth } from '@/stores/auth'
import { confirmDialog } from '../ui/confirm'
import { errorMessage, type Project, type Task, type Milestone, type Comment } from './pm'
const props = defineProps<{
  open: boolean
  project: Project
  task: Task | null
  column: number
  milestones: Milestone[]
}>()
const emit = defineEmits<{ close: []; saved: [] }>()
const { user } = useAuth()
const saving = ref(false)
const error = ref('')
const comments = ref<Comment[]>([])
const commentsError = ref('')
const commentsLoading = ref(false)
const comment = ref('')
const posting = ref(false)
const form = reactive({
  title: '',
  description: '',
  column: 0,
  assignee: null as number | null,
  priority: 'medium',
  estimate: null as number | null,
  labels: '',
  milestone: null as number | null,
  start_date: '',
  due_date: '',
})
const columns = computed(
  () =>
    props.project.boards.find((b) => b.columns.some((c) => c.id === form.column))?.columns || [],
)
const canMove = computed(() => props.project.can_manage || props.task?.assignee === user.value?.id)
async function loadComments() {
  commentsLoading.value = true
  commentsError.value = ''
  try {
    comments.value = (
      await api.get<Comment[]>('pm/comments/', { params: { task: props.task!.id } })
    ).data
  } catch {
    commentsError.value = 'Could not load comments.'
  } finally {
    commentsLoading.value = false
  }
}
watch(
  () => props.open,
  async (open) => {
    if (!open) return
    error.value = ''
    comment.value = ''
    comments.value = []
    commentsError.value = ''
    const t = props.task
    Object.assign(form, {
      title: t?.title || '',
      description: t?.description || '',
      column: t?.column || props.column,
      assignee: t?.assignee ?? null,
      priority: t?.priority || 'medium',
      estimate: t?.estimate ?? null,
      labels: t?.labels.join(', ') || '',
      milestone: t?.milestone ?? null,
      start_date: t?.start_date || '',
      due_date: t?.due_date || '',
    })
    if (t) await loadComments()
  },
)
async function save() {
  saving.value = true
  error.value = ''
  try {
    const payload = props.project.can_manage
      ? {
          ...form,
          labels: form.labels
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
          start_date: form.start_date || null,
          due_date: form.due_date || null,
          estimate:
            form.estimate === null || String(form.estimate) === '' ? null : Number(form.estimate),
        }
      : { column: form.column }
    if (props.task) await api.patch(`pm/tasks/${props.task.id}/`, payload)
    else await api.post('pm/tasks/', payload)
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
async function postComment() {
  if (!comment.value.trim()) return
  posting.value = true
  commentsError.value = ''
  try {
    await api.post('pm/comments/', { task: props.task!.id, body: comment.value })
    comment.value = ''
    await loadComments()
  } catch (e) {
    commentsError.value = errorMessage(e)
  } finally {
    posting.value = false
  }
}
async function remove() {
  if (
    !(await confirmDialog({
      title: 'Delete task?',
      body: 'This also removes its comments.',
      confirmLabel: 'Delete task',
      danger: true,
    }))
  )
    return
  saving.value = true
  try {
    await api.delete(`pm/tasks/${props.task!.id}/`)
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>
<template>
  <Modal
    :open="open"
    :title="task ? task.key : 'New task'"
    width="max-w-2xl"
    @close="emit('close')"
  >
    <form class="grid gap-4" @submit.prevent="save">
      <label class="field"
        ><span class="ledger-label">Title</span
        ><input
          v-model="form.title"
          class="input"
          required
          maxlength="200"
          :readonly="!project.can_manage"
      /></label>
      <label class="field"
        ><span class="ledger-label">Description</span
        ><textarea
          v-model="form.description"
          class="input"
          rows="3"
          :readonly="!project.can_manage"
        />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Status</span
          ><select v-model="form.column" class="input" :disabled="!canMove">
            <option v-for="c in columns" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Assignee</span
          ><select v-model="form.assignee" class="input" :disabled="!project.can_manage">
            <option :value="null">Unassigned</option>
            <option v-for="p in project.people" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select></label
        >
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Priority</span
          ><select v-model="form.priority" class="input" :disabled="!project.can_manage">
            <option v-for="p in ['low', 'medium', 'high', 'urgent']" :key="p">{{ p }}</option>
          </select></label
        ><label class="field"
          ><span class="ledger-label">Estimate (points)</span
          ><input
            v-model="form.estimate"
            class="input"
            type="number"
            min="0"
            max="32767"
            :readonly="!project.can_manage"
        /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label class="field"
          ><span class="ledger-label">Start date</span
          ><input
            v-model="form.start_date"
            class="input"
            type="date"
            :readonly="!project.can_manage" /></label
        ><label class="field"
          ><span class="ledger-label">Due date</span
          ><input
            v-model="form.due_date"
            class="input"
            type="date"
            :min="form.start_date"
            :readonly="!project.can_manage"
        /></label>
      </div>
      <label class="field"
        ><span class="ledger-label">Labels (comma separated)</span
        ><input v-model="form.labels" class="input" :readonly="!project.can_manage"
      /></label>
      <label class="field"
        ><span class="ledger-label">Milestone</span
        ><select v-model="form.milestone" class="input" :disabled="!project.can_manage">
          <option :value="null">No milestone</option>
          <option v-for="m in milestones" :key="m.id" :value="m.id">{{ m.title }}</option>
        </select></label
      >
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <div class="flex justify-between gap-3">
        <button
          v-if="task && project.can_manage"
          type="button"
          class="btn-danger btn-sm"
          :disabled="saving"
          @click="remove"
        >
          Delete task</button
        ><button v-if="canMove" class="btn-ink ml-auto" :disabled="saving">
          {{ saving ? 'Saving…' : task ? 'Save changes' : 'Create task' }}
        </button>
      </div>
    </form>
    <section v-if="task" class="mt-7 border-t border-ink/15 pt-5" aria-label="Task comments">
      <h3 class="text-sm font-medium">Discussion</h3>
      <p v-if="commentsLoading" class="mt-4 text-sm text-ink/60">Loading discussion…</p>
      <p v-else-if="!comments.length && !commentsError" class="mt-4 text-sm text-ink/60">
        No comments yet. Add context for your team.
      </p>
      <article v-for="c in comments" :key="c.id" class="mt-4 rounded-lg bg-panel/50 p-3">
        <p class="text-xs font-medium">
          {{ c.author_name }}
          <time class="ml-2 font-normal text-ink/60">{{
            new Date(c.created_at).toLocaleString('en-GB', { timeZone: 'Asia/Kathmandu' })
          }}</time>
        </p>
        <p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{{ c.body }}</p>
      </article>
      <form class="mt-4 grid gap-3" @submit.prevent="postComment">
        <label class="field"
          ><span class="ledger-label">Add comment</span
          ><textarea v-model="comment" class="input" rows="2" required maxlength="10000" />
        </label>
        <p v-if="commentsError" role="alert" class="text-sm text-rust">
          {{ commentsError }}
          <button type="button" class="underline" @click="loadComments">Retry</button>
        </p>
        <button class="btn-ghost justify-self-end" :disabled="posting || !comment.trim()">
          {{ posting ? 'Posting…' : 'Post comment' }}
        </button>
      </form>
    </section>
  </Modal>
</template>
