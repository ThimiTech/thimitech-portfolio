<script setup lang="ts">
import { reactive } from 'vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const form = reactive({ email: '', password: '' })

function handleSubmit() {
  // TODO: replace this with a real fetch() call to your Django login endpoint later
  alert('Login is not connected to a server yet.')
  emit('close')
}
</script>

<template>
  <div
    v-if="props.open"
    class="fixed inset-0 z-[10000] flex items-center justify-center bg-ink/60 px-4 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-sm rounded-2xl border border-ink/10 bg-paper p-8 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="font-display text-xl font-semibold text-ink">Log in</h2>
        <button aria-label="Close" class="text-ink/50 hover:text-ink" @click="emit('close')">✕</button>
      </div>
      <p class="mt-1 text-sm text-ink/60">Access your Thimitech client dashboard.</p>

      <form class="mt-6 grid gap-4" @submit.prevent="handleSubmit">
        <label class="grid gap-1.5 text-sm">
          <span class="text-ink/70">Email</span>
          <input v-model="form.email" type="email" required class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river" />
        </label>
        <label class="grid gap-1.5 text-sm">
          <span class="text-ink/70">Password</span>
          <input v-model="form.password" type="password" required class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river" />
        </label>
        <button type="submit" class="mt-2 rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river">
          Log in
        </button>
      </form>

      <p class="mt-5 text-center text-xs text-ink/50">
        Don't have an account?
        <a href="#contact" class="text-river hover:underline" @click="emit('close')">Contact us</a>
      </p>
    </div>
  </div>
</template>