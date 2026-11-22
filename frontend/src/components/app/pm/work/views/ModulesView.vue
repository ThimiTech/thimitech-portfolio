<script setup lang="ts">
/** Every module as a card with its rolled-up progress; epics that sit outside a module are listed after them. */
import { computed } from 'vue'
import Avatar from '../../../ui/Avatar.vue'
import EmptyState from '../../../ui/EmptyState.vue'
import { dateLabel, todayNPT, type Task } from '../../pm'
import TypeIcon from '../TypeIcon.vue'
import StatusMenu from '../StatusMenu.vue'
import InlineCreate from '../InlineCreate.vue'
import { CATEGORY_META, rollup, swatch } from '../meta'
import { useWorkspace } from '../workspace'

const ws = useWorkspace()
const today = todayNPT()
const stats = (t: Task) => rollup(t.id, ws.children, ws.blocked)
const childCount = (t: Task, type: string) => (ws.children.get(t.id) || []).filter((c) => c.type === type).length
const looseEpics = computed(() => ws.epics.filter((e) => !e.parent || ws.byId.get(e.parent)?.type !== 'module'))
const looseWork = computed(() => ws.work.filter((t) => !t.parent).length)
</script>

<template>
  <div class="grid grid-cols-1 gap-6">
    <p class="max-w-3xl text-sm text-ink/65">
      Modules are the big parts of the product. Each holds epics (features), and epics hold the stories, tasks and bugs your team works on.
      Open a module to plan its epics and issues.
    </p>

    <div v-if="!ws.modules.length" class="panel">
      <EmptyState title="No modules yet" :hint="ws.canManage ? 'Create the first module below, or import your plan from a spreadsheet in the List view.' : 'Your project lead has not set up modules yet.'" />
    </div>
    <section v-else aria-label="Modules" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="m in ws.modules"
        :key="m.id"
        class="group panel flex min-w-0 cursor-pointer flex-col p-5 transition hover:border-river/50 hover:shadow-md"
        :style="{ borderTop: `3px solid ${swatch(m.id)}` }"
        @click="$router.push(ws.pathOf(m))"
      >
        <div class="flex items-center gap-2">
          <TypeIcon type="module" />
          <span class="font-mono text-[11px] text-ink/55">{{ m.key }}</span>
          <span class="ml-auto"><StatusMenu :task="m" /></span>
        </div>
        <h2 class="mt-3 line-clamp-2 text-lg leading-snug font-medium break-words">
          <RouterLink :to="ws.pathOf(m)" class="group-hover:text-river focus-visible:underline focus-visible:outline-none" @click.stop>{{ m.title }}</RouterLink>
        </h2>
        <p v-if="m.description" class="mt-1 line-clamp-2 text-sm text-ink/60 break-words">{{ m.description }}</p>
        <div class="mt-auto pt-5">
          <div class="flex h-2 overflow-hidden rounded-full bg-ink/10" role="img" :aria-label="`${stats(m).done} of ${stats(m).total} issues done`">
            <span class="bg-moss" :style="{ width: `${stats(m).total ? (stats(m).done / stats(m).total) * 100 : 0}%` }" />
            <span class="bg-sky" :style="{ width: `${stats(m).total ? (stats(m).progress / stats(m).total) * 100 : 0}%` }" />
          </div>
          <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink/60">
            <span class="readout font-medium text-ink">{{ stats(m).percent }}%</span>
            <span>{{ stats(m).done }}/{{ stats(m).total }} issues</span>
            <span>{{ childCount(m, 'epic') }} epic{{ childCount(m, 'epic') === 1 ? '' : 's' }}</span>
            <span v-if="stats(m).blocked" class="text-rust">{{ stats(m).blocked }} blocked</span>
            <span v-if="m.due_date || stats(m).due" class="ml-auto" :class="(m.due_date || stats(m).due)! < today && stats(m).done < stats(m).total ? 'text-rust' : ''">
              Due {{ dateLabel(m.due_date || stats(m).due) }}
            </span>
            <Avatar v-if="m.assignee_name" :name="m.assignee_name" :size="22" class="ml-1" />
          </div>
        </div>
      </article>
    </section>
    <div class="max-w-xl"><InlineCreate :types="['module']" label="Create module" placeholder="Module name, e.g. Dashboard" /></div>

    <section v-if="looseEpics.length || looseWork" aria-labelledby="loose-epics">
      <h2 id="loose-epics" class="mb-3 text-sm font-semibold">Outside any module</h2>
      <ul class="divide-y divide-ink/5 overflow-hidden rounded-xl border border-ink/10 bg-sheet">
        <li v-for="e in looseEpics" :key="e.id">
          <RouterLink :to="ws.pathOf(e)" class="flex min-w-0 items-center gap-3 px-4 py-2.5 text-sm hover:bg-panel/40">
            <TypeIcon type="epic" />
            <span class="font-mono text-[11px] text-ink/55">{{ e.key }}</span>
            <span class="min-w-0 flex-1 truncate">{{ e.title }}</span>
            <span class="hidden w-28 sm:block"><span class="block h-1.5 overflow-hidden rounded-full bg-ink/10"><span class="block h-full bg-moss" :style="{ width: `${stats(e).percent}%` }" /></span></span>
            <span class="font-mono text-[11px] text-ink/55">{{ stats(e).done }}/{{ stats(e).total }}</span>
          </RouterLink>
        </li>
        <li v-if="looseWork" class="px-4 py-2.5 text-sm text-ink/60">
          {{ looseWork }} issue{{ looseWork === 1 ? '' : 's' }} without a parent ·
          <RouterLink :to="`${ws.base}/list`" class="text-river hover:underline">see them in the list</RouterLink>
        </li>
      </ul>
    </section>
    <p class="flex flex-wrap gap-4 text-xs text-ink/50">
      <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm" :class="CATEGORY_META.done.bar" />Done</span>
      <span class="flex items-center gap-1.5"><span class="h-2 w-3 rounded-sm" :class="CATEGORY_META.progress.bar" />In progress</span>
    </p>
  </div>
</template>
