import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, PageHeader, StatCard, Badge } from '../components/ui';
import { Table } from '../components/ui/Table';
import { PriceLine } from '../components/charts/Charts';
import { OrderTicket } from '../components/trading/OrderTicket';
import { Watchlist } from '../components/trading/Watchlist';
import { useApi } from '../hooks/useApi';
import { get } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import { quoteKey, useMarketStore } from '../store/marketStore';
import type { Exchange, Order, PerfMetrics, PortfolioSummary } from '../types';
import {
  formatClock,
  formatDuration,
  formatINR,
  formatNum,
  formatPct,
  formatTime,
  pnlClass,
  signed,
} from '../utils/format';

export function statusTone(status: string) {
  if (status === 'FILLED' || status === 'COMPLETED') return 'buy' as const;
  if (status === 'REJECTED' || status === 'FAILED') return 'sell' as const;
  if (status === 'NEW' || status === 'PARTIAL' || status === 'HEDGED') return 'amber' as const;
  return 'muted' as const;
}

export function usePriceSeries(symbol: string, exchange: Exchange) {
  const key = quoteKey(symbol, exchange);
  const history = useMarketStore((s) => s.history[key]);
  useEffect(() => {
    get<{ t: number; price: number }[]>(`/market/${symbol}/history`, { exchange, limit: 240 })
      .then((pts) => useMarketStore.getState().seedHistory(key, pts))
      .catch(() => undefined);
  }, [key, symbol, exchange]);
  return useMemo(() => (history ?? []).map((p) => ({ label: formatClock(p.t), price: p.price })), [history]);
}

export default function Dashboard() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [exchange, setExchange] = useState<Exchange>('NSE');
  const version = useAccountStore((s) => s.version);
  const summary = useApi(() => get<PortfolioSummary>('/portfolio/summary'), [version], 5000);
  const perf = useApi(() => get<PerfMetrics>('/dashboard/performance'), [], 3000);
  const orders = useApi(() => get<Order[]>('/orders', { size: 8 }), [version]);
  const series = usePriceSeries(symbol, exchange);
  const s = summary.data;
  const p = perf.data;

  return (
    <div>
      <PageHeader
        title="Trading Floor"
        subtitle="Live simulated NSE/BSE market. Everything here is paper trading."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Equity"
          value={s ? formatINR(s.equity) : '—'}
          sub={s ? `Capital added ${formatINR(s.capital_added)}` : undefined}
        />
        <StatCard
          label="Total P&L"
          value={s ? signed(s.total_pnl) : '—'}
          tone={s && s.total_pnl >= 0 ? 'buy' : 'sell'}
          sub={s ? formatPct(s.total_return_pct) : undefined}
        />
        <StatCard
          label="Available cash"
          value={s ? formatINR(s.available) : '—'}
          sub={s ? `Blocked ${formatINR(s.blocked)}` : undefined}
        />
        <StatCard
          label="Open positions"
          value={s?.open_positions ?? '—'}
          sub={s ? `${s.trade_count} fills total` : undefined}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Orders / sec (1m)" value={p ? formatNum(p.orders_per_sec, 3) : '—'} tone="amber" />
        <StatCard
          label="Avg order latency"
          value={p ? `${formatNum(p.avg_order_latency_us / 1000)} ms` : '—'}
          sub="risk check + match + settle"
        />
        <StatCard
          label="Tick-to-trade"
          value={p ? `${formatNum(p.avg_tick_to_trade_us / 1000)} ms` : '—'}
          sub="strategy bots"
        />
        <StatCard
          label="Uptime"
          value={p ? formatDuration(p.uptime_seconds) : '—'}
          sub={p ? `${p.ticks_total.toLocaleString('en-IN')} ticks` : undefined}
        />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card
            title={`${symbol} · ${exchange}`}
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
            <PriceLine data={series} />
          </Card>
          <Card
            title="Watchlist"
            actions={<span className="text-xs text-fg-dim">click a row to chart it</span>}
          >
            <Watchlist exchange={exchange} selected={symbol} onSelect={setSymbol} />
          </Card>
        </div>
        <div className="space-y-4">
          <OrderTicket
            symbol={symbol}
            exchange={exchange}
            onSymbol={(sym, ex) => (setSymbol(sym), setExchange(ex))}
            onPlaced={() => orders.refetch()}
          />
          <Card
            title="Recent orders"
            actions={
              <Link to="/app/history" className="text-xs text-amber">
                History →
              </Link>
            }
          >
            <Table<Order>
              dense
              rows={orders.data ?? []}
              rowKey={(o) => o.id}
              empty="No orders yet. Place one above."
              columns={[
                {
                  key: 'sym',
                  header: 'Order',
                  render: (o) => (
                    <span>
                      {o.side === 'BUY' ? (
                        <span className="text-buy">B</span>
                      ) : (
                        <span className="text-sell">S</span>
                      )}{' '}
                      {o.quantity} {o.symbol}
                    </span>
                  ),
                },
                {
                  key: 'st',
                  header: 'Status',
                  render: (o) => <Badge tone={statusTone(o.status)}>{o.status}</Badge>,
                },
                {
                  key: 'px',
                  header: 'Avg',
                  align: 'right',
                  render: (o) => (o.avg_fill_price ? formatNum(o.avg_fill_price) : '—'),
                },
                {
                  key: 't',
                  header: 'Time',
                  align: 'right',
                  render: (o) => (
                    <span className="text-fg-dim">{formatTime(o.created_at).split(', ')[1]}</span>
                  ),
                },
              ]}
            />
          </Card>
          {s && (
            <Card title="Realized vs unrealized">
              <div className="space-y-2 text-sm">
                <Row label="Realized (gross)" value={s.realized_pnl} />
                <Row label="Charges paid" value={-s.total_fees} />
                <Row label="Unrealized" value={s.unrealized_pnl} />
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between">
      <span className="text-fg-muted">{label}</span>
      <span className={`font-mono ${pnlClass(value)}`}>{signed(value)}</span>
    </div>
  );
}
