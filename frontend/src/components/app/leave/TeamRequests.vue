<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import api from "@/api/api";
import EmptyState from "../ui/EmptyState.vue";
import RequestsTable from "./RequestsTable.vue";
import { type LeaveRequest, type LeaveStatus, STATUSES, cancelRequest, currentYear, errorMessage } from "./leave";

const emit = defineEmits<{ changed: [] }>();

const year = ref(currentYear());
const years = [currentYear() + 1, currentYear(), currentYear() - 1, currentYear() - 2];
const status = ref<LeaveStatus | "">("");
const person = ref<number | "">("");

const rows = ref<LeaveRequest[]>([]);
const loading = ref(true);
const error = ref("");
const busyId = ref<number | null>(null);
const actionError = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const { data } = await api.get<LeaveRequest[]>("leave/requests/", { params: { scope: "team", year: year.value } });
    rows.value = data;
  } catch (e) {
    error.value = errorMessage(e, "Couldn't load team requests.");
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(year, load);
defineExpose({ load });

// Status + person filter client-side: the year fetch is already bounded.
const people = computed(() => {
  const m = new Map<number, string>();
  rows.value.forEach((r) => m.set(r.user.id, r.user.full_name));
  return [...m].sort((a, b) => a[1].localeCompare(b[1]));
});
const shown = computed(() =>
  rows.value.filter((r) => (!status.value || r.status === status.value) && (!person.value || r.user.id === person.value)),
);

async function onCancel(r: LeaveRequest) {
  busyId.value = r.id;
  actionError.value = "";
  try {
    const updated = await cancelRequest(r, false);
    if (!updated) return;
    rows.value = rows.value.map((x) => (x.id === r.id ? updated : x));
    emit("changed");
  } catch (e) {
    actionError.value = errorMessage(e);
  } finally {
    busyId.value = null;
  }
}
</script>

<template>
  <section class="panel" aria-labelledby="team-heading">
    <div class="panel-head flex-wrap">
      <h2 id="team-heading" class="font-display text-lg font-medium">Team ledger</h2>
      <div class="flex flex-wrap items-end gap-2">
        <div class="field">
          <label for="team-year" class="ledger-label">Year</label>
          <select id="team-year" v-model.number="year" class="input readout py-1.5 text-xs">
            <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>
        <div class="field">
          <label for="team-status" class="ledger-label">Status</label>
          <select id="team-status" v-model="status" class="input py-1.5 text-xs capitalize">
            <option value="">All</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="field">
          <label for="team-person" class="ledger-label">Person</label>
          <select id="team-person" v-model="person" class="input max-w-[180px] py-1.5 text-xs">
            <option value="">Everyone</option>
            <option v-for="[id, name] in people" :key="id" :value="id">{{ name }}</option>
          </select>
        </div>
      </div>
    </div>

    <p v-if="actionError" class="mx-5 mt-4 text-sm text-rust" role="alert">{{ actionError }}</p>

    <div v-if="loading" class="grid gap-2 p-5" aria-busy="true" aria-label="Loading team requests">
      <div v-for="i in 4" :key="i" class="h-10 rounded-md border border-dashed border-ink/15 motion-safe:animate-pulse" />
    </div>
    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 p-5" role="alert">
      <p class="text-sm text-rust">{{ error }}</p>
      <button class="btn-ghost btn-sm" @click="load">Retry</button>
    </div>
    <EmptyState
      v-else-if="!shown.length"
      :title="rows.length ? 'No requests match' : `No team requests in ${year}`"
      :hint="rows.length ? 'Try clearing a filter.' : 'Requests from people you manage will be listed here.'"
    />
    <RequestsTable v-else :requests="shown" show-person :busy-id="busyId" :caption="`Team leave requests, ${year}`" @cancel="onCancel" />
  </section>
</template>
