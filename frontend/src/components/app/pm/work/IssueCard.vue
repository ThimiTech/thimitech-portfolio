<script setup lang="ts">
import { computed } from 'vue'
import { dateLabel, isOverdue, type Task } from '../pm'
import Avatar from '../../ui/Avatar.vue'
import TypeIcon from './TypeIcon.vue'
import PriorityIcon from './PriorityIcon.vue'
import ParentChip from './ParentChip.vue'
import { nearest } from './meta'
import { useWorkspace } from './workspace'
const props = defineProps<{ task: Task; dragging?: boolean }>()
const ws = useWorkspace()
const parent = computed(() => nearest(props.task, ws.byId, 'epic') || nearest(props.task, ws.byId, 'module'))
const done = computed(() => props.task.status === 'done')
</script>
<template>
  <article
    class="group cursor-pointer rounded-lg border bg-sheet p-3 shadow-[0_1px_1px_rgba(26,26,26,0.06)] transition hover:bg-paper"
    :class="[dragging ? 'opacity-40' : '', ws.blocked(task) ? 'border-rust/40' : 'border-ink/10']"
    @click="ws.openIssue(task)"
  >
    <RouterLink :to="ws.linkOf(task)" draggable="false" @click.stop class="block text-sm leading-snug hover:text-river focus-visible:underline focus-visible:outline-none" :class="done ? 'text-ink/60' : ''">
      <span class="line-clamp-3 break-words">{{ task.title }}</span>
    </RouterLink>
    <div v-if="parent || task.labels.length" class="mt-2 flex min-w-0 flex-wrap gap-1">
      <ParentChip v-if="parent" :item="parent" />
      <span v-for="l in task.labels.slice(0, 2)" :key="l" class="max-w-[8rem] truncate rounded border border-ink/10 px-1.5 py-0.5 text-[10px] text-ink/60">{{ l }}</span>
    </div>
    <p v-if="ws.blocked(task)" class="mt-2 truncate text-[11px] font-medium text-rust" :title="task.blocker || 'Blocked by another issue'">⚠ {{ task.blocker || 'Blocked' }}</p>
    <div class="mt-3 flex items-center gap-2">
      <TypeIcon :type="task.type" />
      <span class="font-mono text-[11px] text-ink/55" :class="done ? 'line-through' : ''">{{ task.key }}</span>
      <span v-if="task.due_date && !done" class="text-[11px]" :class="isOverdue(task) ? 'font-medium text-rust' : 'text-ink/50'" :title="`Due ${dateLabel(task.due_date)}`">{{ dateLabel(task.due_date) }}</span>
      <span class="ml-auto flex items-center gap-1.5">
        <span v-if="(task.comment_count || 0) > 0" class="inline-flex items-center gap-0.5 text-[11px] text-ink/50" :title="`${task.comment_count} comments`">
          <svg viewBox="0 0 16 16" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M3 3.5h10v7H7l-3 2.5v-2.5H3z" /></svg>{{ task.comment_count }}
        </span>
        <span v-if="task.estimate !== null" class="grid grid-cols-1 h-5 min-w-5 place-items-center rounded-full bg-ink/[0.07] px-1.5 font-mono text-[10.5px] text-ink/70" :title="`${task.estimate} story points`">{{ task.estimate }}</span>
        <PriorityIcon :priority="task.priority" />
        <Avatar v-if="task.assignee_name" :name="task.assignee_name" :size="22" />
      </span>
    </div>
  </article>
</template>
