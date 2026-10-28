import clsx from 'clsx';
import { useToastStore } from '../../store/toastStore';

const tone = {
  success: 'border-buy/50',
  error: 'border-sell/60',
  info: 'border-info/50',
  warning: 'border-amber/60',
};

export function Toaster() {
  const { toasts, dismiss } = useToastStore();
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={clsx(
            'pointer-events-auto rounded-md border-l-4 bg-ink-800 px-4 py-3 shadow-lg',
            tone[t.kind],
          )}
          role="alert"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="text-sm font-semibold text-fg">{t.title}</div>
            <button className="text-fg-dim hover:text-fg" onClick={() => dismiss(t.id)} aria-label="Dismiss">
              ×
            </button>
          </div>
          {t.message && <div className="mt-0.5 text-xs text-fg-muted">{t.message}</div>}
        </div>
      ))}
    </div>
  );
}
