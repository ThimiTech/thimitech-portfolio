<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import api from '@/api/api'
import { toast } from '../ui/toast'
import MarkdownView from './MarkdownView.vue'
import { errorMessage, type Doc, type ProjectLink, type Project } from './pm'
const props = defineProps<{ project: Project; docs: Doc[]; links: ProjectLink[] }>()
const emit = defineEmits<{ saved: [] }>()

const SECTIONS: { id: string; label: string; hint: string }[] = [
  { id: 'story', label: 'Story', hint: 'The write-up below' },
  { id: 'progress', label: 'Progress', hint: 'Percent of tasks done' },
  { id: 'milestones', label: 'Milestones', hint: 'Titles, dates and status' },
  { id: 'team', label: 'Team', hint: 'Names and designations' },
  { id: 'links', label: 'Links', hint: 'Only links marked Public' },
  { id: 'gallery', label: 'Gallery', hint: 'Public image documents' },
  { id: 'documents', label: 'Downloads', hint: 'Public non-image documents' },
]
const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80)
const form = reactive({
  visibility: props.project.visibility,
  slug: props.project.slug || slugify(props.project.name),
  tagline: props.project.tagline,
  story: props.project.story,
  tech: props.project.tech.join(', '),
  public_sections: [...(props.project.public_sections.length ? props.project.public_sections : ['story', 'progress', 'milestones', 'links', 'gallery'])],
})
const cover = ref<File | null>(null)
const preview = ref(props.project.cover || '')
const removeCover = ref(false)
const busy = ref(false)
const tab = ref<'write' | 'preview'>('write')
const publicDocs = computed(() => props.docs.filter((d) => d.public).length)
const publicLinks = computed(() => props.links.filter((l) => l.public).length)
const url = computed(() => `${location.origin}/work/${form.slug}`)

function pickCover(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (f.size > 5 * 1024 * 1024) return toast.error('Cover image must be 5 MB or smaller.')
  if (preview.value.startsWith('blob:')) URL.revokeObjectURL(preview.value)
  cover.value = f
  removeCover.value = false
  preview.value = URL.createObjectURL(f)
}
onBeforeUnmount(() => preview.value.startsWith('blob:') && URL.revokeObjectURL(preview.value))
async function save() {
  busy.value = true
  try {
    await api.patch(`pm/projects/${props.project.id}/`, {
      ...form,
      slug: form.slug || null,
      tech: form.tech
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    })
    if (cover.value || removeCover.value) {
      const data = new FormData()
      if (cover.value) data.append('cover', cover.value)
      else data.append('remove_cover', 'true')
      await api.patch(`pm/projects/${props.project.id}/`, data)
      cover.value = null
      removeCover.value = false
    }
    toast.success(form.visibility === 'public' ? 'Public page updated.' : 'Profile saved (private).')
    emit('saved')
  } catch (e) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <form class="grid items-start gap-6 xl:grid-cols-[1fr_340px]" @submit.prevent="save">
    <div class="grid gap-6">
      <section class="panel overflow-hidden">
        <div class="relative aspect-[21/8] bg-panel">
          <img v-if="preview && !removeCover" :src="preview" alt="Cover preview" class="h-full w-full object-cover" />
          <div v-else class="contour-bg grid h-full place-items-center bg-ink text-sm text-paper/60">No cover image</div>
          <div class="absolute bottom-3 right-3 flex gap-2">
            <label class="btn-ghost btn-sm cursor-pointer !bg-sheet">
              {{ preview && !removeCover ? 'Replace cover' : 'Upload cover' }}
              <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" class="sr-only" @change="pickCover" />
            </label>
            <button v-if="preview && !removeCover" type="button" class="btn-ghost btn-sm !bg-sheet" @click="(removeCover = true), (cover = null)">Remove</button>
          </div>
        </div>
        <div class="grid gap-4 p-5">
          <label class="field"><span class="ledger-label">Tagline</span><input v-model="form.tagline" maxlength="200" class="input text-base" placeholder="One line that says why this project matters" /></label>
          <label class="field"><span class="ledger-label">Tech & tools (comma separated)</span><input v-model="form.tech" class="input" placeholder="Vue, Django, PostGIS, Leaflet" /></label>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h3 class="font-medium">Story</h3>
          <div class="flex rounded-full border border-ink/15 p-0.5" role="group" aria-label="Story editor">
            <button v-for="t in ['write', 'preview'] as const" :key="t" type="button" class="rounded-full px-3 py-0.5 text-xs capitalize" :class="tab === t ? 'bg-ink text-paper' : 'text-ink/60'" :aria-pressed="tab === t" @click="tab = t">{{ t }}</button>
          </div>
        </div>
        <div class="p-5">
          <textarea
            v-if="tab === 'write'"
            v-model="form.story"
            rows="16"
            class="input font-mono text-[13px] leading-6"
            aria-label="Story (Markdown)"
            placeholder="## The challenge&#10;&#10;## What we built&#10;&#10;## Outcome"
          />
          <MarkdownView v-else :source="form.story" empty="Write the story of this project — the problem, the approach, the outcome." />
        </div>
      </section>
    </div>

    <aside class="grid gap-6 xl:sticky xl:top-4">
      <section class="panel p-5">
        <h3 class="font-medium">Visibility</h3>
        <div class="mt-4 grid grid-cols-2 gap-2" role="radiogroup" aria-label="Visibility">
          <label
            v-for="v in ['private', 'public'] as const"
            :key="v"
            class="cursor-pointer rounded-lg border p-3 text-sm capitalize"
            :class="form.visibility === v ? 'border-ink bg-panel/60 font-medium' : 'border-ink/15'"
            ><input v-model="form.visibility" type="radio" :value="v" class="sr-only" />{{ v }}
            <span class="mt-1 block text-[11px] font-normal normal-case text-ink/55">{{ v === 'private' ? 'Team only' : 'Listed on /work' }}</span></label
          >
        </div>
        <label class="field mt-4"
          ><span class="ledger-label">Public URL</span>
          <div class="flex items-center rounded-lg border border-ink/15 bg-sheet pl-3 text-sm focus-within:border-river">
            <span class="shrink-0 text-ink/45">/work/</span>
            <input v-model="form.slug" pattern="[a-z0-9-]+" maxlength="80" class="w-full bg-transparent px-1 py-2 outline-none" @blur="form.slug = slugify(form.slug)" />
          </div>
        </label>
        <a v-if="project.visibility === 'public' && project.slug" :href="`/work/${project.slug}`" target="_blank" rel="noopener" class="mt-2 block truncate text-xs text-river underline">{{ url }} ↗</a>
        <p v-if="project.published_at" class="mt-2 text-[11px] text-ink/50">First published {{ new Date(project.published_at).toLocaleDateString('en-GB') }}</p>
      </section>
      <section class="panel p-5">
        <h3 class="font-medium">What the public sees</h3>
        <p class="mt-1 text-xs text-ink/55">Nothing else — tasks, notes, meetings and internal files always stay private.</p>
        <div class="mt-4 grid gap-2.5">
          <label v-for="s in SECTIONS" :key="s.id" class="flex items-start gap-2.5 text-sm">
            <input v-model="form.public_sections" type="checkbox" :value="s.id" class="mt-1 accent-ink" />
            <span>{{ s.label }}<span class="block text-[11px] text-ink/50">{{ s.hint }}<template v-if="s.id === 'links'"> · {{ publicLinks }} public</template><template v-if="s.id === 'gallery' || s.id === 'documents'"> · {{ publicDocs }} public files</template></span></span>
          </label>
        </div>
      </section>
      <button class="btn-primary" :disabled="busy">{{ busy ? 'Saving…' : form.visibility === 'public' ? 'Save & publish' : 'Save profile' }}</button>
    </aside>
  </form>
</template>
