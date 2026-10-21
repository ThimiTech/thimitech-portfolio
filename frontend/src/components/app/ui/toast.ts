import { reactive } from "vue";

export type ToastTone = "success" | "error" | "info";
export interface Toast {
  id: number;
  tone: ToastTone;
  message: string;
}

/** Shared toast queue, rendered by ToastHost.vue in AppLayout. */
export const toasts = reactive<Toast[]>([]);
let seq = 0;
const timers = new Map<number, number>();

export function dismissToast(id: number) {
  clearTimeout(timers.get(id));
  timers.delete(id);
  const i = toasts.findIndex((t) => t.id === id);
  if (i >= 0) toasts.splice(i, 1);
}

function push(tone: ToastTone, message: string, ms = tone === "error" ? 7000 : 4000) {
  const id = ++seq;
  toasts.push({ id, tone, message });
  if (toasts.length > 4) dismissToast(toasts[0]!.id);
  timers.set(id, window.setTimeout(() => dismissToast(id), ms));
  return id;
}

export const toast = {
  success: (message: string) => push("success", message),
  error: (message: string) => push("error", message),
  info: (message: string) => push("info", message),
};
