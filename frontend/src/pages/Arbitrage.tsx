import clsx from 'clsx';
import { useEffect, useState } from 'react';
import { Badge, Button, Card, Field, Input, PageHeader, StatCard, Toggle } from '../components/ui';
import { Pager, Table } from '../components/ui/Table';
import { SingleLine } from '../components/charts/Charts';
import { useApi } from '../hooks/useApi';
import { ApiError, api, get, post, put } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import { useMarketStore } from '../store/marketStore';
import { toast } from '../store/toastStore';
import type { ArbStats, ArbTrade, Opportunity, RiskSettings } from '../types';
import { formatINR, formatNum, formatTime, pnlClass, signed } from '../utils/format';
import { statusTone } from './Dashboard';

const NOTE =
  'Real NSE-BSE arbitrage is dominated by low-latency firms with co-located servers. Real spreads are usually a few paise and disappear in microseconds, so after brokerage, STT, GST and stamp duty a retail trader rarely captures them. This module shows why.';

export default function Arbitrage() {
  const spreads = useMarketStore((s) => s.spreads);
  const version = useAccountStore((s) => s.version);
  const [page, setPage] = useState(1);
  const opps = useApi(() => get<Opportunity[]>('/arbitrage/opportunities'), [], 1500);
  const stats = useApi(() => get<ArbStats>('/arbitrage/stats'), [version]);
  const trades = useApi(
    () => api<ArbTrade[]>({ url: '/arbitrage/trades', params: { page, size: 10 } }),
    [version, page],
  );
  const risk = useApi(() => get<RiskSettings>('/risk'), []);
  const [auto, setAuto] = useState({ enabled: false, min_profit: 50, quantity: 100 });
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (risk.data)
      setAuto({
        enabled: risk.data.arb_auto_enabled,
        min_profit: risk.data.arb_min_profit,
        quantity: risk.data.arb_quantity,
      });
  }, [risk.data]);

  const execute = async (o: Opportunity) => {
    setBusy(o.symbol);
    try {
      const t = await post<ArbTrade>('/arbitrage/execute', { symbol: o.symbol, quantity: o.quantity });
      const fn = t.status === 'COMPLETED' ? toast.success : toast.warning;
      fn(
        `Arbitrage ${t.status}`,
        `${t.symbol}: net ${formatINR(t.net_pnl)}${t.failure_reason ? ` · ${t.failure_reason}` : ''}`,
      );
      stats.refetch();
      trades.refetch();
    } catch (e) {
      toast.error('Not executed', e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const saveAuto = async (next: typeof auto) => {
    try {
      const r = await put<typeof auto>('/arbitrage/auto', next);
      setAuto(r);
      toast.info(
        r.enabled ? 'Auto mode ON' : 'Auto mode OFF',
        r.enabled
          ? `Executes when net profit > ${formatINR(r.min_profit)} for ${r.quantity} shares`
          : undefined,
      );
    } catch (e) {
      toast.error('Could not update auto mode', e instanceof ApiError ? e.message : String(e));
    }
  };

  const st = stats.data;
  return (
    <div>
      <PageHeader
        title="NSE-BSE Arbitrage"
        subtitle="Buy on the cheaper exchange, sell on the dearer one, at the same time (two-leg paper trade)."
      />
      <div
        className="mb-4 rounded-md border border-info/40 bg-info/10 px-4 py-3 text-sm text-info"
        role="note"
      >
        <strong className="font-semibold">Reality check: </strong>
        {NOTE}
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label="Cumulative net P&L"
          value={st ? signed(st.cumulative_net_pnl) : '—'}
          tone={st && st.cumulative_net_pnl >= 0 ? 'buy' : 'sell'}
        />
        <StatCard
          label="Executed"
          value={st ? `${st.executed}` : '—'}
          sub={st ? `${st.completed} completed of ${st.attempts} attempts` : undefined}
        />
        <StatCard
          label="Hit rate"
          value={st ? `${formatNum(st.hit_rate_pct, 1)}%` : '—'}
          sub="executions with net profit"
          tone="amber"
        />
        <StatCard
          label="Avg spread captured"
          value={st ? `₹${formatNum(st.avg_spread_captured, 3)}` : '—'}
          sub="per share, completed"
        />
        <StatCard
          label="Avg latency"
          value={st ? `${formatNum(st.avg_latency_ms, 0)} ms` : '—'}
          sub={st ? `charges paid ${formatINR(st.total_costs)}` : undefined}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-5">
        <Card title="Live spreads: same stock, both exchanges" className="xl:col-span-3">
          <Table
            dense
            rows={spreads}
            rowKey={(r) => r.symbol}
            empty="Waiting for the market feed…"
            columns={[
              {
                key: 's',
                header: 'Symbol',
                render: (r) => <span className="font-semibold">{r.symbol}</span>,
              },
              { key: 'n', header: 'NSE', align: 'right', render: (r) => formatNum(r.nse_last) },
              { key: 'b', header: 'BSE', align: 'right', render: (r) => formatNum(r.bse_last) },
              {
                key: 'sa',
                header: 'BSE − NSE',
                align: 'right',
                render: (r) => (
                  <span className={pnlClass(r.spread_abs)}>{signed(r.spread_abs, (v) => formatNum(v))}</span>
                ),
              },
              {
                key: 'sp',
                header: '%',
                align: 'right',
                render: (r) => <span className="text-fg-muted">{formatNum(r.spread_pct, 3)}</span>,
              },
              {
                key: 'net',
                header: 'Net @100 after costs',
                align: 'right',
                render: (r) =>
                  r.opportunity ? (
                    <span className={pnlClass(r.opportunity.est_net_profit)}>
                      {signed(r.opportunity.est_net_profit)}
                    </span>
                  ) : (
                    '—'
                  ),
              },
            ]}
          />
        </Card>
        <Card title="Mode" className="xl:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold">{auto.enabled ? 'Auto' : 'Manual'}</div>
              <div className="text-xs text-fg-muted">
                Auto executes the best opportunity above your threshold, within risk limits.
              </div>
            </div>
            <Toggle
              label="Auto mode"
              checked={auto.enabled}
              onChange={(v) => saveAuto({ ...auto, enabled: v })}
            />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Field label="Min net profit (₹)">
              <Input
                type="number"
                min={0}
                value={auto.min_profit}
                onChange={(e) => setAuto({ ...auto, min_profit: Number(e.target.value) })}
              />
            </Field>
            <Field label="Quantity per leg">
              <Input
                type="number"
                min={1}
                value={auto.quantity}
                onChange={(e) => setAuto({ ...auto, quantity: Number(e.target.value) })}
              />
            </Field>
          </div>
          <Button variant="ghost" className="mt-3 w-full" onClick={() => saveAuto(auto)}>
            Save threshold
          </Button>
          <p className="mt-3 text-[11px] text-fg-dim">
            Each leg gets simulated latency (20-150 ms) and a 5% chance of failing. A failed leg is closed at
            market straight away and the loss is shown below.
          </p>
        </Card>
      </div>

      <Card title={`Opportunities at ${auto.quantity} shares (refreshes every 1.5 s)`} className="mt-4">
        <Table<Opportunity>
          rows={opps.data ?? []}
          rowKey={(o) => o.symbol}
          empty="No data yet."
          columns={[
            { key: 's', header: 'Symbol', render: (o) => <span className="font-semibold">{o.symbol}</span> },
            {
              key: 'b',
              header: 'Buy on',
              render: (o) => (
                <Badge tone="buy">
                  {o.buy_exchange} @ {formatNum(o.buy_price)}
                </Badge>
              ),
            },
            {
              key: 'se',
              header: 'Sell on',
              render: (o) => (
                <Badge tone="sell">
                  {o.sell_exchange} @ {formatNum(o.sell_price)}
                </Badge>
              ),
            },
            {
              key: 'sp',
              header: 'Spread',
              align: 'right',
              render: (o) => `${formatNum(o.spread_abs, 2)} (${formatNum(o.spread_pct, 3)}%)`,
            },
            {
              key: 'c',
              header: 'Est. costs',
              align: 'right',
              render: (o) => (
                <span
                  title={`Brokerage ${o.cost_breakdown.brokerage} · STT ${o.cost_breakdown.stt} · Exch ${o.cost_breakdown.exchange_txn} · GST ${o.cost_breakdown.gst} · Stamp ${o.cost_breakdown.stamp} · Slippage ${o.cost_breakdown.slippage}`}
                >
                  {formatINR(o.est_costs)}
                </span>
              ),
            },
            {
              key: 'n',
              header: 'Est. net',
              align: 'right',
              render: (o) => (
                <span className={clsx('font-semibold', pnlClass(o.est_net_profit))}>
                  {signed(o.est_net_profit)}
                </span>
              ),
            },
            {
              key: 'l',
              header: 'Liquidity / confidence',
              render: (o) => (
                <span className="flex gap-1">
                  <Badge tone={o.liquidity_ok ? 'buy' : 'sell'}>
                    {o.liquidity_ok ? 'OK' : `max ${o.max_qty}`}
                  </Badge>
                  <Badge
                    tone={o.confidence === 'HIGH' ? 'buy' : o.confidence === 'MEDIUM' ? 'amber' : 'muted'}
                  >
                    {o.confidence}
                  </Badge>
                </span>
              ),
            },
            {
              key: 'x',
              header: '',
              align: 'right',
              render: (o) => (
                <Button
                  variant={o.actionable ? 'primary' : 'ghost'}
                  disabled={!o.actionable}
                  loading={busy === o.symbol}
                  onClick={() => execute(o)}
                  className="px-2.5 py-1 text-xs"
                >
                  Execute
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Cumulative arbitrage P&L">
          <SingleLine
            data={(st?.curve ?? []).map((p) => ({ x: formatTime(p.t), pnl: p.cumulative_pnl }))}
            dataKey="pnl"
            zeroLine
          />
        </Card>
        <Card title="Executed arbitrage trades" className="xl:col-span-2">
          <Table<ArbTrade>
            dense
            rows={trades.data?.data ?? []}
            rowKey={(t) => t.id}
            empty="No arbitrage trades yet."
            columns={[
              {
                key: 't',
                header: 'Time',
                render: (t) => <span className="text-fg-dim">{formatTime(t.created_at)}</span>,
              },
              {
                key: 's',
                header: 'Trade',
                render: (t) => `${t.symbol} ${t.buy_exchange}→${t.sell_exchange} ×${t.quantity}`,
              },
              { key: 'm', header: 'Mode', render: (t) => <Badge tone="info">{t.mode}</Badge> },
              {
                key: 'st',
                header: 'Result',
                render: (t) => (
                  <span title={t.failure_reason ?? ''}>
                    <Badge tone={statusTone(t.status)}>{t.status}</Badge>
                  </span>
                ),
              },
              {
                key: 'sp',
                header: 'Spread exp/got',
                align: 'right',
                render: (t) => `${formatNum(t.expected_spread)} / ${formatNum(t.captured_spread)}`,
              },
              { key: 'c', header: 'Costs', align: 'right', render: (t) => formatINR(t.total_costs) },
              {
                key: 'n',
                header: 'Net',
                align: 'right',
                render: (t) => <span className={pnlClass(t.net_pnl)}>{signed(t.net_pnl)}</span>,
              },
              { key: 'l', header: 'Latency', align: 'right', render: (t) => `${t.latency_ms} ms` },
            ]}
          />
          {trades.data?.meta && (
            <Pager page={page} size={10} total={Number(trades.data.meta.total)} onPage={setPage} />
          )}
          {(trades.data?.data ?? []).some((t) => t.failure_reason) && (
            <p className="mt-2 text-[11px] text-fg-dim">Hover a result to see what happened to each leg.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
