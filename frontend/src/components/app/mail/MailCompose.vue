<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import api from "@/api/api";
import Modal from "@/components/app/ui/Modal.vue";
import { toast } from "@/components/app/ui/toast";
import { confirmDialog } from "@/components/app/ui/confirm";
import { errMsg } from "@/components/app/attendance/attendance";
import { composeHtml, fileSize, replyFields, type ComposeMode, type MailMessage, type MailStatus, type Upload } from "./mail";

const props = defineProps<{ open: boolean; mode: ComposeMode; source: MailMessage | null; status: MailStatus }>();
const emit = defineEmits<{ close: []; sent: [] }>();

interface Pending {
  key: number;
  name: string;
  size: number;
  upload: Upload | null;
  error: string;
}

const form = reactive({ from: "", to: "", cc: "", bcc: "", subject: "", text: "" });
const showCc = ref(false);
const files = ref<Pending[]>([]);
const sending = ref(false);
let seq = 0;

const title = computed(() => ({ new: "New message", reply: "Reply", replyall: "Reply all", forward: "Forward" })[props.mode]);
const uploading = computed(() => files.value.some((f) => !f.upload && !f.error));
const dirty = computed(() => !!(form.text.trim() || files.value.length || (props.mode === "new" && (form.to || form.subject))));

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    const me = props.status.send_from.map((s) => s.address).concat(props.status.email);
    const prefill = props.source && props.mode !== "new" ? replyFields(props.source, props.mode, me) : { to: "", cc: "", subject: "" };
    Object.assign(form, { from: props.status.send_from[0]?.address || props.status.email, bcc: "", text: "", ...prefill });
    showCc.value = !!prefill.cc;
    files.value = [];
  },
);

async function addFiles(e: Event) {
  const input = e.target as HTMLInputElement;
  for (const file of Array.from(input.files || [])) {
    const item = reactive<Pending>({ key: ++seq, name: file.name, size: file.size, upload: null, error: "" });
    files.value.push(item);
    const body = new FormData();
    body.append("file", file);
    api
      .post<Upload>("mail/attachments/", body)
      .then(({ data }) => (item.upload = data))
      .catch((err) => (item.error = errMsg(err, "Upload failed")));
  }
  input.value = "";
}
const removeFile = (key: number) => (files.value = files.value.filter((f) => f.key !== key));

async function close() {
  if (sending.value) return;
  if (dirty.value && !(await confirmDialog({ title: "Discard this message?", body: "What you wrote will be lost.", confirmLabel: "Discard", danger: true }))) return;
  emit("close");
}

async function send() {
  if (!form.to.trim()) return toast.error("Add at least one recipient.");
  if (uploading.value) return toast.error("Wait for the attachments to finish uploading.");
  sending.value = true;
  try {
    await api.post("mail/send/", {
      from_address: form.from || undefined,
      to: form.to,
      cc: form.cc,
      bcc: form.bcc,
      subject: form.subject,
      content: composeHtml(form.text, props.source ?? undefined, props.mode),
      format: "html",
      attachments: files.value.flatMap((f) => (f.upload ? [f.upload] : [])),
      ...(props.source && props.mode !== "new"
        ? { reply_to: props.source.id, action: props.mode === "forward" ? "forward" : "reply" }
        : {}),
    });
    toast.success("Sent.");
    emit("sent");
  } catch (e) {
    toast.error(errMsg(e, "Couldn't send the message."));
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <Modal :open="open" :title="title" width="max-w-2xl" @close="close">
    <form class="grid gap-3" @submit.prevent="send">
      <label v-if="status.send_from.length > 1" class="field">
        <span class="ledger-label">From</span>
        <select v-model="form.from" class="input">
          <option v-for="s in status.send_from" :key="s.address" :value="s.address">{{ s.name ? `${s.name} <${s.address}>` : s.address }}</option>
        </select>
      </label>
      <div class="field">
        <div class="flex items-center justify-between">
          <label for="mail-to" class="ledger-label">To</label>
          <button v-if="!showCc" type="button" class="text-xs text-river hover:text-flag" @click="showCc = true">Cc / Bcc</button>
        </div>
        <input id="mail-to" v-model="form.to" class="input" autocomplete="email" placeholder="name@example.com, another@example.com" />
      </div>
      <template v-if="showCc">
        <label class="field"><span class="ledger-label">Cc</span><input v-model="form.cc" class="input" /></label>
        <label class="field"><span class="ledger-label">Bcc</span><input v-model="form.bcc" class="input" /></label>
      </template>
      <label class="field"><span class="ledger-label">Subject</span><input v-model="form.subject" class="input" maxlength="998" /></label>
      <label class="field">
        <span class="ledger-label">Message</span>
        <textarea v-model="form.text" rows="10" class="input font-[inherit]" />
      </label>
      <p v-if="source && mode !== 'new'" class="text-xs text-ink/55">
        The original message is quoted below what you write{{ mode === "forward" ? ". Its attachments are not forwarded." : "." }}
      </p>

      <div>
        <ul v-if="files.length" class="mb-2 flex flex-wrap gap-2">
          <li v-for="f in files" :key="f.key" class="flex items-center gap-2 rounded-lg border border-ink/10 bg-panel px-2.5 py-1 text-xs">
            <span class="max-w-48 truncate">{{ f.name }}</span>
            <span class="text-ink/50">{{ f.error || (f.upload ? fileSize(f.size) : "Uploading…") }}</span>
            <button type="button" class="text-ink/50 hover:text-flag" :aria-label="`Remove ${f.name}`" @click="removeFile(f.key)">×</button>
          </li>
        </ul>
        <label class="btn-ghost inline-flex cursor-pointer">
          Attach files
          <input type="file" multiple class="sr-only" @change="addFiles" />
        </label>
      </div>
    </form>
    <template #footer>
      <button type="button" class="btn-ghost" :disabled="sending" @click="close">Discard</button>
      <button type="button" class="btn-primary" :disabled="sending || uploading" @click="send">{{ sending ? "Sending…" : "Send" }}</button>
    </template>
  </Modal>
</template>
