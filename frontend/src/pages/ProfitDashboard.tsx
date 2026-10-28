import { Card, ErrorState, Loading, PageHeader, StatCard } from '../components/ui';
import { Table } from '../components/ui/Table';
import { PnlBars, SingleLine } from '../components/charts/Charts';
import { useApi } from '../hooks/useApi';
import { get } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import type { Position, ProfitDashboard as Data } from '../types';
import { formatINR, formatNum, formatPct, formatTime, pnlClass, signed } from '../utils/format';

const SOURCE_LABEL: Record<string, string> = {
  MANUAL: 'Manual',
  STRATEGY: 'Strategy bots',
  ARBITRAGE: 'Arbitrage',
};

/** Profit + portfolio only: the page to check "am I making money, and from what?" */
export default function ProfitDashboard() {
  const version = useAccountStore((s) => s.version);
  const { data, error, loading, refetch } = useApi(() => get<Data>('/dashboard/profit'), [version], 5000);
  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorState message={error.message} onRetry={refetch} />;
  if (!data) return null;
  const s = data.summary;
  const curve = data.equity_curve.map((p) => ({ x: formatTime(p.t), equity: p.equity }));

  return (
    <div>
      <PageHeader
        title="Profit & Portfolio"
        subtitle="Profit is measured against the money you added (₹5,00,000 + any top-ups), so top-ups never count as profit."
      />
      <div className="rounded-lg border border-ink-700 bg-ink-850 p-5">
        <div className="text-xs uppercase tracking-wider text-fg-dim">Total profit / loss</div>
        <div className={`mt-1 font-mono text-4xl font-semibold ${pnlClass(s.total_pnl)}`}>
          {signed(s.total_pnl)}
        </div>
        <div className="mt-1 text-sm text-fg-muted">
          {formatPct(s.total_return_pct)} on {formatINR(s.capital_added)} capital · equity{' '}
          {formatINR(s.equity)}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Realized P&L (net)"
          value={signed(s.net_realized_pnl)}
          tone={s.net_realized_pnl >= 0 ? 'buy' : 'sell'}
          sub={`after ${formatINR(s.total_fees)} charges`}
        />
        <StatCard
          label="Unrealized P&L"
          value={signed(s.unrealized_pnl)}
          tone={s.unrealized_pnl >= 0 ? 'buy' : 'sell'}
          sub={`${s.open_positions} open positions`}
        />
        <StatCard
          label="Win rate"
          value={`${formatNum(data.win_rate_pct, 1)}%`}
          sub={`${data.closed_trades} closing trades`}
          tone="amber"
        />
        <StatCard
          label="Best / worst trade"
          value={
            <span className="text-base">
              {signed(data.best_trade)} / {signed(data.worst_trade)}
            </span>
          }
        />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Equity curve" className="xl:col-span-2">
          <SingleLine data={curve} dataKey="equity" />
        </Card>
        <Card title="P&L by source">
          <PnlBars
            data={data.by_source.map((r) => ({ ...r, label: SOURCE_LABEL[r.source] ?? r.source }))}
            labelKey="label"
          />
          <div className="mt-2 text-xs text-fg-muted">
            Arbitrage net (after all charges):{' '}
            <span className={pnlClass(data.arbitrage_net_pnl)}>{signed(data.arbitrage_net_pnl)}</span>
          </div>
        </Card>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Daily P&L">
          <PnlBars data={data.daily.map((d) => ({ ...d, label: d.date.slice(5) }))} labelKey="label" />
        </Card>
        <Card title="By strategy">
          <Table
            dense
            rows={data.by_strategy}
            rowKey={(r) => r.name}
            empty="No trades yet."
            columns={[
              { key: 'n', header: 'Strategy', render: (r) => r.name },
              {
                key: 'p',
                header: 'Net P&L',
                align: 'right',
                render: (r) => <span className={pnlClass(r.pnl)}>{signed(r.pnl)}</span>,
              },
            ]}
          />
        </Card>
        <Card title="By symbol">
          <Table
            dense
            rows={data.by_symbol}
            rowKey={(r) => r.symbol}
            empty="No trades yet."
            columns={[
              { key: 's', header: 'Symbol', render: (r) => r.symbol },
              {
                key: 'p',
                header: 'Net P&L',
                align: 'right',
                render: (r) => <span className={pnlClass(r.pnl)}>{signed(r.pnl)}</span>,
              },
            ]}
          />
        </Card>
      </div>
      <Card title="Holdings" className="mt-4">
        <PositionsTable rows={data.positions} />
      </Card>
    </div>
  );
}

export function PositionsTable({
  rows,
  action,
}: {
  rows: Position[];
  action?: (p: Position) => React.ReactNode;
}) {
  return (
    <Table<Position>
      rows={rows}
      rowKey={(p) => p.symbol}
      empty="No open positions."
      columns={[
        { key: 's', header: 'Symbol', render: (p) => <span className="font-semibold">{p.symbol}</span> },
        {
          key: 'side',
          header: 'Side',
          render: (p) => <span className={p.side === 'LONG' ? 'text-buy' : 'text-sell'}>{p.side}</span>,
        },
        { key: 'q', header: 'Qty', align: 'right', render: (p) => p.quantity },
        { key: 'a', header: 'Avg price', align: 'right', render: (p) => formatNum(p.avg_price) },
        { key: 'm', header: 'Mark', align: 'right', render: (p) => formatNum(p.mark_price) },
        { key: 'v', header: 'Value', align: 'right', render: (p) => formatINR(p.market_value) },
        {
          key: 'u',
          header: 'Unrealized',
          align: 'right',
          render: (p) => (
            <span className={pnlClass(p.unrealized_pnl)}>
              {signed(p.unrealized_pnl)} <span className="text-[11px]">({formatPct(p.unrealized_pct)})</span>
            </span>
          ),
        },
        ...(action ? [{ key: 'act', header: '', align: 'right' as const, render: action }] : []),
      ]}
    />
  );
}
