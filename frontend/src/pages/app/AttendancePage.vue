<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api/api";
import { useAuth } from "@/stores/auth";
import PageHeader from "../../components/app/ui/PageHeader.vue";
import PunchCard from "../../components/app/attendance/PunchCard.vue";
import MyLog from "../../components/app/attendance/MyLog.vue";
import TeamBoard from "../../components/app/attendance/TeamBoard.vue";
import RegisterGrid from "../../components/app/attendance/RegisterGrid.vue";
import CorrectionsPanel from "../../components/app/attendance/CorrectionsPanel.vue";
import type { Department } from "../../components/app/attendance/attendance";

const { user, hasRole } = useAuth();
const route = useRoute();
const router = useRouter();

const isManager = computed(() => hasRole("manager"));
const isHR = computed(() => hasRole("hr_admin"));

type Tab = "log" | "corrections" | "team" | "register";
const tabs = computed(() => [
  { id: "log" as Tab, label: "My log" },
  { id: "corrections" as Tab, label: "Corrections" },
  ...(isManager.value ? [{ id: "team" as Tab, label: "Team" }, { id: "register" as Tab, label: "Register" }] : []),
]);
const tab = computed<Tab>(() => {
  const q = route.query.tab as Tab;
  return tabs.value.some((t) => t.id === q) ? q : "log";
});
const setTab = (id: Tab) => router.replace({ query: { ...route.query, tab: id === "log" ? undefined : id } });

function onTabKey(e: KeyboardEvent, i: number) {
  const n = tabs.value.length;
  const next = e.key === "ArrowRight" ? (i + 1) % n : e.key === "ArrowLeft" ? (i - 1 + n) % n : -1;
  if (next < 0) return;
  setTab(tabs.value[next]!.id);
  document.getElementById(`att-tab-${tabs.value[next]!.id}`)?.focus();
}

const refreshKey = ref(0);

// Department filter options: HR sees all, managers only the departments they run.
const departments = ref<Department[]>([]);
watch(
  isManager,
  async (ok) => {
    if (!ok || departments.value.length) return;
    try {
      const { data } = await api.get<(Department & { manager: { id: number } | null })[]>("org/departments/");
      departments.value = isHR.value ? data : data.filter((d) => d.manager?.id === user.value?.id);
    } catch {
      departments.value = []; // filter is optional; the views still work unfiltered
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="space-y-8">
    <PageHeader
      eyebrow="A2 · Attendance"
      title="Attendance"
      description="Punch in and out, and keep an eye on your month. Times are in Nepal time."
    />

    <PunchCard @changed="refreshKey++" />

    <section>
      <div v-if="tabs.length > 1" role="tablist" aria-label="Attendance views" class="mb-5 flex gap-1 overflow-x-auto border-b border-ink/10">
        <button
          v-for="(t, i) in tabs"
          :id="`att-tab-${t.id}`"
          :key="t.id"
          type="button"
          role="tab"
          :aria-selected="tab === t.id"
          :aria-controls="tab === t.id ? `att-panel-${t.id}` : undefined"
          :tabindex="tab === t.id ? 0 : -1"
          class="-mb-px border-b-2 px-4 py-2.5 text-sm whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flag/40"
          :class="tab === t.id ? 'border-flag font-medium text-ink' : 'border-transparent text-ink/55 hover:text-ink'"
          @click="setTab(t.id)"
          @keydown="onTabKey($event, i)"
        >
          {{ t.label }}
        </button>
      </div>
      <h2 v-else class="mb-4 font-display text-xl">My log</h2>

      <div :id="`att-panel-${tab}`" role="tabpanel" :aria-labelledby="tabs.length > 1 ? `att-tab-${tab}` : undefined">
        <MyLog v-if="tab === 'log'" :refresh-key="refreshKey" />
        <CorrectionsPanel v-else-if="tab === 'corrections'" :can-approve="isManager" :start-open="route.query.new === '1'" />
        <TeamBoard v-else-if="tab === 'team'" :departments="departments" />
        <RegisterGrid v-else :departments="departments" :can-edit="isHR" />
      </div>
    </section>
  </div>
</template>
