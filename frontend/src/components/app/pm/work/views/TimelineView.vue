<script setup lang="ts">
import TaskTimeline from '../../TaskTimeline.vue'
import type { Task } from '../../pm'
import { useWorkspace } from '../workspace'
const ws = useWorkspace()
const reschedule = (t: Task, start_date: string, due_date: string) => ws.patch(t, { start_date, due_date })
</script>
<template>
  <TaskTimeline :tasks="ws.tasks" :milestones="ws.milestones" :sprints="ws.sprints" :can-manage="ws.canManage" @select="ws.go" @reschedule="reschedule" />
</template>
