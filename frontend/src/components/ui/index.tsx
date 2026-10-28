// Small, reusable UI primitives in the trading-terminal style.
import clsx from 'clsx';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';

type Variant = 'primary' | 'buy' | 'sell' | 'ghost' | 'danger';

const variants: Record<Variant, string> = {
  primary: 'bg-amber text-ink-950 hover:brightness-110',
  buy: 'bg-buy text-ink-950 hover:brightness-110',
  sell: 'bg-sell text-white hover:brightness-110',
  ghost: 'border border-ink-600 text-fg hover:bg-ink-700',
  danger: 'border border-sell/60 text-sell hover:bg-sell-soft',
};

export function Button({
  variant = 'primary',
  loading,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading && <Spinner small />}
      {children}
    </button>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx('rounded-lg border border-ink-700 bg-ink-850', className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-2.5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-fg-muted">{title}</h2>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: 'buy' | 'sell' | 'amber';
}) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-850 px-4 py-3">
      <div className="text-[11px] font-medium uppercase tracking-wider text-fg-dim">{label}</div>
      <div
        className={clsx(
          'mt-1 font-mono text-xl font-semibold',
          tone === 'buy' && 'text-buy',
          tone === 'sell' && 'text-sell',
          tone === 'amber' && 'text-amber',
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-fg-muted">{sub}</div>}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-fg-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-fg-dim">{hint}</span>}
    </label>
  );
}

const inputCls =
  'w-full rounded-md border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-fg placeholder:text-fg-dim focus:border-amber focus:outline-none';

export const Input = (props: InputHTMLAttributes<HTMLInputElement>) => (
  <input {...props} className={clsx(inputCls, props.className)} />
);

export const Select = (props: SelectHTMLAttributes<HTMLSelectElement>) => (
  <select {...props} className={clsx(inputCls, props.className)} />
);

export function Badge({
  children,
  tone = 'muted',
}: {
  children: ReactNode;
  tone?: 'buy' | 'sell' | 'amber' | 'muted' | 'info';
}) {
  const tones = {
    buy: 'bg-buy-soft text-buy',
    sell: 'bg-sell-soft text-sell',
    amber: 'bg-amber-soft text-amber',
    muted: 'bg-ink-700 text-fg-muted',
    info: 'bg-info/15 text-info',
  };
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold',
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Spinner({ small }: { small?: boolean }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={clsx(
        'inline-block animate-spin rounded-full border-2 border-current border-t-transparent',
        small ? 'h-3.5 w-3.5' : 'h-6 w-6 text-amber',
      )}
    />
  );
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm text-fg-muted">
      <Spinner /> {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-sell/30 bg-sell-soft py-8 text-sm text-sell">
      <span>{message}</span>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-8 text-center text-sm text-fg-dim">{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-fg">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

export function SideTag({ side }: { side: 'BUY' | 'SELL' }) {
  return <Badge tone={side === 'BUY' ? 'buy' : 'sell'}>{side}</Badge>;
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={clsx('relative h-6 w-11 rounded-full transition', checked ? 'bg-amber' : 'bg-ink-600')}
    >
      <span
        className={clsx(
          'absolute top-0.5 h-5 w-5 rounded-full bg-ink-950 transition',
          checked ? 'left-[22px]' : 'left-0.5',
        )}
      />
    </button>
  );
}
