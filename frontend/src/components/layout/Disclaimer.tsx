export const DISCLAIMER =
  'NanoEX Web is an educational simulation. All trading is paper trading with virtual money: no real orders are placed and nothing here is financial advice.';

export function PaperBadge() {
  return (
    <span className="rounded border border-amber/60 bg-amber-soft px-2 py-0.5 font-mono text-[11px] font-semibold tracking-wider text-amber">
      PAPER TRADING · SIMULATION
    </span>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-ink-700 px-6 py-3 text-center text-[11px] text-fg-dim">
      {DISCLAIMER}
    </footer>
  );
}
