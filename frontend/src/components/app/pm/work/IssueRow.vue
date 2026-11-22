<script setup lang="ts">
/** One issue as a list row (backlog, sprints, module and epic pages, child issues). */
import { computed } from 'vue'
import type { Task } from '../pm'
import { dateLabel, isOverdue } from '../pm'
import TypeIcon from './TypeIcon.vue'
import PriorityIcon from './PriorityIcon.vue'
import StatusMenu from './StatusMenu.vue'
import PersonMenu from './PersonMenu.vue'
import ParentChip from './ParentChip.vue'
import { nearest } from './meta'
import { useWorkspace } from './workspace'
const props = withDefaults(defineProps<{ task: Task; depth?: number; showParent?: boolean; showDue?: boolean }>(), {
  depth: 0,
  showParent: true,
  showDue: false,
})
const ws = useWorkspace()
const parent = computed(() => (props.showParent ? nearest(props.task, ws.byId, 'epic') || nearest(props.task, ws.byId, 'module') : null))
const done = computed(() => props.task.status === 'done')
</script>
<template>
  <div
    class="group flex min-w-0 items-center gap-2.5 py-2 pr-3 text-sm"
    :style="{ paddingLeft: `${0.75 + depth * 1.5}rem` }"
    @click="ws.go(task)"
  >
    <TypeIcon :type="task.type" />
    <span class="shrink-0 font-mono text-[11px] text-ink/55" :class="done ? 'line-through' : ''">{{ task.key }}</span>
    <RouterLink
      :to="ws.linkOf(task)"
      draggable="false"
      class="min-w-0 flex-1 truncate hover:text-river hover:underline focus-visible:underline focus-visible:outline-none"
      :class="done ? 'text-ink/55' : ''"
      :title="task.title"
      @click.stop
    >
      {{ task.title }}
    </RouterLink>
    <span v-if="ws.blocked(task)" class="shrink-0 text-[11px] font-medium text-rust" :title="task.blocker || 'Blocked by another issue'">⚠ Blocked</span>
    <ParentChip v-if="parent" :item="parent" class="hidden sm:inline-flex" />
    <span v-if="showDue && task.due_date" class="hidden shrink-0 text-[11px] md:inline" :class="isOverdue(task) ? 'text-rust' : 'text-ink/55'">{{ dateLabel(task.due_date) }}</span>
    <span v-if="(task.comment_count || 0) > 0" class="hidden shrink-0 items-center gap-0.5 text-[11px] text-ink/50 md:inline-flex" :title="`${task.comment_count} comments`">
      <svg viewBox="0 0 16 16" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M3 3.5h10v7H7l-3 2.5v-2.5H3z" /></svg>{{ task.comment_count }}
    </span>
    <StatusMenu :task="task" class="shrink-0" />
    <span class="grid grid-cols-1 h-5 min-w-6 shrink-0 place-items-center rounded-full bg-ink/[0.07] px-1.5 font-mono text-[10.5px] text-ink/70" :title="task.estimate === null ? 'Not estimated' : `${task.estimate} story points`">{{ task.estimate ?? '–' }}</span>
    <PriorityIcon :priority="task.priority" class="hidden sm:block" />
    <PersonMenu :value="task.assignee" :disabled="!ws.canManage" @change="(id) => ws.patch(task, { assignee: id })" />
  </div>
</template>
