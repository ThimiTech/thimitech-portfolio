<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { isAxiosError } from "axios";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";

/**
 * Log in / create account. Shared by the /login + /register pages and the
 * landing-page modal (Login.vue). After success it follows `?next=` (same-origin
 * paths only), else staff go to /app and applicants stay on the public site.
 */
const props = defineProps<{ mode: "login" | "signup"; idPrefix?: string }>();
const emit = defineEmits<{ switch: [mode: "login" | "signup"]; done: [] }>();

const { setSession, fetchMe, hasRole, closeLogin } = useAuth();
const route = useRoute();
const router = useRouter();
const id = (f: string) => `${props.idPrefix ?? "auth"}-${f}`;

const form = reactive({ name: "", email: "", password: "", confirm: "" });
const errors = reactive<Record<string, string>>({});
const touched = reactive<Record<string, boolean>>({});
const formError = ref("");
const loading = ref(false);
const showPw = ref(false);
const capsLock = ref(false);
const root = ref<HTMLFormElement | null>(null);

const isSignup = computed(() => props.mode === "signup");
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(field?: string) {
  const check: Record<string, () => string> = {
    name: () => (isSignup.value && !form.name.trim() ? "Enter your full name." : ""),
    email: () => (!form.email.trim() ? "Enter your email address." : EMAIL.test(form.email.trim()) ? "" : "That doesn't look like an email address."),
    password: () =>
      !form.password ? "Enter your password." : isSignup.value && form.password.length < 8 ? "Use at least 8 characters." : "",
    confirm: () => (isSignup.value && form.confirm !== form.password ? "Passwords don't match." : ""),
  };
  for (const f of field ? [field] : Object.keys(check)) errors[f] = check[f]!();
  return !Object.values(errors).some(Boolean);
}
function blur(f: string) {
  touched[f] = true;
  validate(f);
}
const shown = (f: string) => (touched[f] ? errors[f] : "");

watch(
  () => props.mode,
  () => {
    formError.value = "";
    for (const k of Object.keys(errors)) delete errors[k];
    for (const k of Object.keys(touched)) delete touched[k];
    form.password = form.confirm = "";
  },
);

/** Maps DRF errors onto fields; returns whatever is left as a sentence. */
function applyApiError(e: unknown, fallback: string): string {
  if (!isAxiosError(e)) return fallback;
  if (!e.response) return "Can't reach the server. Check your connection and try again.";
  if (e.response.status >= 500) return "The server hit a problem. Please try again in a moment.";
  const data = e.response.data as Record<string, unknown> | undefined;
  if (!data || typeof data !== "object") return fallback;
  const rest: string[] = [];
  for (const [k, v] of Object.entries(data)) {
    const msg = Array.isArray(v) ? v.join(" ") : String(v);
    if (k in form && k !== "name") {
      errors[k] = msg;
      touched[k] = true;
    } else rest.push(msg);
  }
  return rest.join(" ");
}

function safeNext(): string | null {
  const n = route.query.next;
  return typeof n === "string" && n.startsWith("/") && !n.startsWith("//") ? n : null;
}

async function signIn() {
  const { data } = await api.post<{ access: string; refresh: string }>("token/", { email: form.email.trim(), password: form.password });
  setSession(data.access, data.refresh, form.email.trim());
}

async function submit() {
  formError.value = "";
  for (const f of ["name", "email", "password", "confirm"]) touched[f] = true;
  if (!validate()) {
    await nextTick();
    root.value?.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
    return;
  }
  loading.value = true;
  try {
    if (isSignup.value) {
      const [first, ...rest] = form.name.trim().split(/\s+/);
      try {
        // One call: creates a guest account and returns its token pair.
        const { data } = await api.post<{ access: string; refresh: string }>("register/", {
          email: form.email.trim(),
          password: form.password,
          first_name: first,
          last_name: rest.join(" "),
        });
        setSession(data.access, data.refresh, form.email.trim().toLowerCase());
      } catch (e) {
        formError.value = applyApiError(e, "We couldn't create your account. Check the details and try again.");
        return;
      }
    } else {
      await signIn();
    }
    await fetchMe();
    emit("done");
    const next = safeNext();
    if (next) router.push(next);
    else if (hasRole("employee")) router.push("/app");
    else if (route.name === "login" || route.name === "register") router.push("/");
  } catch (e) {
    const status = isAxiosError(e) ? e.response?.status : undefined;
    formError.value =
      status === 401 ? "That email and password don't match an active account." : applyApiError(e, "Sign-in failed. Please try again.");
  } finally {
    loading.value = false;
  }
  if (formError.value) {
    await nextTick();
    root.value?.querySelector<HTMLElement>("[aria-invalid='true']")?.focus();
  }
}

function onPwKey(e: KeyboardEvent) {
  capsLock.value = !!e.getModifierState?.("CapsLock");
}
</script>

<template>
  <form ref="root" class="grid gap-4" novalidate @submit.prevent="submit">
    <div v-if="formError" class="flex items-start gap-2.5 rounded-lg border border-rust/30 bg-rust/10 px-3.5 py-2.5 text-sm text-rust" role="alert">
      <svg viewBox="0 0 24 24" class="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" /></svg>
      <span>{{ formError }}</span>
    </div>

    <div v-if="isSignup" class="field">
      <label :for="id('name')" class="text-sm font-medium text-ink/80">Full name</label>
      <input
        :id="id('name')"
        v-model="form.name"
        type="text"
        autocomplete="name"
        class="input h-11 text-[15px]"
        :aria-invalid="!!shown('name')"
        :aria-describedby="shown('name') ? id('name-err') : undefined"
        @blur="blur('name')"
      />
      <p v-if="shown('name')" :id="id('name-err')" class="text-xs text-rust">{{ shown("name") }}</p>
    </div>

    <div class="field">
      <label :for="id('email')" class="text-sm font-medium text-ink/80">Work email</label>
      <input
        :id="id('email')"
        v-model="form.email"
        type="email"
        inputmode="email"
        autocomplete="username"
        autocapitalize="off"
        spellcheck="false"
        placeholder="you@thimitech.com"
        class="input h-11 text-[15px]"
        :aria-invalid="!!shown('email')"
        :aria-describedby="shown('email') ? id('email-err') : undefined"
        @blur="blur('email')"
      />
      <p v-if="shown('email')" :id="id('email-err')" class="text-xs text-rust">{{ shown("email") }}</p>
    </div>

    <div class="field">
      <div class="flex items-baseline justify-between">
        <label :for="id('password')" class="text-sm font-medium text-ink/80">Password</label>
        <RouterLink
          v-if="!isSignup"
          :to="{ path: '/forgot-password', query: form.email.trim() ? { email: form.email.trim() } : {} }"
          class="rounded text-xs font-medium text-river underline-offset-2 hover:text-flag hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          @click="closeLogin()"
        >Forgot password?</RouterLink>
      </div>
      <div class="relative">
        <input
          :id="id('password')"
          v-model="form.password"
          :type="showPw ? 'text' : 'password'"
          :autocomplete="isSignup ? 'new-password' : 'current-password'"
          class="input h-11 pr-11 text-[15px]"
          :aria-invalid="!!shown('password')"
          :aria-describedby="[shown('password') ? id('password-err') : isSignup ? id('password-hint') : '', capsLock ? id('caps') : ''].filter(Boolean).join(' ') || undefined"
          @blur="blur('password')"
          @keyup="onPwKey"
          @keydown="onPwKey"
        />
        <button
          type="button"
          class="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-ink/45 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          :aria-label="showPw ? 'Hide password' : 'Show password'"
          :aria-pressed="showPw"
          @click="showPw = !showPw"
        >
          <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <template v-if="showPw"><path d="M9.9 4.2A10 10 0 0 1 12 4c7 0 10 8 10 8a17 17 0 0 1-2.2 3.2M6.6 6.6A17 17 0 0 0 2 12s3 8 10 8a10 10 0 0 0 5.4-1.6M2 2l20 20M14.1 14.1a3 3 0 0 1-4.2-4.2" /></template>
            <template v-else><path d="M2 12s3-8 10-8 10 8 10 8-3 8-10 8-10-8-10-8z" /><circle cx="12" cy="12" r="3" /></template>
          </svg>
        </button>
      </div>
      <p v-if="shown('password')" :id="id('password-err')" class="text-xs text-rust">{{ shown("password") }}</p>
      <p v-else-if="isSignup" :id="id('password-hint')" class="text-xs text-ink/50">At least 8 characters. Avoid anything you use elsewhere.</p>
      <p v-if="capsLock" :id="id('caps')" class="text-xs text-contour-ink">Caps Lock is on.</p>
    </div>

    <div v-if="isSignup" class="field">
      <label :for="id('confirm')" class="text-sm font-medium text-ink/80">Confirm password</label>
      <input
        :id="id('confirm')"
        v-model="form.confirm"
        :type="showPw ? 'text' : 'password'"
        autocomplete="new-password"
        class="input h-11 text-[15px]"
        :aria-invalid="!!shown('confirm')"
        :aria-describedby="shown('confirm') ? id('confirm-err') : undefined"
        @blur="blur('confirm')"
      />
      <p v-if="shown('confirm')" :id="id('confirm-err')" class="text-xs text-rust">{{ shown("confirm") }}</p>
    </div>

    <button type="submit" class="btn-ink mt-1 h-11 w-full text-[15px]" :disabled="loading" :aria-busy="loading">
      <svg v-if="loading" viewBox="0 0 24 24" class="h-4 w-4 motion-safe:animate-spin" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.2-8.6" stroke-linecap="round" /></svg>
      {{ loading ? (isSignup ? "Creating account…" : "Signing in…") : isSignup ? "Create account" : "Sign in" }}
    </button>

    <p class="text-center text-sm text-ink/60">
      {{ isSignup ? "Already have an account?" : "New here? Applicants can" }}
      <button type="button" class="font-medium text-river underline-offset-2 hover:text-flag hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40" @click="emit('switch', isSignup ? 'login' : 'signup')">
        {{ isSignup ? "Sign in" : "create an account" }}
      </button>
    </p>
  </form>
</template>
