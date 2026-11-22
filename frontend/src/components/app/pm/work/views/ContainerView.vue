<script setup lang="ts">
/** A module's or an epic's own page. A module lists its epics, each with the issues inside it, plus issues that sit
 *  directly in the module; an epic lists its stories (each with their tasks) plus its loose tasks and bugs. Create
 *  epics, stories, tasks and bugs in place; drag rows to reorder them or move them to another epic. */
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Avatar from '../../../ui/Avatar.vue'
import EmptyState from '../../../ui/EmptyState.vue'
import { pageTitle } from '../../../ui/crumb'
import MarkdownView from '../../MarkdownView.vue'
import { dateLabel, todayNPT, type Task } from '../../pm'
import type { ItemType } from '../../plan'
import TypeIcon from '../TypeIcon.vue'
import StatusMenu from '../StatusMenu.vue'
import PersonMenu from '../PersonMenu.vue'
import IssueRow from '../IssueRow.vue'
import InlineCreate from '../InlineCreate.vue'
import { CATEGORY_META, TYPE_META, ancestors, categoryOf, descendants, moveInList, rollup, swatch } from '../meta'
import { useWorkspace } from '../workspace'
import { toast } from '../../../ui/toast'
import { TYPES } from '../../plan'

const RANK = Object.fromEntries(Object.entries(TYPES).map(([k, v]) => [k, v.rank])) as Record<ItemType, number>

const ws = useWorkspace()
const route = useRoute()
const item = computed(() => ws.byId.get(Number(route.params.itemId)) || null)
watch(() => item.value?.title, (t) => t && (pageTitle.value = `${t} · ${ws.project?.name || ''}`), { immediate: true })

const CONFIG: Record<'module' | 'epic', { group: ItemType; inGroup: ItemType[]; loose: ItemType[]; groups: string; looseLabel: string }> = {
  module: { group: 'epic', inGroup: ['story', 'task', 'bug'], loose: ['story', 'task', 'bug'], groups: 'Epics', looseLabel: 'Issues directly in this module' },
  epic: { group: 'story', inGroup: ['task', 'bug'], loose: ['task', 'bug'], groups: 'Stories', looseLabel: 'Tasks and bugs directly in this epic' },
}
const cfg = computed(() => (item.value?.type === 'module' || item.value?.type === 'epic' ? CONFIG[item.value.type] : null))
const trail = computed(() => (item.value ? ancestors(item.value, ws.byId).reverse() : []))
const direct = computed(() => (item.value ? ws.children.get(item.value.id) || [] : []))
const groups = computed(() => direct.value.filter((t) => t.type === cfg.value?.group))
const loose = computed(() => direct.value.filter((t) => t.type !== cfg.value?.group))
const stats = computed(() => (item.value ? rollup(item.value.id, ws.children, ws.blocked) : null))
const groupStats = (t: Task) => rollup(t.id, ws.children, ws.blocked)
/** A top-level row followed by everything beneath it, indented. */
const rowsOf = (tops: Task[]) => tops.flatMap((t, top) => [{ task: t, depth: 0, top }, ...descendants(t.id, ws.children, 1).map((d) => ({ ...d, top }))])
const today = todayNPT()

const team = computed(() => {
  if (!item.value) return []
  const counts = new Map<number, { name: string; open: number; done: number }>()
  for (const { task: t } of descendants(item.value.id, ws.children)) {
    if (!t.assignee || t.type === 'module' || t.type === 'epic') continue
    const row = counts.get(t.assignee) || { name: t.assignee_name || '', open: 0, done: 0 }
    row[categoryOf(t.status) === 'done' ? 'done' : 'open']++
    counts.set(t.assignee, row)
  }
  return [...counts.values()].sort((a, b) => b.open - a.open)
})
const collapsed = ref(new Set<number>())
function toggle(id: number) {
  const next = new Set(collapsed.value)
  if (!next.delete(id)) next.add(id)
  collapsed.value = next
}
const descOpen = ref(false)
const longDesc = computed(() => !!item.value && (item.value.description.length > 320 || item.value.description.split('\n').length > 5))

// ───── summary editing ─────
const editing = ref(false)
const draft = ref('')
const titleInput = ref<HTMLInputElement | null>(null)
async function editTitle() {
  if (!ws.canManage || !item.value) return
  draft.value = item.value.title
  editing.value = true
  await nextTick()
  titleInput.value?.select()
}
function commitTitle() {
  if (!editing.value) return
  editing.value = false
  if (item.value && draft.value.trim() && draft.value.trim() !== item.value.title) ws.patch(item.value, { title: draft.value.trim() })
}
const groupCreate = ref<InstanceType<typeof InlineCreate> | null>(null)

// ───── drag: reorder top-level rows, or move them under another group ─────
const dragging = ref<number | null>(null)
const target = ref<{ list: number; index: number } | null>(null)
function onDragStart(t: Task, e: DragEvent) {
  dragging.value = t.id
  e.dataTransfer?.setData('text/plain', t.key)
}
function onDragEnd() {
  dragging.value = null
  target.value = null
}
function overRow(list: number, top: number, depth: number, e: DragEvent) {
  if (dragging.value === null) return
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
  target.value = { list, index: depth === 0 && e.clientY < r.top + r.height / 2 ? top : top + 1 }
}
function overList(list: number, size: number) {
  if (dragging.value !== null && target.value?.list !== list) target.value = { list, index: size }
}
/** `list` is the parent the rows sit under: a group's id, or the page item's id for the loose list. */
function drop(list: number, tops: Task[]) {
  const t = dragging.value !== null ? ws.byId.get(dragging.value) : undefined
  const to = target.value
  onDragEnd()
  if (!t || !to || !ws.canManage) return
  const parent = ws.byId.get(list)
  if (parent && RANK[parent.type] >= RANK[t.type]) {
    toast.error(`A ${TYPE_META[t.type].label.toLowerCase()} can’t go inside a ${TYPE_META[parent.type].label.toLowerCase()}.`)
    return
  }
  const ids = tops.map((x) => x.id)
  const from = ids.indexOf(t.id)
  const order = moveInList(ids, t.id, from >= 0 && from < to.index ? to.index - 1 : to.index)
  ws.move(t, { parent: list }, order)
}
const line = (list: number, i: number) => target.value?.list === list && target.value.index === i
</script>

<template>
  <div v-if="!item" class="panel">
    <EmptyState :title="ws.loading ? 'Loading…' : 'Not found'" :hint="ws.loading ? '' : 'This module or epic was deleted, or it belongs to another project.'">
      <RouterLink :to="`${ws.base}/modules`" class="btn-ghost btn-sm">All modules</RouterLink>
    </EmptyState>
  </div>
  <div v-else-if="!cfg" class="panel">
    <EmptyState title="This is not a module or an epic" :hint="`${item.key} is a ${TYPE_META[item.type].label.toLowerCase()}.`">
      <button type="button" class="btn-ghost btn-sm" @click="ws.openIssue(item)">Open {{ item.key }}</button>
    </EmptyState>
  </div>
  <div v-else class="grid grid-cols-1 gap-6">
    <!-- header -->
    <header class="min-w-0">
      <nav aria-label="Location" class="mb-3 flex min-w-0 flex-wrap items-center gap-1.5 text-xs text-ink/60">
        <RouterLink :to="`${ws.base}/modules`" class="hover:text-ink hover:underline">Modules</RouterLink>
        <template v-for="a in trail" :key="a.id">
          <span aria-hidden="true">/</span>
          <RouterLink :to="ws.pathOf(a)" class="inline-flex max-w-[16rem] min-w-0 items-center gap-1 hover:text-ink hover:underline"><TypeIcon :type="a.type" :size="14" /><span class="truncate">{{ a.title }}</span></RouterLink>
        </template>
        <span aria-hidden="true">/</span>
        <span class="font-mono">{{ item.key }}</span>
      </nav>
      <div class="flex flex-wrap items-start gap-3">
        <span class="mt-1.5 h-8 w-1.5 shrink-0 rounded-full" :style="{ background: swatch(item.id) }" aria-hidden="true" />
        <TypeIcon :type="item.type" :size="24" class="mt-1.5" />
        <div class="min-w-0 flex-1">
          <input v-if="editing" ref="titleInput" v-model="draft" class="input font-display !text-2xl font-medium" maxlength="200" aria-label="Name" @keydown.enter.prevent="commitTitle" @keydown.esc.prevent="editing = false" @blur="commitTitle" />
          <h2 v-else>
            <button type="button" class="rounded-md px-1 text-left font-display text-[26px] leading-tight font-medium tracking-tight break-words" :class="ws.canManage ? 'hover:bg-panel/70' : 'cursor-default'" :aria-label="ws.canManage ? `${item.title}. Rename` : undefined" @click="editTitle">
              {{ item.title }}
            </button>
          </h2>
          <p class="mt-1 px-1 text-xs text-ink/55">{{ TYPE_META[item.type].label }} · {{ item.key }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <StatusMenu :task="item" size="md" />
          <button type="button" class="btn-ghost btn-sm" @click="ws.openIssue(item)">Details</button>
          <RouterLink :to="{ path: `${ws.base}/board`, query: { in: String(item.id) } }" class="btn-ghost btn-sm">View on board</RouterLink>
          <button v-if="ws.canManage" type="button" class="btn-primary btn-sm" @click="groupCreate?.start()">+ {{ TYPE_META[cfg.group].label }}</button>
        </div>
      </div>
    </header>

    <div class="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
      <div class="grid grid-cols-1 min-w-0 gap-6">
        <!-- progress strip -->
        <section v-if="stats" class="panel grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center" aria-label="Progress">
          <div class="min-w-0">
            <div class="flex h-2.5 overflow-hidden rounded-full bg-ink/10" role="img" :aria-label="`${stats.done} of ${stats.total} done, ${stats.progress} in progress`">
              <span class="bg-moss" :style="{ width: `${stats.total ? (stats.done / stats.total) * 100 : 0}%` }" />
              <span class="bg-sky" :style="{ width: `${stats.total ? (stats.progress / stats.total) * 100 : 0}%` }" />
            </div>
            <p class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink/60">
              <span><strong class="readout text-ink">{{ stats.percent }}%</strong> done</span>
              <span>{{ stats.done }} done · {{ stats.progress }} in progress · {{ stats.total - stats.done - stats.progress }} to do</span>
              <span>{{ stats.donePoints }}/{{ stats.points }} pts</span>
              <span v-if="stats.blocked" class="text-rust">{{ stats.blocked }} blocked</span>
            </p>
          </div>
          <p class="text-sm" :class="(item.due_date || stats.due) && (item.due_date || stats.due)! < today && stats.done < stats.total ? 'text-rust' : 'text-ink/65'">
            {{ item.due_date || stats.due ? `Due ${dateLabel(item.due_date || stats.due)}` : 'No due date' }}
          </p>
        </section>

        <!-- description -->
        <section v-if="item.description" class="min-w-0">
          <div class="relative overflow-hidden" :class="longDesc && !descOpen ? 'max-h-32' : ''">
            <MarkdownView :source="item.description" />
            <div v-if="longDesc && !descOpen" class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-paper" />
          </div>
          <button v-if="longDesc" type="button" class="mt-1 text-xs text-river hover:underline" :aria-expanded="descOpen" @click="descOpen = !descOpen">{{ descOpen ? 'Show less' : 'Show more' }}</button>
        </section>

        <!-- groups (epics in a module, stories in an epic) -->
        <section :aria-labelledby="`grp-${item.id}`" class="grid grid-cols-1 gap-3">
          <h3 :id="`grp-${item.id}`" class="flex items-center gap-2 text-sm font-semibold">
            {{ cfg.groups }} <span class="font-mono text-xs font-normal text-ink/50">{{ groups.length }}</span>
          </h3>
          <article
            v-for="g in groups"
            :key="g.id"
            class="overflow-hidden rounded-xl border bg-sheet transition-colors"
            :class="target?.list === g.id ? 'border-river/60 ring-2 ring-river/20' : 'border-ink/10'"
            @dragover.prevent="overList(g.id, (ws.children.get(g.id) || []).length)"
            @drop.prevent="drop(g.id, ws.children.get(g.id) || [])"
          >
            <header class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5" :style="{ boxShadow: `inset 3px 0 0 ${swatch(g.id)}` }">
              <button type="button" class="shrink-0 rounded p-1 text-ink/50 hover:bg-panel" :aria-expanded="!collapsed.has(g.id)" :aria-label="`${collapsed.has(g.id) ? 'Expand' : 'Collapse'} ${g.title}`" @click="toggle(g.id)">
                <svg viewBox="0 0 12 12" class="h-3 w-3 transition" :class="collapsed.has(g.id) ? '-rotate-90' : ''" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m3 4.5 3 3 3-3" /></svg>
              </button>
              <TypeIcon :type="g.type" />
              <span class="font-mono text-[11px] text-ink/55">{{ g.key }}</span>
              <button type="button" class="min-w-0 flex-1 basis-40 truncate text-left font-medium hover:text-river hover:underline" :title="g.title" @click="ws.go(g)">{{ g.title }}</button>
              <span class="flex w-32 items-center gap-2" :title="`${groupStats(g).done}/${groupStats(g).total} done`">
                <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-ink/10"><span class="block h-full bg-moss" :style="{ width: `${groupStats(g).percent}%` }" /></span>
                <span class="font-mono text-[10.5px] text-ink/55">{{ groupStats(g).done }}/{{ groupStats(g).total }}</span>
              </span>
              <StatusMenu :task="g" />
              <PersonMenu :value="g.assignee" :disabled="!ws.canManage" label="Owner" @change="(id) => ws.patch(g, { assignee: id })" />
            </header>
            <template v-if="!collapsed.has(g.id)">
              <ul class="border-t border-ink/10">
                <template v-for="r in rowsOf(ws.children.get(g.id) || [])" :key="r.task.id">
                  <li v-if="r.depth === 0 && line(g.id, r.top)" class="h-0.5 bg-river" aria-hidden="true" />
                  <li
                    class="cursor-pointer border-b border-ink/5 hover:bg-panel/40"
                    :class="dragging === r.task.id ? 'opacity-40' : ''"
                    :draggable="ws.canManage && r.depth === 0"
                    @dragstart="onDragStart(r.task, $event)"
                    @dragend="onDragEnd"
                    @dragover.prevent.stop="overRow(g.id, r.top, r.depth, $event)"
                  >
                    <IssueRow :task="r.task" :depth="r.depth" :show-parent="false" show-due />
                  </li>
                </template>
                <li v-if="line(g.id, (ws.children.get(g.id) || []).length)" class="h-0.5 bg-river" aria-hidden="true" />
                <li v-if="!(ws.children.get(g.id) || []).length" class="px-4 py-3 text-sm text-ink/55">Nothing in this {{ TYPE_META[g.type].label.toLowerCase() }} yet.</li>
              </ul>
              <div class="p-1.5">
                <InlineCreate :types="cfg.inGroup" :defaults="{ parent: g.id }" :label="`Create issue in ${g.title}`" />
              </div>
            </template>
          </article>
          <p v-if="!groups.length" class="rounded-xl border-2 border-dashed border-ink/15 px-4 py-6 text-center text-sm text-ink/55">
            No {{ cfg.groups.toLowerCase() }} yet.{{ ws.canManage ? ` Create the first ${TYPE_META[cfg.group].label.toLowerCase()} below.` : '' }}
          </p>
          <InlineCreate ref="groupCreate" :types="[cfg.group]" :defaults="{ parent: item.id }" :label="`Create ${TYPE_META[cfg.group].label.toLowerCase()}`" :placeholder="`${TYPE_META[cfg.group].label} name`" />
        </section>

        <!-- loose issues -->
        <section
          :aria-labelledby="`loose-${item.id}`"
          class="rounded-xl border bg-sheet transition-colors"
          :class="target?.list === item.id ? 'border-river/60 ring-2 ring-river/20' : 'border-ink/10'"
          @dragover.prevent="overList(item.id, loose.length)"
          @drop.prevent="drop(item.id, loose)"
        >
          <h3 :id="`loose-${item.id}`" class="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold">
            {{ cfg.looseLabel }} <span class="font-mono text-xs font-normal text-ink/50">{{ loose.length }}</span>
          </h3>
          <ul class="border-t border-ink/10">
            <template v-for="r in rowsOf(loose)" :key="r.task.id">
              <li v-if="r.depth === 0 && line(item.id, r.top)" class="h-0.5 bg-river" aria-hidden="true" />
              <li
                class="cursor-pointer border-b border-ink/5 hover:bg-panel/40"
                :class="dragging === r.task.id ? 'opacity-40' : ''"
                :draggable="ws.canManage && r.depth === 0"
                @dragstart="onDragStart(r.task, $event)"
                @dragend="onDragEnd"
                @dragover.prevent.stop="overRow(item.id, r.top, r.depth, $event)"
              >
                <IssueRow :task="r.task" :depth="r.depth" :show-parent="false" show-due />
              </li>
            </template>
            <li v-if="line(item.id, loose.length)" class="h-0.5 bg-river" aria-hidden="true" />
            <li v-if="!loose.length" class="px-4 py-3 text-sm text-ink/55">None. Drag issues here to take them out of their {{ TYPE_META[cfg.group].label.toLowerCase() }}.</li>
          </ul>
          <div class="p-1.5"><InlineCreate :types="cfg.loose" :defaults="{ parent: item.id }" /></div>
        </section>
      </div>

      <!-- sidebar -->
      <aside class="grid grid-cols-1 min-w-0 gap-4 xl:sticky xl:top-4">
        <dl class="panel grid grid-cols-1 gap-3 p-4 text-sm">
          <div class="grid grid-cols-[5.5rem_minmax(0,1fr)] items-center gap-2">
            <dt class="text-xs text-ink/55">Owner</dt>
            <dd><PersonMenu :value="item.assignee" :disabled="!ws.canManage" show-name label="Owner" @change="(id) => ws.patch(item!, { assignee: id })" /></dd>
          </div>
          <div class="grid grid-cols-[5.5rem_minmax(0,1fr)] items-center gap-2">
            <dt class="text-xs text-ink/55">Start</dt>
            <dd>
              <input v-if="ws.canManage" :value="item.start_date || ''" type="date" class="input !py-1 text-sm" aria-label="Start date" @change="ws.patch(item!, { start_date: ($event.target as HTMLInputElement).value || null })" />
              <span v-else>{{ item.start_date ? dateLabel(item.start_date) : '—' }}</span>
            </dd>
          </div>
          <div class="grid grid-cols-[5.5rem_minmax(0,1fr)] items-center gap-2">
            <dt class="text-xs text-ink/55">Due</dt>
            <dd>
              <input v-if="ws.canManage" :value="item.due_date || ''" type="date" :min="item.start_date || undefined" class="input !py-1 text-sm" aria-label="Due date" @change="ws.patch(item!, { due_date: ($event.target as HTMLInputElement).value || null })" />
              <span v-else>{{ item.due_date ? dateLabel(item.due_date) : '—' }}</span>
            </dd>
          </div>
        </dl>
        <section v-if="stats && stats.total" class="panel p-4" aria-labelledby="cv-status">
          <h3 id="cv-status" class="mb-3 text-xs font-semibold">Status</h3>
          <ul class="grid grid-cols-1 gap-2 text-sm">
            <li v-for="cat in (['todo', 'progress', 'done'] as const)" :key="cat" class="flex items-center gap-2">
              <span class="w-20 shrink-0 text-xs text-ink/65">{{ CATEGORY_META[cat].label }}</span>
              <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-ink/10"><span class="block h-full" :class="CATEGORY_META[cat].bar" :style="{ width: `${((cat === 'done' ? stats.done : cat === 'progress' ? stats.progress : stats.total - stats.done - stats.progress) / stats.total) * 100}%` }" /></span>
              <span class="w-6 text-right font-mono text-xs">{{ cat === 'done' ? stats.done : cat === 'progress' ? stats.progress : stats.total - stats.done - stats.progress }}</span>
            </li>
          </ul>
        </section>
        <section v-if="team.length" class="panel p-4" aria-labelledby="cv-team">
          <h3 id="cv-team" class="mb-3 text-xs font-semibold">People</h3>
          <ul class="grid grid-cols-1 gap-2">
            <li v-for="p in team" :key="p.name" class="flex min-w-0 items-center gap-2 text-sm">
              <Avatar :name="p.name" :size="24" /><span class="min-w-0 flex-1 truncate">{{ p.name }}</span>
              <span class="font-mono text-[11px] text-ink/55" :title="`${p.open} open, ${p.done} done`">{{ p.open }} open</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>
