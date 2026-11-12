<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import api from "@/api/api";
import { toast } from "@/components/app/ui/toast";
import { errMsg } from "@/components/app/attendance/attendance";

interface Task { id: number; title: string; description: string; done: boolean; done_at: string | null; done_by_name: string }

/** A person's onboarding checklist. Renders nothing when there is none (unless HR can start one). */
const props = defineProps<{ userId: number; canTick: boolean; canStart: boolean }>();

const tasks = ref<Task[]>([]);
const loaded = ref(false);
const busy = ref(false);
const done = computed(() => tasks.value.filter((t) => t.done).length);

async function load() {
  try {
    tasks.value = (await api.get<Task[]>("org/onboarding/tasks/", { params: { user: props.userId } })).data;
  } catch {
    tasks.value = []; // not visible to this viewer
  } finally {
    loaded.value = true;
  }
}
async function toggle(t: Task) {
  try {
    Object.assign(t, (await api.post<Task>(`org/onboarding/tasks/${t.id}/toggle/`)).data);
  } catch (e) {
    toast.error(errMsg(e, "Couldn't update that step."));
  }
}
async function start() {
  busy.value = true;
  try {
    tasks.value = (await api.post<Task[]>("org/onboarding/tasks/start/", { user: props.userId })).data;
    toast.success("Onboarding checklist started.");
  } catch (e) {
    toast.error(errMsg(e, "Couldn't start the checklist."));
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>

<template>
  <section v-if="loaded && (tasks.length || canStart)" class="panel" aria-labelledby="onb-title">
    <div class="panel-head">
      <div>
        <h2 id="onb-title" class="font-display text-lg">Onboarding</h2>
        <p v-if="tasks.length" class="ledger-label mt-0.5">{{ done }} of {{ tasks.length }} done</p>
      </div>
      <button v-if="!tasks.length" type="button" class="btn-ghost btn-sm" :disabled="busy" @click="start">Start checklist</button>
      <svg v-else viewBox="0 0 100 6" preserveAspectRatio="none" class="h-1.5 w-28 rounded-full bg-panel" aria-hidden="true">
        <rect x="0" y="0" height="6" :width="(100 * done) / tasks.length" class="fill-moss" />
      </svg>
    </div>
    <p v-if="!tasks.length" class="panel-body text-sm text-ink/55">No checklist yet. Starting one copies the steps from the template under Hiring.</p>
    <ul v-else class="divide-y divide-dashed divide-ink/10">
      <li v-for="t in tasks" :key="t.id">
        <label class="flex items-start gap-3 px-5 py-3" :class="canTick ? 'cursor-pointer hover:bg-panel/40' : ''">
          <input type="checkbox" class="mt-1 h-4 w-4 accent-[var(--color-moss)]" :checked="t.done" :disabled="!canTick" @change="toggle(t)" />
          <span class="min-w-0">
            <span class="block text-sm" :class="t.done ? 'text-ink/45 line-through' : 'text-ink'">{{ t.title }}</span>
            <span v-if="t.description" class="block text-xs text-ink/55">{{ t.description }}</span>
          </span>
        </label>
      </li>
    </ul>
  </section>
</template>
