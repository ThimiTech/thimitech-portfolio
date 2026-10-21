<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { isAxiosError } from "axios";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";

/**
 * Password reset, both steps. "request": email in, the server always answers 200.
 * "confirm": uid + token come from the emailed link (/reset-password?uid=…&token=…);
 * they are read once and stripped from the address bar.
 */
const props = defineProps<{ mode: "request" | "confirm" }>();

const route = useRoute();
const router = useRouter();
const { isLoggedIn, logout } = useAuth();

const q = (k: string) => (typeof route.query[k] === "string" ? (route.query[k] as string) : "");
const link = { uid: q("uid"), token: q("token") };
if (props.mode === "confirm" && (link.uid || link.token)) router.replace({ query: {} });

const form = reactive({ email: q("email"), password: "", confirm: "" });
const errors = reactive<Record<string, string>>({});
const formError = ref("");
const sent = ref(false);
const loading = ref(false);
const badLink = ref(props.mode === "confirm" && !(link.uid && link.token));

function check(): boolean {
  for (const k of Object.keys(errors)) delete errors[k];
  if (props.mode === "request") {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = "Enter the email address you sign in with.";
  } else {
    if (form.password.length < 8) errors.password = "Use at least 8 characters.";
    else if (form.confirm !== form.password) errors.confirm = "Passwords don't match.";
  }
  return !Object.keys(errors).length;
}

function message(e: unknown): string {
  if (!isAxiosError(e) || !e.response) return "Can't reach the server. Check your connection and try again.";
  if (e.response.status === 429) return "Too many attempts. Wait a while and try again.";
  if (e.response.status >= 500) return "The server hit a problem. Please try again in a moment.";
  const data = (e.response.data ?? {}) as Record<string, string | string[]>;
  const text = (v: string | string[] | undefined) => (Array.isArray(v) ? v.join(" ") : (v ?? ""));
  if (data.token) {
    badLink.value = true;
    return "";
  }
  if (data.new_password) errors.password = text(data.new_password);
  if (data.email) errors.email = text(data.email);
  return errors.password || errors.email ? "" : "Something went wrong. Please try again.";
}

async function submit() {
  formError.value = "";
  if (!check()) return;
  loading.value = true;
  try {
    if (props.mode === "request") {
      await api.post("password-reset/", { email: form.email.trim() });
      sent.value = true;
    } else {
      await api.post("password-reset/confirm/", { ...link, new_password: form.password });
      if (isLoggedIn.value) logout(); // the reset revoked every session anyway
      router.push({ name: "login", query: { reset: "1" } });
    }
  } catch (e) {
    formError.value = message(e);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div v-if="sent" class="grid gap-4" role="status">
    <p class="rounded-lg border border-moss/30 bg-moss/10 px-3.5 py-3 text-sm text-ink">
      If <strong>{{ form.email.trim() }}</strong> has an account, a reset link is on its way. It works once and expires in a few days.
    </p>
    <p class="text-sm text-ink/60">Nothing after a few minutes? Check spam, or ask HR to reset it for you.</p>
    <RouterLink :to="{ name: 'login' }" class="btn-ink h-11 w-full text-[15px]">Back to sign in</RouterLink>
  </div>

  <div v-else-if="badLink" class="grid gap-4" role="alert">
    <p class="rounded-lg border border-rust/30 bg-rust/10 px-3.5 py-3 text-sm text-rust">
      This reset link is invalid, already used, or expired.
    </p>
    <RouterLink :to="{ name: 'forgot-password' }" class="btn-ink h-11 w-full text-[15px]">Send a new link</RouterLink>
  </div>

  <form v-else class="grid gap-4" novalidate @submit.prevent="submit">
    <p v-if="formError" class="rounded-lg border border-rust/30 bg-rust/10 px-3.5 py-2.5 text-sm text-rust" role="alert">{{ formError }}</p>

    <div v-if="mode === 'request'" class="field">
      <label for="reset-email" class="text-sm font-medium text-ink/80">Work email</label>
      <input
        id="reset-email"
        v-model="form.email"
        type="email"
        inputmode="email"
        autocomplete="username"
        autocapitalize="off"
        spellcheck="false"
        class="input h-11 text-[15px]"
        :aria-invalid="!!errors.email"
        :aria-describedby="errors.email ? 'reset-email-err' : undefined"
      />
      <p v-if="errors.email" id="reset-email-err" class="text-xs text-rust">{{ errors.email }}</p>
    </div>

    <template v-else>
      <div class="field">
        <label for="reset-pw" class="text-sm font-medium text-ink/80">New password</label>
        <input
          id="reset-pw"
          v-model="form.password"
          type="password"
          autocomplete="new-password"
          class="input h-11 text-[15px]"
          :aria-invalid="!!errors.password"
          :aria-describedby="errors.password ? 'reset-pw-err' : 'reset-pw-hint'"
        />
        <p v-if="errors.password" id="reset-pw-err" class="text-xs text-rust">{{ errors.password }}</p>
        <p v-else id="reset-pw-hint" class="text-xs text-ink/50">At least 8 characters, not too common or all numbers.</p>
      </div>
      <div class="field">
        <label for="reset-confirm" class="text-sm font-medium text-ink/80">Confirm new password</label>
        <input
          id="reset-confirm"
          v-model="form.confirm"
          type="password"
          autocomplete="new-password"
          class="input h-11 text-[15px]"
          :aria-invalid="!!errors.confirm"
          :aria-describedby="errors.confirm ? 'reset-confirm-err' : undefined"
        />
        <p v-if="errors.confirm" id="reset-confirm-err" class="text-xs text-rust">{{ errors.confirm }}</p>
      </div>
    </template>

    <button type="submit" class="btn-ink mt-1 h-11 w-full text-[15px]" :disabled="loading" :aria-busy="loading">
      {{ loading ? "Please wait…" : mode === "request" ? "Email me a reset link" : "Set new password" }}
    </button>
    <p class="text-center text-sm text-ink/60">
      Remembered it?
      <RouterLink :to="{ name: 'login' }" class="font-medium text-river underline-offset-2 hover:text-flag hover:underline">Sign in</RouterLink>
    </p>
  </form>
</template>
