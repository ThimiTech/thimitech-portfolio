<script setup lang="ts">
import { computed } from 'vue'
import { dateLabel, type Task, type Milestone } from './pm'
const props = defineProps<{ tasks: Task[]; milestones: Milestone[] }>()
const emit = defineEmits<{ select: [task: Task] }>()
const day = (value: string) => Date.parse(value + 'T00:00:00Z') / 86400000
const dated = computed(() => props.tasks.filter((t) => t.start_date || t.due_date))
const range = computed(() => {
  const dates = [
    ...dated.value.flatMap((t) => [t.start_date, t.due_date].filter((d): d is string => !!d)),
    ...props.milestones.map((m) => m.due_date),
  ].map(day)
  const start = Math.min(...dates)
  const end = Math.max(...dates)
  return { start, end, span: Math.max(end - start + 1, 7) }
})
function placement(task: Task) {
  const start = day(task.start_date || task.due_date!)
  const end = day(task.due_date || task.start_date!)
  return {
    marginLeft: `${((start - range.value.start) / range.value.span) * 100}%`,
    width: `${Math.max(((end - start + 1) / range.value.span) * 100, 1)}%`,
  }
}
</script>
<template>
  <section class="panel overflow-hidden" aria-label="Project timeline">
    <div class="panel-head">
      <h2 class="font-medium">Delivery timeline</h2>
      <span class="text-xs text-ink/60">{{ tasks.length - dated.length }} tasks without dates</span>
    </div>
    <div v-if="!dated.length && !milestones.length" class="p-10 text-center text-sm text-ink/60">
      Add dates to tasks or a milestone to start your timeline.
    </div>
    <div v-else class="overflow-x-auto p-5">
      <div class="min-w-[560px]">
        <div class="mb-5 grid grid-cols-[180px_1fr] gap-4 text-xs text-ink/60">
          <span>Task / milestone</span>
          <div class="flex justify-between font-mono">
            <span>{{ dateLabel(new Date(range.start * 86400000).toISOString().slice(0, 10)) }}</span
            ><span>{{
              dateLabel(
                new Date((range.start + range.span - 1) * 86400000).toISOString().slice(0, 10),
              )
            }}</span>
          </div>
        </div>
        <div
          v-for="task in dated"
          :key="task.id"
          class="grid grid-cols-[180px_1fr] items-center gap-4 border-t border-ink/10 py-4"
        >
          <button class="truncate text-left text-sm hover:text-river" @click="emit('select', task)">
            {{ task.title }}
          </button>
          <div class="timeline-track">
            <button
              class="block min-h-7 max-w-full overflow-hidden rounded px-2 text-left text-[10px] text-paper"
              :class="task.status === 'done' ? 'bg-moss' : 'bg-river'"
              :style="placement(task)"
              :aria-label="`${task.title}: ${dateLabel(task.start_date)} to ${dateLabel(task.due_date)}`"
              @click="emit('select', task)"
            >
              {{ task.key }}
            </button>
          </div>
        </div>
        <div
          v-for="m in milestones"
          :key="`m${m.id}`"
          class="grid grid-cols-[180px_1fr] items-center gap-4 border-t border-dashed border-ink/15 py-4"
        >
          <span class="truncate text-sm">{{ m.completed ? '✓' : '◇' }} {{ m.title }}</span>
          <div class="timeline-track relative h-6">
            <span
              class="absolute text-flag"
              :style="{
                left: `${Math.min(((day(m.due_date) - range.start) / range.span) * 100, 96)}%`,
              }"
              :aria-label="dateLabel(m.due_date)"
              >◆</span
            >
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<style scoped>
.timeline-track {
  background: repeating-linear-gradient(
    to right,
    transparent 0,
    transparent calc(25% - 1px),
    rgb(26 26 26 / 0.08) calc(25% - 1px),
    rgb(26 26 26 / 0.08) 25%
  );
}
</style>
