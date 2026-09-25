<script setup lang="ts">
import { reactive, ref } from "vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

// 'login' | 'signup' | 'verify'
const mode = ref<"login" | "signup" | "verify">("login");

const form = reactive({ name: "", email: "", password: "", confirm: "" });
const code = reactive(["", "", "", ""]);
const codeInputs = ref<HTMLInputElement[]>([]);

function handleLogin() {
  alert("Login is not connected to a server yet.");
  closeAndReset();
}

function handleSignup() {
  mode.value = "verify";
}

function handleVerify() {
  alert("Account created — not connected to a server yet.");
  closeAndReset();
}

function onCodeInput(i: number) {
  if (code[i] && i < 3) codeInputs.value[i + 1]?.focus();
}

function closeAndReset() {
  emit("close");
  mode.value = "login";
  code.forEach((_, i) => (code[i] = ""));
}
</script>

<template>
  <div
    v-if="props.open"
    class="fixed inset-0 z-[10000] flex items-center justify-center bg-ink/60 px-4 backdrop-blur-sm"
    @click.self="closeAndReset"
  >
    <div class="w-full max-w-sm rounded-2xl border border-ink/10 bg-paper p-8 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="font-display text-xl font-semibold text-ink">
          {{
            mode === "login" ? "Log in" : mode === "signup" ? "Create account" : "Verify your email"
          }}
        </h2>
        <button aria-label="Close" class="text-ink/50 hover:text-ink" @click="closeAndReset">
          ✕
        </button>
      </div>

      <!-- LOGIN -->
      <template v-if="mode === 'login'">
        <p class="mt-1 text-sm text-ink/60">Access your Thimitech client dashboard.</p>

        <form class="mt-6 grid gap-4" @submit.prevent="handleLogin">
          <label class="grid gap-1.5 text-sm">
            <span class="text-ink/70">Email</span>
            <input
              v-model="form.email"
              type="email"
              required
              class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
            />
          </label>
          <label class="grid gap-1.5 text-sm">
            <span class="text-ink/70">Password</span>
            <input
              v-model="form.password"
              type="password"
              required
              class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
            />
          </label>
          <a href="#" class="-mt-1 text-xs text-river hover:underline">Forgotten password?</a>
          <button
            type="submit"
            class="mt-2 rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river"
          >
            Log in
          </button>
        </form>

        <div class="mt-6 flex items-center gap-3 text-xs text-ink/40">
          <span class="h-px flex-1 bg-ink/10"></span>
          or log in with
          <span class="h-px flex-1 bg-ink/10"></span>
        </div>

        <div class="mt-4 grid gap-2.5">
          <button
            class="flex items-center justify-center gap-2 rounded-lg border border-ink/15 py-2.5 text-sm font-medium text-ink hover:bg-panel"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4">
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.7-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.8z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.2 0 6-1.1 7.9-2.9l-3.9-3c-1.1.7-2.4 1.1-4 1.1-3.1 0-5.7-2.1-6.6-4.9H1.4v3.1C3.3 21.3 7.3 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.4 14.3c-.2-.7-.4-1.5-.4-2.3s.1-1.6.4-2.3V6.6H1.4C.5 8.3 0 10.1 0 12s.5 3.7 1.4 5.4l4-3.1z"
              />
              <path
                fill="#EA4335"
                d="M12 4.8c1.7 0 3.3.6 4.5 1.8l3.4-3.4C17.9 1.2 15.1 0 12 0 7.3 0 3.3 2.7 1.4 6.6l4 3.1C6.3 6.9 8.9 4.8 12 4.8z"
              />
            </svg>
            Google
          </button>
          <button
            class="flex items-center justify-center gap-2 rounded-lg border border-ink/15 py-2.5 text-sm font-medium text-ink hover:bg-panel"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4">
              <path fill="#F35325" d="M1 1h10v10H1z" />
              <path fill="#81BC06" d="M13 1h10v10H13z" />
              <path fill="#05A6F0" d="M1 13h10v10H1z" />
              <path fill="#FFBA08" d="M13 13h10v10H13z" />
            </svg>
            Microsoft
          </button>
          <button
            class="flex items-center justify-center gap-2 rounded-lg border border-ink/15 py-2.5 text-sm font-medium text-ink hover:bg-panel"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="#1DA1F2">
              <path
                d="M23 4.9c-.8.4-1.7.6-2.6.8 1-.6 1.7-1.5 2-2.6-.9.5-1.9.9-3 1.1a4.7 4.7 0 00-8 4.3A13.4 13.4 0 011.7 3.1a4.7 4.7 0 001.5 6.3c-.7 0-1.4-.2-2-.6v.1c0 2.3 1.6 4.2 3.8 4.6-.4.1-.8.2-1.3.2-.3 0-.6 0-.9-.1a4.7 4.7 0 004.4 3.3A9.5 9.5 0 011 19.3 13.4 13.4 0 007.3 21c8.7 0 13.5-7.3 13.5-13.6v-.6c.9-.7 1.7-1.5 2.3-2.5z"
              />
            </svg>
            Twitter / X
          </button>
          <button
            class="flex items-center justify-center gap-2 rounded-lg border border-ink/15 py-2.5 text-sm font-medium text-ink hover:bg-panel"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4" fill="#181717">
              <path
                d="M12 .3a12 12 0 00-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.3-1.8-1.3-1.8-1.1-.7 0-.7 0-.7 1.2 0 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.4 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-6a4.6 4.6 0 011.2-3.2 4.3 4.3 0 01.1-3.2s1-.3 3.3 1.2a11.3 11.3 0 016 0c2.3-1.5 3.3-1.2 3.3-1.2a4.3 4.3 0 01.1 3.2 4.6 4.6 0 011.2 3.2c0 4.7-2.8 5.7-5.5 6 .5.4.9 1.2.9 2.4v3.5c0 .3.2.7.8.6A12 12 0 0012 .3z"
              />
            </svg>
            GitHub
          </button>
        </div>

        <p class="mt-6 text-center text-xs text-ink/50">
          Don't have an account?
          <button class="text-river hover:underline" @click="mode = 'signup'">Sign up</button>
        </p>
      </template>

      <!-- SIGN UP -->
      <template v-else-if="mode === 'signup'">
        <p class="mt-1 text-sm text-ink/60">Get started with your free client account.</p>

        <form class="mt-6 grid gap-4" @submit.prevent="handleSignup">
          <label class="grid gap-1.5 text-sm">
            <span class="text-ink/70">Full name</span>
            <input
              v-model="form.name"
              type="text"
              required
              class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
            />
          </label>
          <label class="grid gap-1.5 text-sm">
            <span class="text-ink/70">Email</span>
            <input
              v-model="form.email"
              type="email"
              required
              class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
            />
          </label>
          <label class="grid gap-1.5 text-sm">
            <span class="text-ink/70">Password</span>
            <input
              v-model="form.password"
              type="password"
              required
              class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
            />
          </label>
          <button
            type="submit"
            class="mt-2 rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river"
          >
            Create account
          </button>
        </form>

        <p class="mt-6 text-center text-xs text-ink/50">
          Already have an account?
          <button class="text-river hover:underline" @click="mode = 'login'">Log in</button>
        </p>
      </template>

      <!-- VERIFY CODE -->
      <template v-else>
        <p class="mt-1 text-sm text-ink/60">We've sent a verification code to your inbox.</p>

        <form class="mt-6" @submit.prevent="handleVerify">
          <div class="flex justify-center gap-3">
            <input
              v-for="(d, i) in code"
              :key="i"
              :ref="(el) => (codeInputs[i] = el as HTMLInputElement)"
              v-model="code[i]"
              maxlength="1"
              inputmode="numeric"
              class="h-14 w-14 rounded-lg border border-ink/15 text-center text-xl font-medium outline-none focus:border-river"
              @input="onCodeInput(i)"
            />
          </div>
          <button
            type="submit"
            class="mt-6 w-full rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river"
          >
            Verify code
          </button>
        </form>

        <p class="mt-5 text-center text-xs text-ink/50">
          <button class="text-river hover:underline" @click="mode = 'signup'">← Back</button>
        </p>
      </template>
    </div>
  </div>
</template>
