import { ref, watch, type Ref } from "vue";
import { isAxiosError } from "axios";
import api from "@/api/api";

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * State + fetching for a DataTable in server mode, against a DRF list that accepts
 * ?page=&page_size=&search=&ordering= (backend: config/pagination.py).
 *   <DataTable :rows="t.rows.value" :total="t.total.value" :loading="t.loading.value" :page-size="t.pageSize"
 *     v-model:page="t.page.value" v-model:search="t.search.value" v-model:ordering="t.ordering.value" />
 * `params` adds filters; changing them (or the search) goes back to page 1. Call load() for the first fetch.
 */
export function useServerTable<T>(url: string, opts: { pageSize?: number; params?: () => Record<string, unknown> } = {}) {
  const pageSize = opts.pageSize ?? 10;
  const page = ref(1);
  const search = ref("");
  const ordering = ref("");
  const rows = ref([]) as Ref<T[]>;
  const total = ref(0);
  const loading = ref(false);
  const loaded = ref(false);
  const error = ref("");
  let seq = 0;

  async function load() {
    const id = ++seq;
    loading.value = true;
    error.value = "";
    try {
      const { data } = await api.get<Page<T>>(url, {
        params: {
          page: page.value,
          page_size: pageSize,
          search: search.value || undefined,
          ordering: ordering.value || undefined,
          ...opts.params?.(),
        },
      });
      if (id !== seq) return; // superseded by a newer request
      rows.value = data.results;
      total.value = data.count;
      loaded.value = true;
    } catch (e) {
      if (id !== seq) return;
      // the last page emptied (e.g. after a status change): step back instead of erroring
      if (isAxiosError(e) && e.response?.status === 404 && page.value > 1) page.value = 1;
      else error.value = "Couldn't load this list. Please try again.";
    } finally {
      if (id === seq) loading.value = false;
    }
  }

  // One watcher so a search typed on page 3 (DataTable also resets the page) fetches once, not twice.
  const filters = () => JSON.stringify([search.value, opts.params?.() ?? {}]);
  watch([page, ordering, filters], ([p, , f], [, , before]) => {
    if (p !== 1 && f !== before) page.value = 1; // refetches via this watcher
    else load();
  });

  return { page, search, ordering, rows, total, loading, loaded, error, load, pageSize };
}
