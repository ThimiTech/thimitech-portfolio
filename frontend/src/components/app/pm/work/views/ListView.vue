<script setup lang="ts">
/** The whole plan as one tree (Module › Epic › Story › Task/Bug) with roll-ups, blockers, and spreadsheet import/export. */
import { computed, reactive, ref } from 'vue'
import api from '@/api/api'
import Modal from '../../../ui/Modal.vue'
import EmptyState from '../../../ui/EmptyState.vue'
import { toast } from '../../../ui/toast'
import { buildTree, dateLabel, errorMessage, isBlocked, todayNPT, TYPES, type ItemType, type Task, type TreeNode } from '../../pm'
import TypeIcon from '../TypeIcon.vue'
import StatusMenu from '../StatusMenu.vue'
import PersonMenu from '../PersonMenu.vue'
import PriorityIcon from '../PriorityIcon.vue'
import { useWorkspace } from '../workspace'

const ws = useWorkspace()
const props = reactive({
  get project() {
    return ws.project!
  },
  get tasks() {
    return ws.tasks
  },
  get userId() {
    return ws.me ?? undefined
  },
})
const emit = (event: 'select' | 'create' | 'changed', a?: unknown, b?: unknown) => {
  if (event === 'select') ws.go(a as Task)
  else if (event === 'create') ws.openCreate({ type: a as ItemType, parent: (b as number | null) ?? null })
  else ws.refreshTasks().then(() => ws.refreshProject())
}

const search = ref('')
const depth = ref(3) // deepest rank shown: 0 modules … 3 everything
const blockedOnly = ref(false)
const mine = ref(false)
const collapsed = ref(new Set<number>())

const byId = computed(() => new Map(props.tasks.map((t) => [t.id, t])))
const tree = computed(() => buildTree(props.tasks))
const STATUS_LABEL: Record<string, string> = { backlog: 'To do', active: 'In progress', review: 'In review', done: 'Done' }
const CHILD: Record<ItemType, ItemType | null> = { module: 'epic', epic: 'story', story: 'task', task: null, bug: null }

/** With a filter on, show matches plus their ancestors (and expand everything). */
const matches = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q && !blockedOnly.value && !mine.value) return null
  const keep = new Set<number>()
  for (const t of props.tasks) {
    if (q && !`${t.key} ${t.title} ${t.assignee_name || ''} ${t.blocker}`.toLowerCase().includes(q)) continue
    if (blockedOnly.value && !isBlocked(t, byId.value)) continue
    if (mine.value && t.assignee !== props.userId) continue
    for (let x: Task | undefined = t; x && !keep.has(x.id); x = x.parent ? byId.value.get(x.parent) : undefined) keep.add(x.id)
  }
  return keep
})
const rows = computed(() => {
  const out: TreeNode[] = []
  const walk = (nodes: TreeNode[]) => {
    for (const n of nodes) {
      if (matches.value && !matches.value.has(n.task.id)) continue
      if (TYPES[n.task.type].rank > depth.value) continue
      out.push(n)
      if (matches.value || !collapsed.value.has(n.task.id)) walk(n.children)
    }
  }
  walk(tree.value)
  return out
})
const modules = computed(() => tree.value.filter((n) => n.task.type === 'module'))
const stats = computed(() => {
  const today = todayNPT()
  const work = props.tasks.filter((t) => TYPES[t.type].rank >= 2)
  return {
    blocked: props.tasks.filter((t) => t.status !== 'done' && isBlocked(t, byId.value)).length,
    overdue: work.filter((t) => t.due_date && t.due_date < today && t.status !== 'done').length,
    unassigned: work.filter((t) => !t.assignee && t.status !== 'done').length,
  }
})
const pct = (n: TreeNode) => (n.total ? Math.round((n.done / n.total) * 100) : 0)
const overdue = (n: TreeNode) => !!n.due && n.due < todayNPT() && n.done < n.total
function toggle(id: number) {
  const next = new Set(collapsed.value)
  if (!next.delete(id)) next.add(id)
  collapsed.value = next
}
const collapseAll = () => (collapsed.value = new Set(props.tasks.filter((t) => TYPES[t.type].rank < 2).map((t) => t.id)))
const blockers = (t: Task) =>
  t.blocked_by.map((id) => byId.value.get(id)).filter((b): b is Task => !!b && b.status !== 'done')

// ───── Import from a spreadsheet ─────
const importing = ref(false)
const sheet = ref('')
const busy = ref(false)
const result = ref<{ created: number; updated: number; warnings: string[] } | null>(null)
function openImport() {
  sheet.value = ''
  result.value = null
  importing.value = true
}
async function runImport() {
  busy.value = true
  try {
    result.value = (await api.post('pm/tasks/import/', { project: props.project.id, text: sheet.value })).data
    toast.success(`Imported: ${result.value!.created} new, ${result.value!.updated} updated.`)
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
/** Same column layout as the importer, so the sheet round-trips. */
function exportSheet() {
  const lines = ['Module\tEpic\tStory\tTask\tDescription\tStatus\tBlocker\tAssignee\tDeadline']
  const clean = (s: string) => s.replace(/[\t\r\n]+/g, ' ')
  // Every row carries its full ancestor path, so a task directly under a module can't inherit a stale story.
  const walk = (nodes: TreeNode[], path: string[]) => {
    for (const n of nodes) {
      const t = n.task
      const cells = [...path]
      cells[TYPES[t.type].rank] = clean(t.title)
      const assignee = props.project.people.find((p) => p.id === t.assignee)?.name || ''
      lines.push([...cells, clean(t.description), STATUS_LABEL[t.status] || t.status, clean(t.blocker), assignee, t.due_date || ''].join('\t'))
      walk(n.children, cells)
    }
  }
  walk(tree.value, ['', '', '', ''])
  const href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/tab-separated-values' }))
  Object.assign(document.createElement('a'), { href, download: `${props.project.key}-plan.tsv` }).click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
</script>

<template>
  <div class="grid grid-cols-1 gap-5">
    <section v-if="modules.length" aria-label="Modules" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <RouterLink
        v-for="m in modules"
        :key="m.task.id"
        :to="ws.pathOf(m.task)"
        class="panel min-w-0 p-4 text-left hover:ring-2 hover:ring-river/30"
      >
        <span class="font-mono text-[10px] text-ink/55">{{ m.task.key }}</span>
        <span class="mt-1 block truncate text-sm font-medium">{{ m.task.title }}</span>
        <span class="mt-3 block h-1.5 overflow-hidden rounded-full bg-ink/10"
          ><span class="block h-full bg-moss" :style="{ width: pct(m) + '%' }"
        /></span>
        <span class="mt-2 flex justify-between text-[11px] text-ink/60"
          ><span>{{ m.done }}/{{ m.total }} done · {{ pct(m) }}%</span
          ><span :class="overdue(m) ? 'text-rust' : ''">{{ m.due ? dateLabel(m.due) : '' }}</span></span
        >
      </RouterLink>
    </section>

    <div class="flex flex-wrap items-center gap-3">
      <label class="field w-full sm:w-64"
        ><span class="sr-only">Search the plan</span
        ><input v-model="search" class="input" type="search" placeholder="Search titles, keys, people, blockers…"
      /></label>
      <label class="field"
        ><span class="sr-only">Show down to</span
        ><select v-model.number="depth" class="input">
          <option :value="0">Modules only</option>
          <option :value="1">Down to epics</option>
          <option :value="2">Down to stories</option>
          <option :value="3">Everything</option>
        </select></label
      >
      <label class="flex items-center gap-2 text-xs text-ink/65"
        ><input v-model="blockedOnly" type="checkbox" class="accent-ink" /> Blocked ({{ stats.blocked }})</label
      >
      <label class="flex items-center gap-2 text-xs text-ink/65"
        ><input v-model="mine" type="checkbox" class="accent-ink" /> Mine</label
      >
      <span class="text-xs text-ink/55"
        >{{ stats.overdue }} overdue · {{ stats.unassigned }} unassigned</span
      >
      <div class="ml-auto flex flex-wrap gap-2">
        <button class="btn-ghost btn-sm" @click="collapsed = new Set()">Expand all</button>
        <button class="btn-ghost btn-sm" @click="collapseAll">Collapse</button>
        <button class="btn-ghost btn-sm" :disabled="!props.tasks.length" @click="exportSheet">Export</button>
        <template v-if="props.project.can_manage">
          <button class="btn-ghost btn-sm" @click="openImport">Import from sheet</button>
          <button class="btn-primary btn-sm" @click="emit('create', 'module', null)">+ Module</button>
        </template>
      </div>
    </div>

    <div v-if="!props.tasks.length" class="panel">
      <EmptyState
        title="No plan yet"
        :hint="
          props.project.can_manage
            ? 'Break the project into modules, epics, stories and tasks, or paste your existing spreadsheet.'
            : 'Your project lead has not set up a plan yet.'
        "
      >
        <button v-if="props.project.can_manage" class="btn-ghost btn-sm" @click="openImport">Import from sheet</button>
      </EmptyState>
    </div>
    <div v-else class="relative overflow-x-auto rounded-xl border border-ink/10">
      <table class="w-full min-w-[60rem] table-fixed text-sm">
        <thead class="bg-panel/50 text-left text-[11px] uppercase tracking-wide text-ink/55">
          <tr>
            <th class="px-3 py-2 font-medium">Work</th>
            <th class="w-32 px-3 py-2 font-medium">Status</th>
            <th class="w-32 px-3 py-2 font-medium">Progress</th>
            <th class="w-40 px-3 py-2 font-medium">Assignee</th>
            <th class="w-24 px-3 py-2 font-medium">Deadline</th>
            <th class="w-40 px-3 py-2 font-medium">Blockers</th>
            <th v-if="props.project.can_manage" class="w-10 px-2 py-2"><span class="sr-only">Add child</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="n in rows" :key="n.task.id" class="border-t border-ink/10 hover:bg-panel/30">
            <td class="px-3 py-2">
              <div class="flex min-w-0 items-center gap-2" :style="{ paddingLeft: n.depth * 1.25 + 'rem' }">
                <button
                  v-if="n.children.length"
                  class="w-4 shrink-0 text-ink/55 hover:text-ink"
                  :aria-expanded="!collapsed.has(n.task.id) || !!matches"
                  :aria-label="`${collapsed.has(n.task.id) ? 'Expand' : 'Collapse'} ${n.task.title}`"
                  @click="toggle(n.task.id)"
                >
                  {{ collapsed.has(n.task.id) && !matches ? '▸' : '▾' }}
                </button>
                <span v-else class="w-4 shrink-0" />
                <TypeIcon :type="n.task.type" />
                <span class="shrink-0 font-mono text-[10px] text-ink/50">{{ n.task.key }}</span>
                <button
                  class="min-w-0 truncate text-left hover:text-river"
                  :class="TYPES[n.task.type].rank < 2 ? 'font-medium' : ''"
                  :title="n.task.description || n.task.title"
                  @click="emit('select', n.task)"
                >
                  {{ n.task.title }}
                </button>
              </div>
            </td>
            <td class="px-3 py-2"><StatusMenu :task="n.task" /></td>
            <td class="px-3 py-2">
              <div v-if="n.total && (n.children.length || TYPES[n.task.type].rank < 2)" class="flex items-center gap-2">
                <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-ink/10"
                  ><span class="block h-full bg-moss" :style="{ width: pct(n) + '%' }"
                /></span>
                <span class="w-12 text-right font-mono text-[10px] text-ink/60">{{ n.done }}/{{ n.total }}</span>
              </div>
            </td>
            <td class="px-3 py-2">
              <span class="flex min-w-0 items-center gap-2">
                <PriorityIcon :priority="n.task.priority" />
                <PersonMenu :value="n.task.assignee" :disabled="!props.project.can_manage" show-name :size="22" @change="(id) => ws.patch(n.task, { assignee: id })" />
              </span>
            </td>
            <td class="px-3 py-2 text-xs" :class="overdue(n) ? 'text-rust' : 'text-ink/60'">
              {{ n.due ? dateLabel(n.due) : '—' }}
            </td>
            <td class="px-3 py-2 text-xs">
              <span v-if="n.task.blocker && n.task.status !== 'done'" class="block truncate text-rust" :title="n.task.blocker"
                >⚠ {{ n.task.blocker }}</span
              >
              <span v-if="n.task.status !== 'done'" class="flex flex-wrap gap-1">
                <button
                  v-for="b in blockers(n.task)"
                  :key="b.id"
                  class="rounded border border-rust/30 px-1 font-mono text-[10px] text-rust"
                  :title="`Blocked by ${b.title}`"
                  @click="emit('select', b)"
                >
                  {{ b.key }}
                </button>
              </span>
            </td>
            <td v-if="props.project.can_manage" class="px-2 py-2">
              <button
                v-if="CHILD[n.task.type]"
                class="rounded px-2 py-1 text-ink/60 hover:bg-paper"
                :aria-label="`Add ${TYPES[CHILD[n.task.type]!].label.toLowerCase()} under ${n.task.title}`"
                :title="`Add ${TYPES[CHILD[n.task.type]!].label.toLowerCase()}`"
                @click="emit('create', CHILD[n.task.type]!, n.task.id)"
              >
                +
              </button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="7" class="px-3 py-6 text-center text-sm text-ink/55">Nothing matches these filters.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :open="importing" title="Import from a spreadsheet" width="max-w-3xl" @close="importing = false">
      <form class="grid grid-cols-1 gap-4" @submit.prevent="runImport">
        <p class="text-sm text-ink/70">
          Copy rows from Excel or Google Sheets and paste them below, in this column order:
          <span class="font-mono text-xs"
            >Module · Epic · Story · Task · Description · Status · Blocker · Assignee · Deadline</span
          >. Leave a level blank to keep the one above it, as in an outline. Assignees are matched by name or email, and
          deadlines should be written YYYY-MM-DD. Running the same sheet again updates items instead of duplicating them.
        </p>
        <label class="field"
          ><span class="ledger-label">Rows</span
          ><textarea
            v-model="sheet"
            class="input font-mono text-xs"
            rows="12"
            required
            placeholder="Dashboard&#9;WMS Layer Management&#9;Backend Create Model"
            @keydown.tab.prevent="
              (e: KeyboardEvent) => {
                const el = e.target as HTMLTextAreaElement
                el.setRangeText('\t', el.selectionStart, el.selectionEnd, 'end')
                sheet = el.value
              }
            "
        /></label>
        <div v-if="result" class="rounded-lg bg-panel/50 p-3 text-sm" role="status">
          <p>{{ result.created }} created · {{ result.updated }} updated</p>
          <ul v-if="result.warnings.length" class="mt-2 list-disc pl-5 text-xs text-rust">
            <li v-for="w in result.warnings" :key="w">{{ w }}</li>
          </ul>
        </div>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn-ghost" @click="importing = false">Close</button>
          <button class="btn-ink" :disabled="busy || !sheet.trim()">{{ busy ? 'Importing…' : 'Import' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>
