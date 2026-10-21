<script setup lang="ts">
import { reactive, ref } from 'vue'
import api from '@/api/api'
import { confirmDialog } from '../ui/confirm'
import { errorMessage } from '../pm/pm'
import { type Category } from './inventory'
defineProps<{ categories: Category[] }>()
const emit = defineEmits<{ changed: [] }>()
const editing = ref<number | null>(null)
const form = reactive({ name: '', description: '' })
const busy = ref(false)
const error = ref('')
function edit(c: Category) {
  editing.value = c.id
  form.name = c.name
  form.description = c.description
  error.value = ''
}
function reset() {
  editing.value = null
  form.name = ''
  form.description = ''
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    if (editing.value) await api.patch(`inventory/categories/${editing.value}/`, form)
    else await api.post('inventory/categories/', form)
    reset()
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
async function remove(c: Category) {
  if (
    !(await confirmDialog({
      title: 'Delete category?',
      body: `Delete ${c.name}? Categories in use cannot be deleted.`,
      confirmLabel: 'Delete',
      danger: true,
    }))
  )
    return
  busy.value = true
  error.value = ''
  try {
    await api.delete(`inventory/categories/${c.id}/`)
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <div class="grid items-start gap-6 md:grid-cols-2">
    <section class="panel p-5">
      <h2 class="mb-5 text-lg font-medium">Asset categories</h2>
      <p v-if="!categories.length" class="text-sm text-ink/65">
        Add a category before registering your first asset.
      </p>
      <article v-for="c in categories" :key="c.id" class="mb-5 border-b border-ink/10 pb-4">
        <h3 class="font-medium">{{ c.name }}</h3>
        <p v-if="c.description" class="mt-2 text-sm text-ink/65">{{ c.description }}</p>
        <div class="mt-3 flex gap-3">
          <button
            class="btn-ghost btn-sm"
            :disabled="busy"
            :aria-label="'Edit category ' + c.name"
            @click="edit(c)"
          >
            Edit</button
          ><button
            class="btn-danger btn-sm"
            :disabled="busy"
            :aria-label="'Delete category ' + c.name"
            @click="remove(c)"
          >
            Delete
          </button>
        </div>
      </article>
    </section>
    <form class="panel grid gap-4 p-5" @submit.prevent="save">
      <h2 class="text-lg font-medium">{{ editing ? 'Edit category' : 'New category' }}</h2>
      <label class="field"
        ><span class="ledger-label">Category name</span
        ><input v-model="form.name" class="input" required maxlength="100" /></label
      ><label class="field"
        ><span class="ledger-label">Description</span
        ><textarea v-model="form.description" class="input" rows="3" />
      </label>
      <p v-if="error" role="alert" class="text-sm text-rust">{{ error }}</p>
      <div class="flex gap-3">
        <button class="btn-ink" :disabled="busy">{{ busy ? 'Saving…' : 'Save category' }}</button
        ><button v-if="editing" class="btn-ghost" type="button" @click="reset">Cancel edit</button>
      </div>
    </form>
  </div>
</template>
