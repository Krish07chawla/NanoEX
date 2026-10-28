import clsx from 'clsx';
import { useRef } from 'react';
import { useMarketStore, quoteKey } from '../../store/marketStore';
import type { Exchange } from '../../types';
import { SYMBOLS } from '../../utils/symbols';
import { formatInt, formatNum } from '../../utils/format';

/** Live quotes for every symbol on one exchange; price flashes green/red on change. */
export function Watchlist({
  exchange,
  selected,
  onSelect,
}: {
  exchange: Exchange;
  selected?: string;
  onSelect?: (s: string) => void;
}) {
  const quotes = useMarketStore((s) => s.quotes);
  const prev = useRef<Record<string, number>>({});

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-ink-700 text-[11px] uppercase tracking-wider text-fg-dim">
          <th className="px-3 py-2 text-left font-medium">Symbol</th>
          <th className="px-3 py-2 text-right font-medium">Bid</th>
          <th className="px-3 py-2 text-right font-medium">Ask</th>
          <th className="px-3 py-2 text-right font-medium">LTP</th>
          <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">Volume</th>
        </tr>
      </thead>
      <tbody>
        {SYMBOLS.map((symbol) => {
          const q = quotes[quoteKey(symbol, exchange)];
          const last = prev.current[symbol];
          const dir = q && last != null ? Math.sign(q.last - last) : 0;
          if (q) prev.current[symbol] = q.last;
          return (
            <tr
              key={symbol}
              onClick={() => onSelect?.(symbol)}
              className={clsx(
                'cursor-pointer border-b border-ink-800 hover:bg-ink-800/60',
                selected === symbol && 'bg-amber-soft',
              )}
            >
              <td className="px-3 py-2 font-semibold">{symbol}</td>
              <td className="px-3 py-2 text-right font-mono text-buy">{q ? formatNum(q.bid) : '—'}</td>
              <td className="px-3 py-2 text-right font-mono text-sell">{q ? formatNum(q.ask) : '—'}</td>
              <td
                className={clsx(
                  'px-3 py-2 text-right font-mono',
                  dir > 0 && 'text-buy',
                  dir < 0 && 'text-sell',
                )}
              >
                {q ? formatNum(q.last) : '—'}
              </td>
              <td className="hidden px-3 py-2 text-right font-mono text-fg-muted sm:table-cell">
                {q ? formatInt(q.volume) : '—'}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
