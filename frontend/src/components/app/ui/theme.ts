import { computed, ref } from "vue";

export type ThemeMode = "light" | "dark" | "system";
const KEY = "thimi.theme";

function read(): ThemeMode {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

const mode = ref<ThemeMode>(read());
const media = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
const systemDark = ref(!!media?.matches);
media?.addEventListener?.("change", (e) => (systemDark.value = e.matches));

const isDark = computed(() => (mode.value === "system" ? systemDark.value : mode.value === "dark"));

/** Workspace theme. Persisted per browser; "system" follows prefers-color-scheme. */
export function useTheme() {
  function setMode(m: ThemeMode) {
    mode.value = m;
    try {
      if (m === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, m);
    } catch {
      /* private mode: theme just isn't remembered */
    }
  }
  const toggle = () => setMode(isDark.value ? "light" : "dark");
  return { mode, isDark, setMode, toggle };
}
