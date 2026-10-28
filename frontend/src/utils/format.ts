// Indian number formatting helpers (lakh/crore grouping).

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const num = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });

export const formatINR = (v: number | null | undefined): string => (v == null ? '—' : inr.format(v));

export const formatNum = (v: number | null | undefined, digits = 2): string =>
  v == null
    ? '—'
    : new Intl.NumberFormat('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(
        v,
      );

export const formatInt = (v: number | null | undefined): string =>
  v == null ? '—' : num.format(Math.round(v));

export const formatPct = (v: number | null | undefined, digits = 2): string =>
  v == null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(digits)}%`;

export const signed = (v: number, formatter: (n: number) => string = formatINR): string =>
  `${v > 0 ? '+' : ''}${formatter(v)}`;

/** Compact INR, e.g. 5,00,000 -> ₹5.00 L, 1,20,00,000 -> ₹1.20 Cr */
export const formatLakh = (v: number): string => {
  const abs = Math.abs(v);
  if (abs >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return formatINR(v);
};

/** Backend timestamps may lack a timezone (SQLite); treat them as UTC. */
export const parseTime = (iso: string): Date => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);

export const formatTime = (iso: string): string =>
  parseTime(iso).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

export const formatClock = (unixSeconds: number): string =>
  new Date(unixSeconds * 1000).toLocaleTimeString('en-IN', { hour12: false });

export const pnlClass = (v: number): string => (v > 0 ? 'text-buy' : v < 0 ? 'text-sell' : 'text-fg-muted');

export const formatDuration = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h ? `${h}h ${m}m` : m ? `${m}m ${s}s` : `${s}s`;
};

/** Axis ticks: whole rupees below a crore so small moves on a ₹5 L account stay readable. */
export const formatAxisINR = (v: number): string =>
  Math.abs(v) >= 1e7 ? formatLakh(v) : `${v < 0 ? '-' : ''}₹${formatInt(Math.abs(v))}`;
