<script setup lang="ts">
import { computed, ref } from "vue";
import api from "@/api/api";
import { parseError, type BulkResult } from "./calendar";

const emit = defineEmits<{ done: [] }>();

const text = ref("");
const posting = ref(false);
const result = ref<BulkResult | null>(null);
const error = ref("");
const rowErrors = ref<{ line: number; msg: string }[]>([]);

const LINE = /^(\d{4}-\d{2}-\d{2})\s*,\s*(.+)$/;

/** Each non-blank, non-# line → {line, date, name} or a parse problem. */
const parsed = computed(() => {
  const rows: { line: number; date: string; name: string }[] = [];
  const problems: { line: number; msg: string }[] = [];
  text.value.split(/\r?\n/).forEach((raw, i) => {
    const s = raw.trim();
    if (!s || s.startsWith("#")) return;
    const m = LINE.exec(s);
    const valid = m && !Number.isNaN(Date.parse(m[1]!));
    if (!m || !valid) problems.push({ line: i + 1, msg: `Expected "YYYY-MM-DD, Name" — got "${s.slice(0, 40)}"` });
    else if (m[2]!.trim().length > 150) problems.push({ line: i + 1, msg: "Name is longer than 150 characters." });
    else rows.push({ line: i + 1, date: m[1]!, name: m[2]!.trim() });
  });
  return { rows, problems };
});

async function submit() {
  const { rows, problems } = parsed.value;
  result.value = null;
  error.value = "";
  rowErrors.value = [];
  if (problems.length || !rows.length) return;
  if (rows.length > 366) {
    error.value = "At most 366 rows per paste.";
    return;
  }
  posting.value = true;
  try {
    const { data } = await api.post<BulkResult>("calendar/holidays/bulk/", rows.map(({ date, name }) => ({ date, name })));
    result.value = data;
    text.value = "";
    emit("done");
  } catch (e) {
    const err = parseError(e);
    // Per-row errors arrive index-aligned (as a list, or an object keyed by index).
    const body = err.data;
    if (body && typeof body === "object" && !("detail" in body)) {
      const entries = Array.isArray(body) ? body.map((v, i) => [String(i), v] as const) : Object.entries(body);
      for (const [idx, v] of entries) {
        const row = rows[Number(idx)];
        if (!row || !v || (typeof v === "object" && !Object.keys(v).length)) continue;
        const msg = typeof v === "object" ? Object.entries(v).map(([f, m]) => `${f}: ${([] as unknown[]).concat(m).join(" ")}`).join("; ") : String(v);
        rowErrors.value.push({ line: row.line, msg });
      }
    }
    if (!rowErrors.value.length) error.value = err.detail || Object.values(err.fields).join(" ") || "Import failed.";
  } finally {
    posting.value = false;
  }
}
</script>

<template>
  <form class="grid gap-3" @submit.prevent="submit">
    <div class="field">
      <label for="bulk-holidays" class="ledger-label">Bulk paste</label>
      <textarea
        id="bulk-holidays"
        v-model="text"
        rows="6"
        class="input font-mono text-[12.5px]"
        placeholder="2027-01-11, Prithvi Jayanti&#10;2027-01-15, Maghe Sankranti"
        aria-describedby="bulk-help"
        spellcheck="false"
      />
      <p id="bulk-help" class="text-xs text-ink/50">
        One holiday per line as <span class="font-mono">YYYY-MM-DD, Name</span>. Dates that already have a holiday are skipped, not overwritten.
      </p>
    </div>

    <ul v-if="parsed.problems.length || rowErrors.length" class="space-y-1 rounded-lg border border-rust/30 bg-rust/[0.06] px-3 py-2 text-xs text-rust" role="alert">
      <li v-for="p in [...parsed.problems, ...rowErrors]" :key="`${p.line}-${p.msg}`">
        <span class="readout">L{{ p.line }}</span> · {{ p.msg }}
      </li>
    </ul>
    <p v-if="error" class="text-xs text-rust" role="alert">{{ error }}</p>

    <div class="flex flex-wrap items-center gap-3">
      <button type="submit" class="btn-ink btn-sm" :disabled="posting || !parsed.rows.length || !!parsed.problems.length">
        {{ posting ? "Importing…" : `Import ${parsed.rows.length || ""} holiday${parsed.rows.length === 1 ? "" : "s"}` }}
      </button>
      <span v-if="parsed.rows.length" class="readout text-[11px] text-ink/45">{{ parsed.rows.length }} row(s) ready</span>
    </div>

    <div v-if="result" class="rounded-lg border border-dashed border-ink/20 px-3 py-2.5 text-sm" role="status">
      <p>
        <span class="font-medium text-moss">{{ result.created.length }} created</span>
        <span class="text-ink/40"> · </span>
        <span :class="result.skipped.length ? 'font-medium text-contour-ink' : 'text-ink/50'">{{ result.skipped.length }} skipped</span>
      </p>
      <ul v-if="result.skipped.length" class="mt-1.5 space-y-0.5 text-xs text-ink/60">
        <li v-for="s in result.skipped" :key="`${s.date}-${s.name}`">
          <span class="readout">{{ s.date }}</span> {{ s.name }} — {{ s.reason }}
        </li>
      </ul>
    </div>
  </form>
</template>
