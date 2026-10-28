import { useState } from 'react';
import { Card, PageHeader } from '../components/ui';
import { PriceLine } from '../components/charts/Charts';
import { OrderTicket } from '../components/trading/OrderTicket';
import { Watchlist } from '../components/trading/Watchlist';
import { usePriceSeries } from './Dashboard';
import { quoteKey, useMarketStore } from '../store/marketStore';
import type { Exchange } from '../types';
import { formatNum } from '../utils/format';

export default function LiveMarket() {
  const [symbol, setSymbol] = useState('TCS');
  const [exchange, setExchange] = useState<Exchange>('NSE');
  const nse = useMarketStore((s) => s.quotes[quoteKey(symbol, 'NSE')]);
  const bse = useMarketStore((s) => s.quotes[quoteKey(symbol, 'BSE')]);
  const series = usePriceSeries(symbol, exchange);

  return (
    <div>
      <PageHeader
        title="Live Market"
        subtitle="Simulated ticks streamed over WebSocket. Same stock, two exchanges."
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <div className="grid grid-cols-2 gap-3">
            {[nse, bse].map((q, i) => (
              <div key={i} className="rounded-lg border border-ink-700 bg-ink-850 px-4 py-3">
                <div className="text-xs text-fg-dim">
                  {symbol} · {i === 0 ? 'NSE' : 'BSE'}
                </div>
                <div className="font-mono text-2xl font-semibold">{q ? formatNum(q.last) : '—'}</div>
                <div className="font-mono text-xs text-fg-muted">
                  {q ? `${formatNum(q.bid)} × ${formatNum(q.ask)}` : ''}
                </div>
              </div>
            ))}
          </div>
          <Card
            title={`${symbol} · ${exchange} price`}
            actions={
              <div className="flex gap-1">
                {(['NSE', 'BSE'] as Exchange[]).map((x) => (
                  <button
                    key={x}
                    onClick={() => setExchange(x)}
                    className={`rounded px-2 py-0.5 text-xs ${x === exchange ? 'bg-amber text-ink-950' : 'text-fg-muted'}`}
                  >
                    {x}
                  </button>
                ))}
              </div>
            }
          >
            <PriceLine data={series} height={300} />
          </Card>
          <Card title={`${exchange} quotes`}>
            <Watchlist exchange={exchange} selected={symbol} onSelect={setSymbol} />
          </Card>
        </div>
        <OrderTicket
          symbol={symbol}
          exchange={exchange}
          onSymbol={(s, e) => (setSymbol(s), setExchange(e))}
        />
      </div>
    </div>
  );
}
