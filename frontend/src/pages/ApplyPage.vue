<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, RouterLink } from "vue-router";
import api from "../api/api";
import { useAuth } from "../stores/auth";
import NavBar from "../components/NavBar.vue";
import Footer from "../components/Footer.vue";

const route = useRoute();
const { isLoggedIn, openLogin } = useAuth();

const jobId = Number(route.params.jobId);

const form = reactive({
  name: "",
  phone: "",
  address: "",
  cover_letter: "",
});

const cvFile = ref<File | null>(null);
const submitting = ref(false);
const error = ref("");
const success = ref(false);

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  cvFile.value = target.files?.[0] ?? null;
}

// Turns the backend's error response into a readable message
function readError(data: unknown): string {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.error === "string") return d.error;
    if (typeof d.detail === "string") return d.detail;
    return Object.entries(d)
      .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(" ") : msgs}`)
      .join(" | ");
  }
  return "";
}

async function submitApplication() {
  error.value = "";

  if (!isLoggedIn.value) {
    error.value = "Please log in to apply for this position.";
    openLogin();
    return;
  }

  if (!cvFile.value) {
    error.value = "Please attach your CV.";
    return;
  }

  submitting.value = true;

  const data = new FormData();
  data.append("job", String(jobId));
  data.append("name", form.name);
  data.append("phone", form.phone);
  data.append("address", form.address);
  data.append("cover_letter", form.cover_letter);
  data.append("cv", cvFile.value);

  try {
    // No manual Content-Type: axios/browser sets multipart + boundary itself
    await api.post("jobs/apply/", data);
    success.value = true;
  } catch (err: any) {
    console.error("Apply failed:", err.response?.status, err.response?.data);

    if (err.response?.status === 401) {
      error.value = "Your session has expired. Please log in again.";
      openLogin();
    } else {
      error.value =
        readError(err.response?.data) ||
        "Could not reach the server. Please try again.";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="bg-paper font-body text-ink">
    <NavBar />

    <main class="py-20">
      <div class="mx-auto max-w-2xl px-6">
        <RouterLink to="/#hiring" class="text-sm font-medium text-river hover:underline">
          ← Back to open positions
        </RouterLink>

        <div
          v-if="success"
          class="mt-10 rounded-2xl border border-river/30 bg-river/5 p-8 text-center"
        >
          <h1 class="font-display text-2xl font-semibold text-ink">Application sent</h1>
          <p class="mt-3 text-ink/65">
            Thank you for applying. Our team will review your application and get back to you soon.
          </p>
          <RouterLink
            to="/"
            class="mt-6 inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-paper hover:bg-river"
          >
            Back to home
          </RouterLink>
        </div>

        <template v-else>
          <h1 class="mt-6 font-display text-3xl font-semibold text-ink">Apply for this position</h1>
          <p class="mt-3 text-ink/65">
            Fill in your details below. We'll get back to you within two working days.
          </p>

          <div
            v-if="!isLoggedIn"
            class="mt-6 flex items-center justify-between gap-4 rounded-lg border border-flag/30 bg-flag/5 px-4 py-3 text-sm"
          >
            <span class="text-ink/70">You need to be logged in to submit an application.</span>
            <button
              type="button"
              class="font-medium text-river hover:underline"
              @click="openLogin"
            >
              Log in
            </button>
          </div>

          <form class="mt-10 grid gap-6" @submit.prevent="submitApplication">
            <label class="grid gap-1.5 text-sm">
              <span class="font-medium text-ink/70">Full name</span>
              <input
                v-model="form.name"
                type="text"
                required
                class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
              />
            </label>

            <label class="grid gap-1.5 text-sm">
              <span class="font-medium text-ink/70">Phone number</span>
              <input
                v-model="form.phone"
                type="tel"
                required
                maxlength="20"
                class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
              />
            </label>

            <label class="grid gap-1.5 text-sm">
              <span class="font-medium text-ink/70">Address</span>
              <input
                v-model="form.address"
                type="text"
                required
                class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
              />
            </label>

            <label class="grid gap-1.5 text-sm">
              <span class="font-medium text-ink/70">Cover letter</span>
              <textarea
                v-model="form.cover_letter"
                rows="6"
                required
                class="rounded-lg border border-ink/15 px-4 py-2.5 outline-none focus:border-river"
              ></textarea>
            </label>

            <label class="grid gap-1.5 text-sm">
              <span class="font-medium text-ink/70">CV / Resume</span>
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                required
                class="rounded-lg border border-ink/15 px-4 py-2.5 text-sm file:mr-4 file:rounded-full file:border-0 file:bg-ink file:px-4 file:py-1.5 file:text-xs file:font-medium file:text-paper"
                @change="onFileChange"
              />
            </label>

            <p v-if="error" class="text-sm text-flag">{{ error }}</p>

            <button
              type="submit"
              :disabled="submitting"
              class="mt-2 w-fit rounded-full bg-ink px-7 py-3 text-sm font-medium text-paper transition-colors hover:bg-river disabled:opacity-50"
            >
              {{ submitting ? "Submitting…" : "Submit application" }}
            </button>
          </form>
        </template>
      </div>
    </main>

    <Footer />
  </div>
</template>