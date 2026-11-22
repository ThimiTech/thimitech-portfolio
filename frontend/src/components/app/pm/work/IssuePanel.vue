<script setup lang="ts">
/** The issue view (opened by `?issue=KEY-12` on any workspace or project page). Every field saves as you change it. */
import { computed, nextTick, ref, watch } from 'vue'
import api from '@/api/api'
import Modal from '../../ui/Modal.vue'
import Avatar from '../../ui/Avatar.vue'
import { toast } from '../../ui/toast'
import { confirmDialog } from '../../ui/confirm'
import MarkdownView from '../MarkdownView.vue'
import { dateLabel, errorMessage, type Activity, type Comment, type Task } from '../pm'
import type { ItemType } from '../plan'
import TypeIcon from './TypeIcon.vue'
import PriorityIcon from './PriorityIcon.vue'
import StatusMenu from './StatusMenu.vue'
import PersonMenu from './PersonMenu.vue'
import IssueRow from './IssueRow.vue'
import InlineCreate from './InlineCreate.vue'
import Dropdown from './Dropdown.vue'
import { CATEGORY_META, CHILD_TYPES, FIELD_LABEL, PRIORITIES, PRIORITY_META, TYPE_META, ago, ancestors, categoryOf, parentOptions, rollup } from './meta'
import { useWorkspace } from './workspace'

const ws = useWorkspace()
const task = computed(() => (ws.issueKey ? ws.byKey.get(ws.issueKey) || null : null))
const manage = computed(() => ws.canManage)
const trail = computed(() => (task.value ? ancestors(task.value, ws.byId).reverse() : []))
const kids = computed(() => (task.value ? ws.children.get(task.value.id) || [] : []))
const childTypes = computed<ItemType[]>(() => (task.value ? CHILD_TYPES[task.value.type] : []))
const progress = computed(() => (task.value ? rollup(task.value.id, ws.children) : null))
const blockers = computed(() => (task.value ? task.value.blocked_by.map((id) => ws.byId.get(id)).filter((t): t is Task => !!t) : []))
const blocking = computed(() => (task.value ? ws.tasks.filter((t) => t.blocked_by.includes(task.value!.id)) : []))
const parents = computed(() => (task.value ? parentOptions(task.value.type, ws.tasks, task.value) : []))
const isContainer = computed(() => task.value?.type === 'module' || task.value?.type === 'epic')

const save = (data: Record<string, unknown>) => task.value && ws.patch(task.value, data)

// ───── summary ─────
const editingTitle = ref(false)
const titleDraft = ref('')
const titleInput = ref<HTMLInputElement | null>(null)
async function editTitle() {
  if (!manage.value || !task.value) return
  titleDraft.value = task.value.title
  editingTitle.value = true
  await nextTick()
  titleInput.value?.select()
}
function commitTitle() {
  if (!editingTitle.value) return
  editingTitle.value = false
  const t = titleDraft.value.trim()
  if (t && t !== task.value?.title) save({ title: t })
}

// ───── description ─────
const editingDesc = ref(false)
const descDraft = ref('')
function editDesc() {
  descDraft.value = task.value?.description || ''
  editingDesc.value = true
}
async function commitDesc() {
  if (descDraft.value !== task.value?.description && !(await save({ description: descDraft.value }))) return
  editingDesc.value = false
}

// ───── labels ─────
const labelDraft = ref('')
function addLabel() {
  const l = labelDraft.value.trim().replace(/,$/, '')
  labelDraft.value = ''
  if (l && task.value && !task.value.labels.includes(l)) save({ labels: [...task.value.labels, l] })
}
const dropLabel = (l: string) => task.value && save({ labels: task.value.labels.filter((x) => x !== l) })

// ───── links ─────
const blockerSearch = ref('')
const blockerOptions = computed(() => {
  const q = blockerSearch.value.toLowerCase()
  return ws.tasks
    .filter((t) => t.id !== task.value?.id && !task.value?.blocked_by.includes(t.id) && `${t.key} ${t.title}`.toLowerCase().includes(q))
    .slice(0, 30)
})
const addBlocker = (t: Task) => task.value && save({ blocked_by: [...task.value.blocked_by, t.id] })
const dropBlocker = (t: Task) => task.value && save({ blocked_by: task.value.blocked_by.filter((id) => id !== t.id) })
const impediment = ref('')
watch(
  () => task.value?.blocker,
  (b) => (impediment.value = b || ''),
  { immediate: true },
)
const commitImpediment = () => impediment.value.trim() !== (task.value?.blocker || '') && save({ blocker: impediment.value.trim() })

// ───── activity ─────
const tab = ref<'comments' | 'history'>('comments')
const comments = ref<Comment[]>([])
const history = ref<Activity[]>([])
const activityError = ref('')
const draft = ref('')
const posting = ref(false)
async function loadActivity(id: number) {
  activityError.value = ''
  try {
    const [c, h] = await Promise.all([
      api.get<Comment[]>('pm/comments/', { params: { task: id } }),
      api.get<Activity[]>(`pm/tasks/${id}/activity/`),
    ])
    if (task.value?.id !== id) return
    comments.value = c.data.slice().reverse()
    history.value = h.data
  } catch {
    activityError.value = 'Could not load the activity for this issue.'
  }
}
watch(
  () => task.value?.id,
  (id) => {
    comments.value = []
    history.value = []
    editingTitle.value = editingDesc.value = false
    draft.value = ''
    if (id) loadActivity(id)
  },
  { immediate: true },
)
// a field edit adds history rows: refresh them when the issue changes
watch(
  () => task.value?.updated_at,
  (now, before) => before && now !== before && task.value && tab.value === 'history' && loadActivity(task.value.id),
)
async function postComment() {
  if (!draft.value.trim() || !task.value) return
  posting.value = true
  try {
    await api.post('pm/comments/', { task: task.value.id, body: draft.value })
    draft.value = ''
    task.value.comment_count = (task.value.comment_count || 0) + 1
    await loadActivity(task.value.id)
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    posting.value = false
  }
}
async function deleteComment(c: Comment) {
  if (!(await confirmDialog({ title: 'Delete comment?', body: 'This cannot be undone.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`pm/comments/${c.id}/`)
    comments.value = comments.value.filter((x) => x.id !== c.id)
    if (task.value) task.value.comment_count = Math.max((task.value.comment_count || 1) - 1, 0)
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
function describe(a: Activity) {
  if (a.field === 'created') return { verb: `created the ${a.new.toLowerCase()}`, old: '', new: '' }
  if (a.field === 'description') return { verb: 'updated the Description', old: '', new: '' }
  return { verb: `changed ${FIELD_LABEL[a.field] || a.field}`, old: a.old || 'None', new: a.new || 'None' }
}

async function copyLink() {
  if (!task.value) return
  const url = `${location.origin}${ws.base}?issue=${task.value.key}`
  try {
    await navigator.clipboard.writeText(url)
    toast.success('Link copied.')
  } catch {
    toast.info(url)
  }
}
const fmt = (iso?: string) =>
  iso ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kathmandu' }).format(new Date(iso)) : ''
const dateValue = (e: Event) => (e.target as HTMLInputElement).value || null
</script>

<template>
  <Modal :open="!!ws.issueKey" :title="task ? `${task.key} · ${task.title}` : ws.issueKey" width="max-w-6xl" @close="ws.closeIssue()">
    <div v-if="!task" class="py-10 text-center text-sm text-ink/60">
      {{ ws.loading ? 'Loading issue…' : `${ws.issueKey} isn’t in this project, or you can’t see it.` }}
    </div>
    <div v-else class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <!-- main column -->
      <div class="min-w-0">
        <nav aria-label="Issue hierarchy" class="flex min-w-0 flex-wrap items-center gap-1 text-xs text-ink/60">
          <template v-for="a in trail" :key="a.id">
            <button type="button" class="inline-flex max-w-[14rem] min-w-0 items-center gap-1 rounded px-1 py-0.5 hover:bg-panel hover:text-ink" @click="ws.go(a)">
              <TypeIcon :type="a.type" :size="14" /><span class="truncate">{{ a.title }}</span>
            </button>
            <span aria-hidden="true">/</span>
          </template>
          <span class="inline-flex items-center gap-1 px-1"><TypeIcon :type="task.type" :size="14" /><span class="font-mono">{{ task.key }}</span></span>
        </nav>

        <input
          v-if="editingTitle"
          ref="titleInput"
          v-model="titleDraft"
          class="input mt-3 font-display !text-2xl font-medium"
          maxlength="200"
          aria-label="Summary"
          @keydown.enter.prevent="commitTitle"
          @keydown.esc.stop.prevent="editingTitle = false"
          @blur="commitTitle"
        />
        <h2 v-else class="mt-3">
          <button
            type="button"
            class="w-full rounded-md px-1 py-0.5 text-left font-display text-2xl leading-snug font-medium break-words"
            :class="manage ? 'hover:bg-panel/70' : 'cursor-default'"
            :aria-label="manage ? `Summary: ${task.title}. Edit` : undefined"
            @click="editTitle"
          >
            {{ task.title }}
          </button>
        </h2>

        <div class="mt-3 flex flex-wrap gap-2">
          <button v-if="manage && childTypes.length" type="button" class="btn-ghost btn-sm" @click="ws.openCreate({ type: childTypes[0], parent: task.id, sprint: task.type === 'story' ? task.sprint : null })">
            + Add {{ TYPE_META[childTypes[0]!].label.toLowerCase() }}
          </button>
          <RouterLink v-if="isContainer" :to="ws.pathOf(task)" class="btn-ghost btn-sm">Open {{ TYPE_META[task.type].label.toLowerCase() }} page →</RouterLink>
          <button type="button" class="btn-ghost btn-sm" @click="copyLink">Copy link</button>
        </div>

        <!-- description -->
        <section class="mt-6" aria-labelledby="iss-desc">
          <div class="mb-2 flex items-center justify-between">
            <h3 id="iss-desc" class="text-sm font-semibold">Description</h3>
            <button v-if="manage && !editingDesc && task.description" type="button" class="text-xs text-river hover:underline" @click="editDesc">Edit</button>
          </div>
          <div v-if="editingDesc" class="grid grid-cols-1 gap-2">
            <textarea v-model="descDraft" class="input min-h-40 font-mono text-[13px]" rows="8" aria-label="Description (Markdown)" @keydown.ctrl.enter="commitDesc" @keydown.meta.enter="commitDesc" @keydown.esc.stop="editingDesc = false" />
            <div class="flex items-center gap-2">
              <button type="button" class="btn-ink btn-sm" @click="commitDesc">Save</button>
              <button type="button" class="btn-ghost btn-sm" @click="editingDesc = false">Cancel</button>
              <span class="ml-auto text-[11px] text-ink/50">Markdown · Ctrl+Enter saves</span>
            </div>
          </div>
          <button v-else-if="!task.description && manage" type="button" class="w-full rounded-md border border-dashed border-ink/20 px-3 py-4 text-left text-sm text-ink/50 hover:bg-panel/50" @click="editDesc">
            Add a description…
          </button>
          <MarkdownView v-else :source="task.description" empty="No description." />
        </section>

        <!-- child issues -->
        <section v-if="childTypes.length" class="mt-7" aria-labelledby="iss-children">
          <div class="mb-2 flex items-center gap-3">
            <h3 id="iss-children" class="text-sm font-semibold">{{ isContainer ? 'Contents' : 'Child issues' }}</h3>
            <template v-if="progress && progress.total">
              <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-ink/10"><span class="block h-full rounded-full bg-moss" :style="{ width: `${progress.percent}%` }" /></span>
              <span class="readout text-xs text-ink/60">{{ progress.percent }}% done</span>
            </template>
          </div>
          <ul class="divide-y divide-ink/5 overflow-hidden rounded-lg border border-ink/10">
            <li v-for="k in kids" :key="k.id" class="cursor-pointer hover:bg-panel/40"><IssueRow :task="k" :show-parent="false" /></li>
            <li v-if="!kids.length && !manage" class="px-3 py-3 text-sm text-ink/55">Nothing here yet.</li>
          </ul>
          <InlineCreate class="mt-1" :types="childTypes" :defaults="{ parent: task.id, sprint: task.type === 'story' ? task.sprint : null }" :label="`Create ${childTypes.map((t) => TYPE_META[t].label.toLowerCase()).join(' / ')}`" />
        </section>

        <!-- links -->
        <section class="mt-7" aria-labelledby="iss-links">
          <div class="mb-2 flex items-center justify-between">
            <h3 id="iss-links" class="text-sm font-semibold">Linked issues</h3>
            <Dropdown v-if="manage" label="Add a blocking issue" :width="320" align="right">
              <template #trigger="{ toggle, open }">
                <button type="button" class="text-xs text-river hover:underline" aria-haspopup="menu" :aria-expanded="open" @click="toggle">+ Blocked by…</button>
              </template>
              <template #default="{ close }">
                <div class="px-2 pt-1 pb-1.5"><input v-model="blockerSearch" class="input !py-1 text-sm" placeholder="Search issues…" aria-label="Search issues" /></div>
                <button
                  v-for="o in blockerOptions"
                  :key="o.id"
                  type="button"
                  role="menuitem"
                  class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none"
                  @click="addBlocker(o), close()"
                >
                  <TypeIcon :type="o.type" /><span class="font-mono text-[11px] text-ink/55">{{ o.key }}</span><span class="truncate">{{ o.title }}</span>
                </button>
                <p v-if="!blockerOptions.length" class="px-3 py-2 text-sm text-ink/55">No matching issues.</p>
              </template>
            </Dropdown>
          </div>
          <div class="grid grid-cols-1 gap-3 text-sm">
            <div v-if="blockers.length">
              <p class="ledger-label mb-1">is blocked by</p>
              <ul class="divide-y divide-ink/5 rounded-lg border border-ink/10">
                <li v-for="b in blockers" :key="b.id" class="flex items-center gap-2 px-3 py-1.5">
                  <TypeIcon :type="b.type" />
                  <button type="button" class="font-mono text-[11px] text-ink/60 hover:underline" @click="ws.go(b)">{{ b.key }}</button>
                  <button type="button" class="min-w-0 flex-1 truncate text-left hover:text-river" @click="ws.go(b)">{{ b.title }}</button>
                  <span class="rounded px-1.5 py-0.5 font-mono text-[10px] uppercase" :class="CATEGORY_META[categoryOf(b.status)].lozenge">{{ CATEGORY_META[categoryOf(b.status)].label }}</span>
                  <button v-if="manage" type="button" class="px-1 text-ink/45 hover:text-rust" :aria-label="`Remove link to ${b.key}`" @click="dropBlocker(b)">✕</button>
                </li>
              </ul>
            </div>
            <div v-if="blocking.length">
              <p class="ledger-label mb-1">blocks</p>
              <ul class="divide-y divide-ink/5 rounded-lg border border-ink/10">
                <li v-for="b in blocking" :key="b.id" class="flex items-center gap-2 px-3 py-1.5">
                  <TypeIcon :type="b.type" />
                  <button type="button" class="font-mono text-[11px] text-ink/60 hover:underline" @click="ws.go(b)">{{ b.key }}</button>
                  <button type="button" class="min-w-0 flex-1 truncate text-left hover:text-river" @click="ws.go(b)">{{ b.title }}</button>
                </li>
              </ul>
            </div>
            <label class="field">
              <span class="ledger-label">Impediment (what’s in the way)</span>
              <input
                v-model="impediment"
                class="input"
                maxlength="300"
                :readonly="!manage"
                :placeholder="manage ? 'e.g. Waiting on client data — leave empty when clear' : 'None'"
                @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
                @blur="commitImpediment"
              />
            </label>
          </div>
        </section>

        <!-- activity -->
        <section class="mt-7" aria-labelledby="iss-activity">
          <div class="mb-3 flex items-center gap-4">
            <h3 id="iss-activity" class="text-sm font-semibold">Activity</h3>
            <div role="tablist" aria-label="Activity" class="flex gap-1 text-xs">
              <button
                v-for="t in (['comments', 'history'] as const)"
                :key="t"
                type="button"
                role="tab"
                :aria-selected="tab === t"
                class="rounded-full px-2.5 py-1 capitalize"
                :class="tab === t ? 'bg-ink text-paper' : 'text-ink/60 hover:bg-panel'"
                @click="(tab = t), task && t === 'history' && loadActivity(task.id)"
              >
                {{ t }}<span v-if="t === 'comments' && comments.length"> · {{ comments.length }}</span>
              </button>
            </div>
          </div>
          <p v-if="activityError" role="alert" class="mb-3 text-sm text-rust">{{ activityError }} <button type="button" class="underline" @click="loadActivity(task.id)">Retry</button></p>
          <template v-if="tab === 'comments'">
            <form class="mb-5 flex gap-3" @submit.prevent="postComment">
              <Avatar :name="ws.people.find((p) => p.id === ws.me)?.name || 'Me'" :size="30" />
              <div class="grid grid-cols-1 min-w-0 flex-1 gap-2">
                <label><span class="sr-only">Add a comment</span>
                  <textarea v-model="draft" class="input" rows="2" maxlength="10000" placeholder="Add a comment… (Markdown, Ctrl+Enter to post)" @keydown.ctrl.enter="postComment" @keydown.meta.enter="postComment" />
                </label>
                <div v-if="draft.trim()" class="flex gap-2">
                  <button class="btn-ink btn-sm" :disabled="posting">{{ posting ? 'Posting…' : 'Save' }}</button>
                  <button type="button" class="btn-ghost btn-sm" @click="draft = ''">Cancel</button>
                </div>
              </div>
            </form>
            <p v-if="!comments.length" class="text-sm text-ink/55">No comments yet.</p>
            <article v-for="c in comments" :key="c.id" class="mb-4 flex gap-3">
              <Avatar :name="c.author_name" :size="30" />
              <div class="min-w-0 flex-1">
                <p class="text-xs">
                  <span class="font-medium">{{ c.author_name }}</span>
                  <time class="ml-2 text-ink/50" :datetime="c.created_at" :title="fmt(c.created_at)">{{ ago(c.created_at) }}</time>
                  <button v-if="c.author === ws.me || manage" type="button" class="ml-2 text-ink/45 hover:text-rust" @click="deleteComment(c)">Delete</button>
                </p>
                <MarkdownView class="mt-1" :source="c.body" />
              </div>
            </article>
          </template>
          <ol v-else class="grid grid-cols-1 gap-3">
            <li v-if="!history.length" class="text-sm text-ink/55">No history recorded yet. Changes made from now on appear here.</li>
            <li v-for="a in history" :key="a.id" class="flex gap-3 text-sm">
              <Avatar :name="a.actor_name || 'Someone'" :size="26" />
              <div class="min-w-0 flex-1">
                <p><span class="font-medium">{{ a.actor_name || 'Someone' }}</span> {{ describe(a).verb }} <time class="ml-1 text-xs text-ink/50" :title="fmt(a.at)">{{ ago(a.at) }}</time></p>
                <p v-if="describe(a).old || describe(a).new" class="mt-0.5 flex min-w-0 flex-wrap items-center gap-2 text-xs">
                  <span class="max-w-[45%] truncate rounded bg-ink/[0.06] px-1.5 py-0.5 text-ink/65 line-through decoration-ink/30">{{ describe(a).old }}</span>
                  <span aria-hidden="true">→</span><span class="sr-only">to</span>
                  <span class="max-w-[45%] truncate rounded bg-river/10 px-1.5 py-0.5">{{ describe(a).new }}</span>
                </p>
              </div>
            </li>
          </ol>
        </section>
      </div>

      <!-- details sidebar -->
      <aside class="min-w-0 lg:sticky lg:top-16 lg:self-start">
        <div class="flex items-center gap-2">
          <StatusMenu :task="task" size="md" />
          <Dropdown v-if="manage" label="More actions" :width="190" align="right">
            <template #trigger="{ toggle, open }">
              <button type="button" class="ml-1 rounded-md px-2 py-1.5 text-ink/60 hover:bg-panel" aria-label="More actions" aria-haspopup="menu" :aria-expanded="open" @click="toggle">•••</button>
            </template>
            <template #default="{ close }">
              <button type="button" role="menuitem" class="block w-full px-3 py-1.5 text-left hover:bg-panel focus-visible:bg-panel focus-visible:outline-none" @click="close(), copyLink()">Copy link</button>
              <button type="button" role="menuitem" class="block w-full px-3 py-1.5 text-left text-rust hover:bg-panel focus-visible:bg-panel focus-visible:outline-none" @click="close(false), ws.remove(task)">Delete {{ TYPE_META[task.type].label.toLowerCase() }}</button>
            </template>
          </Dropdown>
        </div>

        <dl class="mt-4 rounded-xl border border-ink/10 text-sm">
          <p class="border-b border-ink/10 px-4 py-2.5 text-xs font-semibold">Details</p>
          <div class="grid grid-cols-1 gap-0.5 px-4 py-2 [&>div]:grid [&>div]:min-h-9 [&>div]:grid-cols-[6.5rem_minmax(0,1fr)] [&>div]:items-center [&>div]:gap-2 [&_dt]:text-xs [&_dt]:text-ink/55">
            <div>
              <dt>Assignee</dt>
              <dd><PersonMenu :value="task.assignee" :disabled="!manage" show-name :size="24" @change="(id) => save({ assignee: id })" /></dd>
            </div>
            <div>
              <dt>Reporter</dt>
              <dd class="flex min-w-0 items-center gap-2"><Avatar v-if="task.created_by_name" :name="task.created_by_name" :size="24" /><span class="truncate">{{ task.created_by_name || '—' }}</span></dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd class="flex items-center gap-1.5">
                <PriorityIcon :priority="task.priority" />
                <select v-if="manage" :value="task.priority" class="input !w-auto !border-transparent !bg-transparent !px-1 !py-1 hover:!border-ink/15" aria-label="Priority" @change="save({ priority: ($event.target as HTMLSelectElement).value })">
                  <option v-for="p in PRIORITIES" :key="p" :value="p">{{ PRIORITY_META[p]!.label }}</option>
                </select>
                <span v-else>{{ PRIORITY_META[task.priority]?.label }}</span>
              </dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd class="flex min-w-0 items-center gap-1.5">
                <TypeIcon :type="task.type" />
                <select v-if="manage" :value="task.type" class="input !w-auto !border-transparent !bg-transparent !px-1 !py-1 hover:!border-ink/15" aria-label="Issue type" @change="save({ type: ($event.target as HTMLSelectElement).value })">
                  <option v-for="(m, k) in TYPE_META" :key="k" :value="k">{{ m.label }}</option>
                </select>
                <span v-else>{{ TYPE_META[task.type].label }}</span>
              </dd>
            </div>
            <div v-if="task.type !== 'module'">
              <dt>Parent</dt>
              <dd class="min-w-0">
                <select v-if="manage" :value="task.parent ?? ''" class="input !py-1 text-sm" aria-label="Parent" @change="save({ parent: Number(($event.target as HTMLSelectElement).value) || null })">
                  <option value="">None</option>
                  <option v-for="p in parents" :key="p.id" :value="p.id">{{ TYPE_META[p.type].label }} · {{ p.key }} {{ p.title }}</option>
                </select>
                <span v-else class="block truncate">{{ task.parent ? ws.byId.get(task.parent)?.title : 'None' }}</span>
              </dd>
            </div>
            <div v-if="!isContainer">
              <dt>Sprint</dt>
              <dd class="min-w-0">
                <select v-if="manage" :value="task.sprint ?? ''" class="input !py-1 text-sm" aria-label="Sprint" @change="save({ sprint: Number(($event.target as HTMLSelectElement).value) || null })">
                  <option value="">Backlog</option>
                  <option v-for="s in ws.sprints.filter((x) => x.status !== 'completed' || x.id === task!.sprint)" :key="s.id" :value="s.id" :disabled="s.status === 'completed'">
                    {{ s.name }}{{ s.status === 'active' ? ' (active)' : s.status === 'completed' ? ' (completed)' : '' }}
                  </option>
                </select>
                <span v-else>{{ ws.sprints.find((s) => s.id === task!.sprint)?.name || 'Backlog' }}</span>
              </dd>
            </div>
            <div v-if="!isContainer">
              <dt>Story points</dt>
              <dd>
                <input
                  v-if="manage"
                  :value="task.estimate ?? ''"
                  type="number"
                  min="0"
                  max="999"
                  class="input !w-24 !py-1 text-sm"
                  aria-label="Story points"
                  placeholder="None"
                  @change="save({ estimate: ($event.target as HTMLInputElement).value === '' ? null : Number(($event.target as HTMLInputElement).value) })"
                />
                <span v-else>{{ task.estimate ?? 'None' }}</span>
              </dd>
            </div>
            <div>
              <dt>Labels</dt>
              <dd class="flex min-w-0 flex-wrap items-center gap-1 py-1">
                <span v-for="l in task.labels" :key="l" class="inline-flex max-w-full items-center gap-1 rounded border border-ink/15 px-1.5 py-0.5 text-xs">
                  <span class="truncate">{{ l }}</span>
                  <button v-if="manage" type="button" class="text-ink/45 hover:text-rust" :aria-label="`Remove label ${l}`" @click="dropLabel(l)">✕</button>
                </span>
                <input v-if="manage && task.labels.length < 12" v-model="labelDraft" class="min-w-16 flex-1 bg-transparent py-0.5 text-xs outline-none placeholder:text-ink/40" placeholder="+ label" maxlength="40" aria-label="Add label" @keydown.enter.prevent="addLabel" @keydown="(e: KeyboardEvent) => e.key === ',' && (e.preventDefault(), addLabel())" @blur="labelDraft.trim() && addLabel()" />
                <span v-if="!manage && !task.labels.length" class="text-ink/50">None</span>
              </dd>
            </div>
            <div>
              <dt>Milestone</dt>
              <dd class="min-w-0">
                <select v-if="manage" :value="task.milestone ?? ''" class="input !py-1 text-sm" aria-label="Milestone" @change="save({ milestone: Number(($event.target as HTMLSelectElement).value) || null })">
                  <option value="">None</option>
                  <option v-for="m in ws.milestones" :key="m.id" :value="m.id">{{ m.title }}</option>
                </select>
                <span v-else class="block truncate">{{ ws.milestones.find((m) => m.id === task!.milestone)?.title || 'None' }}</span>
              </dd>
            </div>
            <div>
              <dt>Start date</dt>
              <dd>
                <input v-if="manage" :value="task.start_date || ''" type="date" class="input !py-1 text-sm" aria-label="Start date" @change="save({ start_date: dateValue($event) })" />
                <span v-else>{{ task.start_date ? dateLabel(task.start_date) : 'None' }}</span>
              </dd>
            </div>
            <div>
              <dt>Due date</dt>
              <dd>
                <input v-if="manage" :value="task.due_date || ''" type="date" :min="task.start_date || undefined" class="input !py-1 text-sm" aria-label="Due date" @change="save({ due_date: dateValue($event) })" />
                <span v-else>{{ task.due_date ? dateLabel(task.due_date) : 'None' }}</span>
              </dd>
            </div>
          </div>
        </dl>
        <p class="mt-3 px-1 text-[11px] leading-relaxed text-ink/50">
          Created {{ fmt(task.created_at) }}<br />Updated {{ task.updated_at ? ago(task.updated_at) : '' }}
        </p>
        <p v-if="!manage" class="mt-3 rounded-lg bg-panel/60 px-3 py-2 text-xs text-ink/65">
          {{ ws.canMove(task) ? 'You can change the status of your own issues. ' : '' }}Ask the project lead to edit other details.
        </p>
      </aside>
    </div>
  </Modal>
</template>
