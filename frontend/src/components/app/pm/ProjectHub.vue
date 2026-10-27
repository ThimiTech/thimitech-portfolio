<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/api'
import { confirmDialog } from '../ui/confirm'
import { errorMessage, dateLabel, detectLinkKind, linkLabel, LINK_KINDS, type Project, type Milestone, type ProjectLink } from './pm'
const props = defineProps<{ project: Project; milestones: Milestone[]; links: ProjectLink[] }>()
const emit = defineEmits<{ saved: [] }>()
const error = ref('')
const busy = ref(false)
const milestone = reactive({ title: '', due_date: '' })
const link = reactive({ title: '', url: '', kind: 'web', public: false })
const kindTouched = ref(false)
watch(
  () => link.url,
  (url) => {
    if (!kindTouched.value) link.kind = detectLinkKind(url)
    if (!link.title && /^https?:\/\/[^/]+/.test(url)) {
      try {
        link.title = new URL(url).hostname.replace(/^www\./, '')
      } catch {
        /* still typing */
      }
    }
  },
)
const grouped = computed(() => {
  const order = LINK_KINDS.map((k) => k.id)
  return [...props.links].sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind))
})
async function togglePublic(l: ProjectLink) {
  busy.value = true
  try {
    await api.patch(`pm/links/${l.id}/`, { public: !l.public })
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function add(kind: 'milestones' | 'links') {
  busy.value = true
  error.value = ''
  try {
    await api.post(`pm/${kind}/`, {
      ...(kind === 'milestones' ? milestone : link),
      project: props.project.id,
    })
    if (kind === 'milestones') Object.assign(milestone, { title: '', due_date: '' })
    else {
      Object.assign(link, { title: '', url: '', kind: 'web', public: false })
      kindTouched.value = false
    }
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function toggle(m: Milestone) {
  busy.value = true
  error.value = ''
  try {
    await api.patch(`pm/milestones/${m.id}/`, { completed: !m.completed })
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function remove(kind: string, id: number) {
  if (
    !(await confirmDialog({
      title: 'Remove this item?',
      body: 'This removes the item from the project hub.',
      confirmLabel: 'Remove',
      danger: true,
    }))
  )
    return
  busy.value = true
  error.value = ''
  try {
    await api.delete(`pm/${kind}/${id}/`)
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <div>
    <p v-if="error" role="alert" class="mb-4 text-sm text-rust">{{ error }}</p>
    <div class="grid items-start gap-6 lg:grid-cols-2">
      <section class="panel">
        <div class="panel-head">
          <h3 class="font-medium">Milestones</h3>
          <span class="readout text-xs text-ink/60"
            >{{ milestones.filter((m) => m.completed).length }}/{{ milestones.length }}</span
          >
        </div>
        <div class="panel-body">
          <p v-if="!milestones.length" class="text-sm text-ink/60">
            Set a target your team can work toward.
          </p>
          <div v-for="m in milestones" :key="m.id" class="mb-4 flex items-start gap-3">
            <input
              v-if="project.can_manage"
              type="checkbox"
              :checked="m.completed"
              :aria-label="`Complete ${m.title}`"
              :disabled="busy"
              class="mt-1 accent-ink"
              @change="toggle(m)"
            />
            <div class="min-w-0 flex-1">
              <p class="text-sm" :class="m.completed ? 'line-through text-ink/55' : ''">
                {{ m.title }}
              </p>
              <p class="mt-1 text-xs text-ink/60">
                {{ dateLabel(m.due_date) }} · {{ m.completed ? 'Completed' : 'Open' }}
              </p>
            </div>
            <button
              v-if="project.can_manage"
              class="text-xs text-rust"
              :disabled="busy"
              :aria-label="`Remove milestone ${m.title}`"
              @click="remove('milestones', m.id)"
            >
              Remove
            </button>
          </div>
          <form
            v-if="project.can_manage"
            class="mt-6 grid gap-3 border-t border-ink/10 pt-5"
            @submit.prevent="add('milestones')"
          >
            <label class="field"
              ><span class="ledger-label">Milestone title</span
              ><input v-model="milestone.title" required maxlength="200" class="input" /></label
            ><label class="field"
              ><span class="ledger-label">Target date</span
              ><input v-model="milestone.due_date" type="date" required class="input" /></label
            ><button class="btn-ghost justify-self-start" :disabled="busy">Add milestone</button>
          </form>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head"><h3 class="font-medium">Links, repositories & socials</h3><span class="readout text-xs text-ink/60">{{ links.length }}</span></div>
        <div class="panel-body">
          <p v-if="!links.length" class="text-sm text-ink/60">
            Keep repositories, designs, docs, social pages and live URLs together.
          </p>
          <div v-for="l in grouped" :key="l.id" class="mb-4 flex items-start gap-3">
            <span class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-panel font-mono text-[10px] font-medium uppercase text-ink/70" aria-hidden="true">{{ l.kind.slice(0, 2) }}</span>
            <div class="min-w-0 flex-1">
              <a
                :href="l.url"
                target="_blank"
                rel="noopener noreferrer"
                class="break-words text-sm font-medium hover:text-river"
                >{{ l.title }} ↗</a
              >
              <p class="mt-0.5 truncate text-[11px] text-ink/55">{{ linkLabel(l.kind) }} · {{ l.url.replace(/^https?:\/\//, '') }}</p>
            </div>
            <button
              v-if="project.can_manage"
              class="rounded-full border px-2 py-0.5 text-[10px]"
              :class="l.public ? 'border-moss/40 text-moss' : 'border-ink/15 text-ink/50'"
              :aria-pressed="l.public"
              :aria-label="`Show ${l.title} on the public page`"
              :disabled="busy"
              @click="togglePublic(l)"
            >
              {{ l.public ? 'Public' : 'Internal' }}
            </button>
            <button
              v-if="project.can_manage"
              class="text-xs text-rust"
              :aria-label="`Remove link ${l.title}`"
              :disabled="busy"
              @click="remove('links', l.id)"
            >
              Remove
            </button>
          </div>
          <form
            v-if="project.can_manage"
            class="mt-6 grid gap-3 border-t border-ink/10 pt-5"
            @submit.prevent="add('links')"
          >
            <label class="field"
              ><span class="ledger-label">Link title</span
              ><input v-model="link.title" required maxlength="120" class="input" /></label
            ><label class="field"
              ><span class="ledger-label">URL</span
              ><input
                v-model="link.url"
                required
                type="url"
                pattern="https?://.*"
                class="input"
                placeholder="https://" /></label
            ><label class="field"
              ><span class="ledger-label">Type</span
              ><select v-model="link.kind" class="input" @change="kindTouched = true">
                <option v-for="k in LINK_KINDS" :key="k.id" :value="k.id">{{ k.label }}</option>
              </select></label
            ><label class="flex items-center gap-2 text-sm"
              ><input v-model="link.public" type="checkbox" class="accent-ink" /> Show on public project page</label
            ><button class="btn-ghost justify-self-start" :disabled="busy">Add link</button>
          </form>
        </div>
      </section>
    </div>
  </div>
</template>
