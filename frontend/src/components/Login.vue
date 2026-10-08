<script setup lang="ts">
import { reactive, ref } from "vue";
import api from "../api/api";
import { useAuth } from "../stores/auth";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{
  close: [];
  loginSuccess: [];
}>();

const { setSession } = useAuth();

// 'login' | 'signup' | 'verify'
const mode = ref<"login" | "signup" | "verify">("login");

const form = reactive({ name: "", email: "", password: "", confirm: "" });
const code = reactive(["", "", "", ""]);
const codeInputs = ref<HTMLInputElement[]>([]);

const error = ref("");
const info = ref("");
const loading = ref(false);

async function handleLogin() {
  error.value = "";
  info.value = "";
  loading.value = true;
  try {
    const { data } = await api.post("token/", {
      email: form.email,
      password: form.password,
    });

    // saves access_token + refresh_token in localStorage and updates the navbar
    setSession(data.access, data.refresh, form.email);

    emit("loginSuccess");
    closeAndReset();
  } catch (e) {
    console.error("Login failed:", e);
    error.value = "Invalid email or password.";
  } finally {
    loading.value = false;
  }
}

async function handleSignup() {
  error.value = "";
  info.value = "";
  loading.value = true;
  try {
    await api.post("register/", {
      email: form.email,
      password: form.password,
    });

    mode.value = "login";
    form.password = "";
    info.value = "Account created. Please log in.";
  } catch (e: any) {
    console.error("Registration failed:", e);
    const data = e?.response?.data;
    error.value =
      data && typeof data === "object"
        ? Object.values(data).flat().join(" ")
        : "Registration failed. Please check your details.";
  } finally {
    loading.value = false;
  }
}

function handleVerify() {
  info.value = "Verification is not connected to a server yet.";
}

function onCodeInput(i: number) {
  if (code[i] && i < 3) codeInputs.value[i + 1]?.focus();
}

function switchMode(next: "login" | "signup" | "verify") {
  error.value = "";
  info.value = "";
  mode.value = next;
}

function closeAndReset() {
  emit("close");
  mode.value = "login";
  error.value = "";
  info.value = "";
  form.name = "";
  form.email = "";
  form.password = "";
  form.confirm = "";
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

          <a href="#" class="-mt-1 text-xs text-river hover:underline"> Forgotten password? </a>

          <p v-if="info" class="text-sm text-green-700">{{ info }}</p>
          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <button
            type="submit"
            :disabled="loading"
            class="mt-2 rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river disabled:opacity-60"
          >
            {{ loading ? "Logging in..." : "Log in" }}
          </button>
        </form>

        <div class="mt-6 flex items-center gap-3 text-xs text-ink/40">
          <span class="h-px flex-1 bg-ink/10"></span>
          or continue with
          <span class="h-px flex-1 bg-ink/10"></span>
        </div>

        <button
          type="button"
          class="mt-4 flex w-full items-center justify-center gap-3 rounded-lg border border-ink/15 py-3 text-sm font-medium text-ink transition-colors hover:border-ink/30 hover:bg-panel"
        >
          <svg viewBox="0 0 24 24" class="h-5 w-5">
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
          Continue with Google
        </button>

        <p class="mt-6 text-center text-xs text-ink/50">
          Don't have an account?
          <button type="button" class="text-river hover:underline" @click="switchMode('signup')">
            Sign up
          </button>
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

          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

          <button
            type="submit"
            :disabled="loading"
            class="mt-2 rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river disabled:opacity-60"
          >
            {{ loading ? "Creating account..." : "Create account" }}
          </button>
        </form>

        <p class="mt-6 text-center text-xs text-ink/50">
          Already have an account?
          <button type="button" class="text-river hover:underline" @click="switchMode('login')">
            Log in
          </button>
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

          <p v-if="info" class="mt-4 text-center text-sm text-ink/60">{{ info }}</p>

          <button
            type="submit"
            class="mt-6 w-full rounded-full bg-ink px-6 py-2.5 font-medium text-paper transition-colors hover:bg-river"
          >
            Verify code
          </button>
        </form>

        <p class="mt-5 text-center text-xs text-ink/50">
          <button type="button" class="text-river hover:underline" @click="switchMode('signup')">
            ← Back
          </button>
        </p>
      </template>
    </div>
  </div>
</template>
