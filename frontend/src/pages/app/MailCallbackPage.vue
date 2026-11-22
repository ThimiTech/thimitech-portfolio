<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "@/api/api";
import EmptyState from "@/components/app/ui/EmptyState.vue";
import { toast } from "@/components/app/ui/toast";
import { errMsg } from "@/components/app/attendance/attendance";

// Zoho sends people back here after they allow access (redirect URI {FRONTEND_URL}/app/mail/callback).
const route = useRoute();
const router = useRouter();
const error = ref("");

onMounted(async () => {
  const q = route.query;
  const code = typeof q.code === "string" ? q.code : "";
  const state = typeof q.state === "string" ? q.state : "";
  if (!code || !state) {
    error.value = q.error === "access_denied" ? "Access wasn't allowed in Zoho, so nothing was connected." : "Zoho didn't send a sign-in code back.";
    return;
  }
  try {
    const server = q["accounts-server"];
    await api.post("mail/callback/", { code, state, accounts_server: typeof server === "string" ? server : "" });
    toast.success("Zoho Mail connected.");
    router.replace({ name: "app-mail" });
  } catch (e) {
    error.value = errMsg(e, "Couldn't finish connecting to Zoho.");
  }
});
</script>

<template>
  <div class="panel mx-auto mt-10 max-w-lg">
    <EmptyState v-if="error" title="Mailbox not connected" :hint="error">
      <RouterLink :to="{ name: 'app-mail' }" class="btn-primary">Back to Mail</RouterLink>
    </EmptyState>
    <EmptyState v-else title="Connecting your mailbox…" hint="Finishing the sign-in with Zoho." />
  </div>
</template>
