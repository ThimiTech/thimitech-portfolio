<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import { confirmDialog } from '../ui/confirm'
import Modal from '../ui/Modal.vue'
import StatusPill from '../ui/StatusPill.vue'
import Avatar from '../ui/Avatar.vue'
import MarkdownView from './MarkdownView.vue'
import { dateTimeLabel, errorMessage, MEETING_KINDS, toLocalInput, type ActionItem, type Meeting, type Project } from './pm'
const props = defineProps<{ project: Project; meetings: Meeting[]; openId?: number | null }>()
const emit = defineEmits<{ changed: []; wikilink: [target: string] }>()

const TEMPLATES: Record<string, string> = {
  standup: '## Yesterday\n- \n\n## Today\n- \n\n## Blockers\n- ',
  planning: '## Sprint goal\n\n## Capacity\n\n## Committed scope\n- \n\n## Risks\n- ',
  review: '## Demoed\n- \n\n## Feedback\n- \n\n## Not done\n- ',
  retro: '## What went well\n- \n\n## What to improve\n- \n\n## We will try\n- ',
  client: '## Attendees\n\n## Discussion\n\n## Decisions\n- \n\n## Next steps\n- ',
  general: '## Discussion\n\n## Decisions\n- \n\n## Notes\n',
}
const now = Date.now()
const upcoming = computed(() => props.meetings.filter((m) => Date.parse(m.end) >= now && m.status === 'scheduled').reverse())
const past = computed(() => props.meetings.filter((m) => !(Date.parse(m.end) >= now && m.status === 'scheduled')))
const selectedId = ref<number | null>(props.openId ?? upcoming.value[0]?.id ?? past.value[0]?.id ?? null)
watch(() => props.openId, (id) => id && (selectedId.value = id))
const m = computed(() => props.meetings.find((x) => x.id === selectedId.value) || null)
const busy = ref(false)

// agenda / minutes editors
const tab = ref<'agenda' | 'minutes'>('agenda')
const editing = ref(false)
const draft = ref('')
watch([m, tab], () => {
  editing.value = false
  if (m.value && m.value.status === 'done' && tab.value === 'agenda' && m.value.minutes) tab.value = 'minutes'
})
function startEdit() {
  draft.value = m.value![tab.value] || (tab.value === 'minutes' ? TEMPLATES[m.value!.kind] || '' : '')
  editing.value = true
}
async function patch(data: Partial<Meeting>, ok?: string) {
  busy.value = true
  try {
    await api.patch(`pm/meetings/${m.value!.id}/`, data)
    if (ok) toast.success(ok)
    emit('changed')
    return true
  } catch (e) {
    toast.error(errorMessage(e))
    return false
  } finally {
    busy.value = false
  }
}
async function saveText() {
  if (await patch({ [tab.value]: draft.value })) editing.value = false
}

// action items
const newItem = reactive({ text: '', assignee: null as number | null, due: '' })
const items = computed(() => m.value?.action_items || [])
const saveItems = (list: ActionItem[]) => patch({ action_items: list })
function addItem() {
  if (!newItem.text.trim()) return
  saveItems([...items.value, { text: newItem.text.trim(), assignee: newItem.assignee, due: newItem.due || null, task: null, done: false }])
  Object.assign(newItem, { text: '', assignee: null, due: '' })
}
const toggleItem = (i: number) => saveItems(items.value.map((it, j) => (j === i ? { ...it, done: !it.done } : it)))
const dropItem = (i: number) => saveItems(items.value.filter((_, j) => j !== i))
async function toTask(i: number) {
  const it = items.value[i]!
  const column = props.project.boards[0]?.columns[0]?.id
  if (!column) return toast.error('Add a board first.')
  busy.value = true
  try {
    const { data } = await api.post('pm/tasks/', {
      column,
      title: it.text.slice(0, 200),
      description: `From meeting “${m.value!.title}” (${dateTimeLabel(m.value!.start)})`,
      assignee: it.assignee,
      due_date: it.due,
      labels: ['meeting'],
    })
    await saveItems(items.value.map((x, j) => (j === i ? { ...x, task: data.id } : x)))
    toast.success(`Created ${data.key}.`)
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
const personName = (id: number | null) => props.project.people.find((p) => p.id === id)?.name || 'Unassigned'

// schedule / edit
const modal = ref(false)
const form = reactive({ id: 0, title: '', kind: 'general', start: '', duration: 30, location: '', agenda: '', attendees: [] as number[] })
function openForm(meeting?: Meeting) {
  const start = new Date(Math.ceil(Date.now() / 1800000) * 1800000 + 86400000).toISOString()
  Object.assign(
    form,
    meeting
      ? {
          id: meeting.id,
          title: meeting.title,
          kind: meeting.kind,
          start: toLocalInput(meeting.start),
          duration: Math.round((Date.parse(meeting.end) - Date.parse(meeting.start)) / 60000),
          location: meeting.location,
          agenda: meeting.agenda,
          attendees: [...meeting.attendees],
        }
      : { id: 0, title: '', kind: 'general', start: toLocalInput(start), duration: 30, location: '', agenda: '', attendees: props.project.people.map((p) => p.id) },
  )
  modal.value = true
}
async function submit() {
  const start = new Date(form.start)
  const payload = {
    project: props.project.id,
    title: form.title,
    kind: form.kind,
    start: start.toISOString(),
    end: new Date(start.getTime() + form.duration * 60000).toISOString(),
    location: form.location,
    agenda: form.agenda,
    attendees: form.attendees,
  }
  busy.value = true
  try {
    const { data } = form.id ? await api.patch<Meeting>(`pm/meetings/${form.id}/`, payload) : await api.post<Meeting>('pm/meetings/', payload)
    selectedId.value = data.id
    modal.value = false
    toast.success(form.id ? 'Meeting updated.' : 'Meeting scheduled — attendees were notified.')
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
async function remove() {
  if (!(await confirmDialog({ title: 'Delete this meeting?', body: 'Agenda, minutes and action items are removed.', confirmLabel: 'Delete', danger: true }))) return
  try {
    await api.delete(`pm/meetings/${m.value!.id}/`)
    selectedId.value = null
    emit('changed')
  } catch (e) {
    toast.error(errorMessage(e))
  }
}
async function ics() {
  const blob = (await api.get<Blob>(`pm/meetings/${m.value!.id}/ics/`, { responseType: 'blob' })).data
  const href = URL.createObjectURL(blob)
  Object.assign(document.createElement('a'), { href, download: `${m.value!.title}.ics` }).click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
const isUrl = (s: string) => /^https?:\/\//.test(s)
const durationLabel = (x: Meeting) => `${Math.round((Date.parse(x.end) - Date.parse(x.start)) / 60000)} min`
</script>
<template>
  <div class="grid gap-5 lg:grid-cols-[300px_1fr]">
    <aside class="grid content-start gap-4">
      <button class="btn-primary" @click="openForm()">Schedule meeting</button>
      <section v-for="[label, list] in [['Upcoming', upcoming], ['Past & held', past]] as const" :key="label">
        <p class="ledger-label mb-2 px-1">{{ label }} · {{ list.length }}</p>
        <p v-if="!list.length" class="px-1 text-xs text-ink/50">{{ label === 'Upcoming' ? 'Nothing scheduled.' : 'No meetings yet.' }}</p>
        <button
          v-for="x in list"
          :key="x.id"
          class="mb-1.5 block w-full rounded-lg border px-3 py-2.5 text-left transition-colors"
          :class="x.id === selectedId ? 'border-ink/25 bg-sheet shadow-sm' : 'border-transparent hover:bg-panel/60'"
          @click="selectedId = x.id"
        >
          <span class="flex items-center justify-between gap-2 font-mono text-[10px] uppercase text-ink/50">
            {{ MEETING_KINDS[x.kind] }}<span v-if="x.status === 'cancelled'" class="text-rust">cancelled</span>
          </span>
          <span class="mt-0.5 block truncate text-sm font-medium" :class="x.status === 'cancelled' ? 'line-through text-ink/50' : ''">{{ x.title }}</span>
          <span class="mt-0.5 block text-xs text-ink/60">{{ dateTimeLabel(x.start) }}</span>
        </button>
      </section>
    </aside>

    <div v-if="!m" class="panel grid place-items-center p-12 text-center text-sm text-ink/60">
      <div>
        <p class="font-display text-lg text-ink">Meetings that leave a trail</p>
        <p class="mt-1">Schedule stand-ups, planning and client calls. Keep the agenda, minutes and action items together.</p>
      </div>
    </div>
    <article v-else class="panel min-w-0">
      <header class="panel-head flex-wrap !items-start">
        <div class="min-w-0">
          <p class="ledger-label">{{ MEETING_KINDS[m.kind] }}</p>
          <h2 class="mt-1 font-display text-2xl font-medium">{{ m.title }}</h2>
          <p class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink/65">
            <span>{{ dateTimeLabel(m.start) }} · {{ durationLabel(m) }}</span>
            <a v-if="isUrl(m.location)" :href="m.location" target="_blank" rel="noopener noreferrer" class="text-river underline">Join call ↗</a>
            <span v-else-if="m.location">@ {{ m.location }}</span>
            <StatusPill :status="m.status" :label="m.status === 'done' ? 'held' : m.status" />
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button class="btn-ghost btn-sm" @click="ics">Add to calendar</button>
          <button v-if="m.status === 'scheduled'" class="btn-ghost btn-sm" :disabled="busy" @click="patch({ status: 'done' }, 'Marked as held.')">Mark held</button>
          <button class="btn-ghost btn-sm" @click="openForm(m)">Edit</button>
          <button v-if="m.status === 'scheduled'" class="btn-ghost btn-sm" :disabled="busy" @click="patch({ status: 'cancelled' }, 'Meeting cancelled.')">Cancel</button>
          <button class="btn-danger btn-sm" @click="remove">Delete</button>
        </div>
      </header>
      <div class="flex flex-wrap items-center gap-2 border-b border-dashed border-ink/15 px-5 py-3">
        <span class="ledger-label mr-1">Attendees</span>
        <span v-for="p in m.attendees_detail" :key="p.id" class="flex items-center gap-1.5 rounded-full bg-panel/70 py-0.5 pl-0.5 pr-2.5 text-xs">
          <Avatar :name="p.name" :size="20" />{{ p.name }}
        </span>
        <span v-if="!m.attendees_detail.length" class="text-xs text-ink/50">No one invited.</span>
      </div>
      <div class="grid gap-0 xl:grid-cols-[1fr_320px]">
        <section class="min-w-0 p-5 xl:border-r xl:border-ink/10">
          <div class="mb-4 flex items-center gap-1">
            <button v-for="t in ['agenda', 'minutes'] as const" :key="t" class="rounded-full px-3 py-1 text-sm capitalize" :class="tab === t ? 'bg-ink text-paper' : 'text-ink/60 hover:bg-panel'" @click="tab = t">{{ t }}</button>
            <button v-if="!editing" class="btn-ghost btn-sm ml-auto" @click="startEdit">{{ m[tab] ? 'Edit' : tab === 'minutes' ? 'Take minutes' : 'Write agenda' }}</button>
          </div>
          <template v-if="editing">
            <label class="sr-only" :for="`mt-${tab}`">{{ tab }}</label>
            <textarea :id="`mt-${tab}`" v-model="draft" rows="14" class="input font-mono text-[13px] leading-6" placeholder="Markdown. Link notes and docs with [[Title]]." />
            <div class="mt-3 flex justify-end gap-2">
              <button class="btn-ghost btn-sm" @click="editing = false">Discard</button>
              <button class="btn-ink btn-sm" :disabled="busy" @click="saveText">Save {{ tab }}</button>
            </div>
          </template>
          <MarkdownView v-else :source="m[tab]" :empty="tab === 'minutes' ? 'No minutes recorded yet.' : 'No agenda yet.'" @wikilink="emit('wikilink', $event)" />
        </section>
        <section class="p-5">
          <h3 class="ledger-label mb-3">Action items · {{ items.filter((i) => i.done).length }}/{{ items.length }}</h3>
          <ul class="grid gap-2">
            <li v-for="(it, i) in items" :key="i" class="group rounded-lg border border-ink/10 p-2.5">
              <div class="flex items-start gap-2">
                <input type="checkbox" class="mt-1 accent-ink" :checked="it.done" :disabled="busy" :aria-label="`Done: ${it.text}`" @change="toggleItem(i)" />
                <p class="flex-1 text-sm" :class="it.done ? 'text-ink/50 line-through' : ''">{{ it.text }}</p>
                <button class="text-xs text-ink/40 opacity-0 hover:text-rust group-hover:opacity-100 focus:opacity-100" :aria-label="`Remove ${it.text}`" @click="dropItem(i)">✕</button>
              </div>
              <p class="mt-1.5 flex flex-wrap items-center gap-2 pl-6 text-[11px] text-ink/55">
                <span>{{ personName(it.assignee) }}</span><span v-if="it.due">· due {{ it.due }}</span>
                <span v-if="it.task" class="font-mono text-moss">→ {{ project.key }}-{{ it.task }}</span>
                <button v-else-if="project.can_manage" class="ml-auto text-river hover:underline" :disabled="busy" @click="toTask(i)">Make task</button>
              </p>
            </li>
          </ul>
          <form class="mt-3 grid gap-2" @submit.prevent="addItem">
            <label class="field"><span class="sr-only">New action item</span><input v-model="newItem.text" maxlength="500" class="input" placeholder="Add an action item…" /></label>
            <div class="flex gap-2">
              <label class="field flex-1"><span class="sr-only">Owner</span>
                <select v-model="newItem.assignee" class="input !py-1 text-xs"><option :value="null">Owner…</option><option v-for="p in project.people" :key="p.id" :value="p.id">{{ p.name }}</option></select>
              </label>
              <label class="field"><span class="sr-only">Due</span><input v-model="newItem.due" type="date" class="input !py-1 text-xs" /></label>
              <button class="btn-ghost btn-sm" :disabled="busy || !newItem.text.trim()">Add</button>
            </div>
          </form>
        </section>
      </div>
      <p class="border-t border-dashed border-ink/15 px-5 py-2 text-[11px] text-ink/50">Organised by {{ m.created_by_name }}</p>
    </article>

    <Modal :open="modal" :title="form.id ? 'Edit meeting' : 'Schedule a meeting'" width="max-w-xl" @close="modal = false">
      <form class="grid gap-4" @submit.prevent="submit">
        <label class="field"><span class="ledger-label">Title</span><input v-model="form.title" required maxlength="200" class="input" /></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"><span class="ledger-label">Type</span><select v-model="form.kind" class="input"><option v-for="(l, k) in MEETING_KINDS" :key="k" :value="k">{{ l }}</option></select></label>
          <label class="field"><span class="ledger-label">Duration</span><select v-model.number="form.duration" class="input"><option v-for="d in [15, 30, 45, 60, 90, 120, 180]" :key="d" :value="d">{{ d }} min</option></select></label>
        </div>
        <label class="field"><span class="ledger-label">Starts</span><input v-model="form.start" type="datetime-local" required class="input" /></label>
        <label class="field"><span class="ledger-label">Location or call link</span><input v-model="form.location" maxlength="300" class="input" placeholder="Room 2, or https://meet.google.com/…" /></label>
        <fieldset>
          <legend class="ledger-label mb-2">Attendees</legend>
          <div class="grid max-h-40 gap-1.5 overflow-y-auto sm:grid-cols-2">
            <label v-for="p in project.people" :key="p.id" class="flex items-center gap-2 text-sm"><input v-model="form.attendees" type="checkbox" :value="p.id" class="accent-ink" />{{ p.name }}</label>
          </div>
        </fieldset>
        <label class="field"><span class="ledger-label">Agenda</span><textarea v-model="form.agenda" rows="4" class="input font-mono text-[13px]" placeholder="- Topic one&#10;- Topic two" /></label>
        <button class="btn-ink justify-self-end" :disabled="busy">{{ form.id ? 'Save changes' : 'Schedule & notify' }}</button>
      </form>
    </Modal>
  </div>
</template>
