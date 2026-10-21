<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import AuthForm from "../components/auth/AuthForm.vue";
import ResetForm from "../components/auth/ResetForm.vue";
import { useTheme } from "../components/app/ui/theme";

const route = useRoute();
const router = useRouter();
const mode = computed<"login" | "signup">(() => (route.name === "register" ? "signup" : "login"));
const reset = computed<"request" | "confirm" | null>(() =>
  route.name === "forgot-password" ? "request" : route.name === "reset-password" ? "confirm" : null,
);
const justReset = computed(() => route.query.reset === "1");
const COPY = {
  request: ["Reset your password", "Enter your work email and we'll send you a link to choose a new password."],
  confirm: ["Choose a new password", "Signing in again is required on every device afterwards."],
} as const;
const fromApp = computed(() => typeof route.query.next === "string" && route.query.next.startsWith("/app"));

// Same theme as the workspace this page leads into.
const { isDark } = useTheme();
watch(isDark, (d) => document.documentElement.classList.toggle("app-dark", d), { immediate: true });
onBeforeUnmount(() => document.documentElement.classList.remove("app-dark"));

function switchMode(m: "login" | "signup") {
  router.replace({ name: m === "signup" ? "register" : "login", query: route.query });
}
</script>

<template>
  <div class="grid min-h-dvh bg-paper font-body text-ink lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
    <!-- Brand panel -->
    <aside class="keep-ink contour-bg relative hidden flex-col justify-between overflow-hidden bg-ink p-10 text-paper lg:flex xl:p-14">
      <RouterLink to="/" class="flex items-center gap-2.5 self-start rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/60">
        <svg viewBox="0 0 24 24" class="h-7 w-7 text-flag" aria-hidden="true">
          <path fill="currentColor" d="M12 2C8 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3-7-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5Z" />
        </svg>
        <span class="font-display text-xl font-semibold tracking-tight">Thimitech</span>
        <span class="rounded border border-paper/20 px-1.5 py-px font-mono text-[10px] tracking-[0.18em] text-paper/60">OS</span>
      </RouterLink>

      <div class="max-w-md">
        <p class="font-mono text-[11px] tracking-[0.16em] text-contour uppercase">The workspace</p>
        <h2 class="mt-4 font-display text-4xl leading-[1.1] font-medium tracking-tight xl:text-[44px]">
          Attendance, leave, projects and the people behind them — in one place.
        </h2>
        <ul class="mt-8 grid gap-3 text-[15px] text-paper/70">
          <li v-for="line in ['Check in and see your day at a glance', 'Request leave and track approvals', 'Follow notices, holidays and your tasks']" :key="line" class="flex items-center gap-3">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-flag" aria-hidden="true" />{{ line }}
          </li>
        </ul>
      </div>

      <p class="font-mono text-[10.5px] tracking-[0.14em] text-paper/35">27.6745°N · 85.3878°E · Bhaktapur, Nepal</p>
    </aside>

    <!-- Form -->
    <main class="flex flex-col px-5 py-8 sm:px-10">
      <div class="flex items-center justify-between">
        <RouterLink to="/" class="flex items-center gap-2 rounded-md lg:hidden" aria-label="Thimitech home">
          <svg viewBox="0 0 24 24" class="h-6 w-6 text-flag" aria-hidden="true">
            <path fill="currentColor" d="M12 2C8 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3-7-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5Z" />
          </svg>
          <span class="font-display text-lg font-semibold">Thimitech</span>
        </RouterLink>
        <RouterLink to="/" class="ml-auto text-sm text-ink/55 hover:text-ink">← Back to website</RouterLink>
      </div>

      <div class="mx-auto my-auto w-full max-w-[400px] py-10">
        <h1 class="font-display text-[30px] leading-tight font-medium tracking-tight">
          {{ reset ? COPY[reset][0] : mode === "signup" ? "Create your account" : "Sign in to Thimitech" }}
        </h1>
        <p class="mt-2 text-[15px] text-ink/60">
          {{
            reset
              ? COPY[reset][1]
              : mode === "signup"
              ? "Applying for a role? Create an account to submit and track your application."
              : fromApp
                ? "Your session has ended or you need to sign in to open that page."
                : "Use the email your team lead or HR registered for you."
          }}
        </p>
        <p v-if="justReset && !reset && mode === 'login'" class="mt-6 rounded-lg border border-moss/30 bg-moss/10 px-3.5 py-2.5 text-sm text-ink" role="status">
          Password updated. Sign in with your new password.
        </p>
        <div class="mt-8">
          <ResetForm v-if="reset" :key="reset" :mode="reset" />
          <AuthForm v-else :mode="mode" id-prefix="page" @switch="switchMode" />
        </div>
      </div>

      <p class="text-center text-xs text-ink/40">© Thimi Tech · Staff accounts are created by HR.</p>
    </main>
  </div>
</template>
