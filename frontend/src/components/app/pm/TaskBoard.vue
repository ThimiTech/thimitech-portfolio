<script setup lang="ts">
import { computed, ref } from 'vue'
import { dateLabel, isOverdue, type Board, type Task } from './pm'
const props = defineProps<{
  board: Board
  tasks: Task[]
  canManage: boolean
  userId?: number
  busy: boolean
}>()
const emit = defineEmits<{
  select: [task: Task]
  move: [task: Task, column: number]
  create: [column: number]
}>()
const dragging = ref<number | null>(null)
const over = ref<number | null>(null)
const byColumn = computed(
  () =>
    new Map(props.board.columns.map((c) => [c.id, props.tasks.filter((t) => t.column === c.id)])),
)
function movable(task: Task) {
  return !props.busy && (props.canManage || task.assignee === props.userId)
}
function startDrag(task: Task, event: DragEvent) {
  dragging.value = task.id
  event.dataTransfer?.setData('text/plain', String(task.id))
}
function endDrag() {
  dragging.value = null
  over.value = null
}
function drop(column: number) {
  const task = props.tasks.find((t) => t.id === dragging.value)
  if (task && movable(task) && task.column !== column) emit('move', task, column)
  dragging.value = null
  over.value = null
}
</script>

<template>
  <div
    class="grid grid-cols-1 items-start gap-4 md:grid-cols-2 xl:grid-cols-4"
    aria-label="Task board"
    :aria-busy="busy"
  >
    <section
      v-for="column in board.columns"
      :key="column.id"
      class="min-w-0 rounded-xl border border-ink/10 bg-panel/40 p-3 transition-colors"
      :class="over === column.id ? 'ring-2 ring-river/50' : ''"
      @dragover.prevent="over = column.id"
      @dragleave.self="over = null"
      @drop.prevent="drop(column.id)"
    >
      <header class="mb-4 flex items-center justify-between gap-2 px-1">
        <h3 class="text-sm font-medium">
          {{ column.name }}
          <span class="ml-2 font-mono text-xs text-ink/50">{{
            byColumn.get(column.id)?.length
          }}</span>
        </h3>
        <button
          v-if="canManage"
          :aria-label="`Add task to ${column.name}`"
          class="rounded px-2 py-1 text-ink/65 hover:bg-paper"
          @click="emit('create', column.id)"
        >
          +
        </button>
      </header>
      <div class="grid min-h-16 gap-3">
        <article
          v-for="task in byColumn.get(column.id)"
          :key="task.id"
          :draggable="movable(task)"
          class="rounded-lg border border-ink/10 bg-sheet p-4"
          :class="movable(task) ? 'cursor-grab active:cursor-grabbing' : ''"
          @dragstart="startDrag(task, $event)"
          @dragend="endDrag"
        >
          <div class="mb-3 flex justify-between gap-2 font-mono text-[10px]">
            <span class="text-ink/55">{{ task.key }}</span
            ><span
              :class="['high', 'urgent'].includes(task.priority) ? 'text-rust' : 'text-ink/55'"
              >{{ task.priority }}</span
            >
          </div>
          <button
            class="w-full text-left text-sm font-medium leading-relaxed hover:text-river"
            @click="emit('select', task)"
          >
            {{ task.title }}
          </button>
          <div v-if="task.labels.length" class="mt-3 flex flex-wrap gap-1">
            <span
              v-for="label in task.labels"
              :key="label"
              class="rounded border border-ink/10 px-1.5 py-0.5 text-[10px] text-ink/65"
              >{{ label }}</span
            >
          </div>
          <div
            class="mt-4 flex items-center justify-between gap-2 border-t border-ink/10 pt-3 text-[11px] text-ink/60"
          >
            <span class="truncate">{{ task.assignee_name || 'Unassigned' }}</span
            ><span v-if="task.estimate !== null" class="shrink-0 font-mono"
              >{{ task.estimate }} pt</span
            >
          </div>
          <p
            v-if="task.due_date"
            class="mt-2 text-[11px]"
            :class="isOverdue(task) ? 'text-rust' : 'text-ink/60'"
          >
            {{ isOverdue(task) ? 'Overdue · ' : '' }}{{ dateLabel(task.due_date) }}
          </p>
        </article>
        <p v-if="!byColumn.get(column.id)?.length" class="px-1 py-5 text-xs text-ink/55">
          No tasks here yet.
        </p>
      </div>
    </section>
  </div>
</template>
