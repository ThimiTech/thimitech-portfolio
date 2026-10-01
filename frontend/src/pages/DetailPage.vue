<script setup>
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import api from "../api/api";

const route = useRoute();

const project = ref(null);

const getProject = async () => {
  try {
    const id = route.params.id;

    const res = await api.get(`projects/${id}/`);

    console.log("Project detail:", res.data);

    project.value = res.data;
  } catch {}
};

onMounted(() => {
  getProject();
});
</script>

<template>
  <section v-if="project" class="min-h-screen bg-panel py-24">
    <div class="mx-auto max-w-6xl px-6">
      <!-- Project -->
      <div>
        <!-- Back Button -->
        <div class="mb-10">
          <router-link
            to="/"
            class="inline-flex items-center gap-2 text-sm font-semibold text-river hover:text-ink"
          >
            ← Back to Projects
          </router-link>
        </div>

        <!-- Project Image -->
        <div v-if="project.image" class="overflow-hidden rounded-3xl border border-ink/10 bg-paper">
          <img
            :src="`http://127.0.0.1:8000${project.image}`"
            :alt="project.name"
            class="h-[300px] w-full object-cover sm:h-[450px] lg:h-[550px]"
          />
        </div>

        <!-- Fallback if no image -->
        <div
          v-else
          class="flex h-[300px] items-center justify-center rounded-3xl bg-gradient-to-br from-river to-ink sm:h-[450px]"
        >
          <h1 class="px-6 text-center font-display text-4xl font-bold text-white">
            {{ project.name }}
          </h1>
        </div>

        <!-- Project Header -->
        <div class="mt-12 max-w-4xl">
          <!-- Project Name -->
          <h1
            class="font-display text-4xl font-bold leading-tight text-ink sm:text-5xl lg:text-6xl"
          >
            {{ project.name }}
          </h1>

          <!-- Subtitle -->
          <p v-if="project.subtitle" class="mt-5 text-xl leading-relaxed text-river sm:text-2xl">
            {{ project.subtitle }}
          </p>
        </div>

        <!-- Description -->
        <div class="mt-14 grid grid-cols-1 gap-12 lg:grid-cols-[1fr_280px]">
          <!-- Main Description -->
          <div>
            <p class="mb-5 font-mono text-xs uppercase tracking-widest text-river">
              [ Project Overview ]
            </p>

            <div class="max-w-3xl text-base leading-8 text-ink/70 sm:text-lg">
              {{ project.description }}
            </div>
          </div>

          <!-- Project Information -->
          <aside class="h-fit rounded-2xl border border-ink/10 bg-paper p-6">
            <p class="font-mono text-xs uppercase tracking-widest text-river">[ Project Info ]</p>

            <div class="mt-6 space-y-5">
              <div>
                <p class="text-xs uppercase tracking-wide text-ink/40">Project</p>

                <p class="mt-1 font-semibold text-ink">
                  {{ project.name }}
                </p>
              </div>

              <div v-if="project.subtitle">
                <p class="text-xs uppercase tracking-wide text-ink/40">Category</p>

                <p class="mt-1 text-sm text-ink/70">
                  {{ project.subtitle }}
                </p>
              </div>
            </div>

            <!-- Project URL -->
            <a
              v-if="project.url"
              :href="project.url"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-8 flex w-full items-center justify-center gap-2 rounded-xl bg-river px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Visit Project
              <span>↗</span>
            </a>
          </aside>
        </div>
      </div>
    </div>
  </section>
  <div v-else>no data</div>
</template>
