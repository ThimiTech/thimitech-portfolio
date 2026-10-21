<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/api'
import { useAuth } from '@/stores/auth'
import Modal from '@/components/app/ui/Modal.vue'
import PageHeader from '@/components/app/ui/PageHeader.vue'
import EmptyState from '@/components/app/ui/EmptyState.vue'
import LoadError from '@/components/app/org/LoadError.vue'
import { toast } from '@/components/app/ui/toast'
import { errorMessage, dateLabel, type Project, type Summary } from '@/components/app/pm/pm'

const { hasRole } = useAuth()
const projects = ref<Project[]>([])
const summary = ref<Summary | null>(null)
const loading = ref(true)
const error = ref('')
const search = ref('')
const showArchived = ref(false)
const modal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = reactive({ name: '', key: '', description: '', start_date: '', due_date: '' })
const filtered = computed(() =>
  projects.value.filter(
    (p) =>
      p.archived === showArchived.value &&
      `${p.name} ${p.key}`.toLowerCase().includes(search.value.toLowerCase()),
  ),
)
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [p, s] = await Promise.all([
      api.get<Project[]>('pm/projects/'),
      api.get<Summary>('pm/summary/'),
    ])
    projects.value = p.data
    summary.value = s.data
  } catch {
    error.value = 'Could not load projects. Check your connection and try again.'
  } finally {
    loading.value = false
  }
}
async function create() {
  saving.value = true
  formError.value = ''
  try {
    await api.post('pm/projects/', {
      ...form,
      start_date: form.start_date || null,
      due_date: form.due_date || null,
    })
    modal.value = false
    toast.success(`Project ${form.name} created.`)
    Object.assign(form, { name: '', key: '', description: '', start_date: '', due_date: '' })
    await load()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Delivery · Projects"
      title="Projects"
      description="A shared view of what we're building and where it stands."
    >
      <template #actions>
        <button v-if="hasRole('manager')" class="btn-primary" @click="modal = true">
          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          New project
        </button>
      </template>
    </PageHeader>
    <dl
      v-if="summary"
      class="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4"
    >
      <div
        v-for="stat in [
          { label: 'Active projects', value: summary.projects },
          { label: 'Tasks completed', value: `${summary.done} / ${summary.tasks}` },
          { label: 'Assigned to you', value: summary.assigned_to_me },
          { label: 'Overdue tasks', value: summary.overdue },
        ]"
        :key="stat.label"
        class="panel p-4"
      >
        <dt class="ledger-label">{{ stat.label }}</dt>
        <dd class="readout mt-1 font-display text-[28px]">{{ stat.value }}</dd>
      </div>
    </dl>
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <label class="field w-full sm:max-w-xs"
        ><span class="sr-only">Search projects</span
        ><input v-model="search" type="search" class="input" placeholder="Find a project…"
      /></label>
      <label class="flex items-center gap-2 text-sm text-ink/70"
        ><input v-model="showArchived" type="checkbox" class="accent-ink" /> Show archived
        projects</label
      >
    </div>
    <div
      v-if="loading"
      aria-busy="true"
      aria-label="Loading projects"
      class="grid gap-5 md:grid-cols-2"
    >
      <div v-for="i in 4" :key="i" class="h-48 rounded-xl bg-panel/70 motion-safe:animate-pulse" />
    </div>
    <LoadError v-else-if="error" :message="error" @retry="load" />
    <div v-else-if="!filtered.length" class="panel">
      <EmptyState
        :title="search ? 'No matching projects' : showArchived ? 'No archived projects' : 'Your next project starts here'"
        :hint="hasRole('manager') ? 'Create a project, bring in your team, and move the first task.' : 'Projects appear here when your project lead adds you to the team.'"
      >
        <button v-if="search" class="btn-ghost btn-sm" @click="search = ''">Clear search</button>
        <button v-else-if="hasRole('manager') && !showArchived" class="btn-primary btn-sm" @click="modal = true">New project</button>
      </EmptyState>
    </div>
    <div v-else class="grid gap-5 md:grid-cols-2">
      <RouterLink
        v-for="p in filtered"
        :key="p.id"
        :to="`/app/projects/${p.id}`"
        class="group panel block p-6 transition-colors hover:border-river/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
      >
        <div class="flex items-center justify-between gap-3">
          <span class="font-mono text-xs text-flag">{{ p.key }}</span
          ><span class="text-sm text-ink/60">{{
            p.archived ? 'Archived' : dateLabel(p.due_date)
          }}</span>
        </div>
        <h2 class="mt-5 text-2xl font-medium tracking-tight group-hover:text-river">
          {{ p.name }}
          <span
            aria-hidden="true"
            class="inline-block transition-transform group-hover:translate-x-1"
            >↗</span
          >
        </h2>
        <p class="mt-2 line-clamp-2 min-h-10 text-sm text-ink/65">
          {{ p.description || 'A new workspace for the team.' }}
        </p>
        <div
          class="mt-5 h-1.5 overflow-hidden rounded-full bg-panel"
          role="progressbar"
          :aria-valuenow="p.progress.percent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`${p.name} progress`"
        >
          <div class="h-full rounded-full bg-moss" :style="{ width: `${p.progress.percent}%` }" />
        </div>
        <div class="mt-3 flex items-center justify-between">
          <span class="text-xs text-ink/65">{{ p.people.length }} team members</span
          ><span class="readout text-sm"
            >{{ p.progress.done }}/{{ p.progress.total }} done
            <span class="ml-2 text-ink/50">{{ p.progress.percent }}%</span></span
          >
        </div>
      </RouterLink>
    </div>
    <Modal :open="modal" title="Create project" @close="modal = false">
      <form class="grid gap-4" @submit.prevent="create">
        <label class="field"
          ><span class="ledger-label">Project name</span
          ><input v-model="form.name" class="input" required maxlength="200"
        /></label>
        <label class="field"
          ><span class="ledger-label">Project key</span
          ><input
            v-model="form.key"
            class="input uppercase"
            required
            pattern="[A-Za-z0-9_-]+"
            maxlength="12"
            placeholder="e.g. GIS"
          /><span class="text-xs text-ink/60">A unique short code for task references.</span></label
        >
        <label class="field"
          ><span class="ledger-label">Description</span
          ><textarea v-model="form.description" class="input" rows="3" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="field"
            ><span class="ledger-label">Start date</span
            ><input v-model="form.start_date" class="input" type="date" /></label
          ><label class="field"
            ><span class="ledger-label">Due date</span
            ><input v-model="form.due_date" class="input" type="date" :min="form.start_date"
          /></label>
        </div>
        <p v-if="formError" role="alert" class="text-sm text-rust">{{ formError }}</p>
        <button class="btn-ink justify-self-end" :disabled="saving">
          {{ saving ? 'Creating…' : 'Create project' }}
        </button>
      </form>
    </Modal>
  </div>
</template>
