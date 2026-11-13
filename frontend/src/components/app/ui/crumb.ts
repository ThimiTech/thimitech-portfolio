import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

/** The name of the thing on screen (a project, a person). A page sets it once loaded; the shell shows it in the
 *  breadcrumb and the browser tab, and remembers it under "Recent" in search. The shell clears it on navigation. */
export const pageTitle = ref("");

/** A page's active tab, kept in `?tab=` so a tab can be linked, bookmarked and reached with Back. */
export function useTabQuery(ids: () => string[], fallback: string) {
  const route = useRoute();
  const router = useRouter();
  return computed({
    get: () => (ids().includes(String(route.query.tab)) ? String(route.query.tab) : fallback),
    set: (t: string) => void router.replace({ query: { ...route.query, tab: t === fallback ? undefined : t } }),
  });
}
