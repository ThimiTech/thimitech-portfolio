import { reactive } from "vue";

export interface ConfirmOptions {
  title: string;
  body: string;
  confirmLabel?: string;
  danger?: boolean;
}

/** Single shared dialog state, rendered by ConfirmHost.vue in AppLayout. */
export const confirmState = reactive<{ open: boolean; opts: ConfirmOptions; resolve: ((ok: boolean) => void) | null }>({
  open: false,
  opts: { title: "", body: "" },
  resolve: null,
});

/** In-app replacement for window.confirm(); resolves true when the user confirms. */
export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  confirmState.resolve?.(false);
  return new Promise((resolve) => {
    Object.assign(confirmState, { open: true, opts, resolve });
  });
}

export function settleConfirm(ok: boolean) {
  const r = confirmState.resolve;
  Object.assign(confirmState, { open: false, resolve: null });
  r?.(ok);
}
