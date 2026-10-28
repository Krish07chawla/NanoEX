import { create } from 'zustand';

export type ToastKind = 'success' | 'error' | 'info' | 'warning';
export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  message?: string;
}

const TOAST_MS = 4500;
let nextId = 1;

interface ToastState {
  toasts: Toast[];
  push: (kind: ToastKind, title: string, message?: string) => void;
  dismiss: (id: number) => void;
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  push: (kind, title, message) => {
    const id = nextId++;
    set({ toasts: [...get().toasts.slice(-4), { id, kind, title, message }] });
    setTimeout(() => get().dismiss(id), TOAST_MS);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

export const toast = {
  success: (t: string, m?: string) => useToastStore.getState().push('success', t, m),
  error: (t: string, m?: string) => useToastStore.getState().push('error', t, m),
  info: (t: string, m?: string) => useToastStore.getState().push('info', t, m),
  warning: (t: string, m?: string) => useToastStore.getState().push('warning', t, m),
};
