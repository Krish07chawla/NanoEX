import { useEffect, useState, type FormEvent } from 'react';
import { Button, Card, Field, Input, Loading, PageHeader, Select, StatCard } from '../components/ui';
import { Table } from '../components/ui/Table';
import { TwoLine } from '../components/charts/Charts';
import { ParamFields, defaultsFor } from '../components/trading/ParamFields';
import { useApi } from '../hooks/useApi';
import { ApiError, get, post } from '../services/api';
import { toast } from '../store/toastStore';
import type { BacktestMetrics, BacktestResult, StrategyType } from '../types';
import { formatINR, formatNum, formatPct, formatTime, pnlClass, signed } from '../utils/format';
import { SYMBOLS } from '../utils/symbols';

interface SavedRun {
  id: string;
  strategy_type: string;
  symbol: string;
  bars: number;
  seed: number | null;
  metrics: BacktestMetrics;
  created_at: string;
}

export default function Backtester() {
  const types = useApi(() => get<StrategyType[]>('/strategies/types'), []);
  const saved = useApi(() => get<SavedRun[]>('/backtests', { size: 10 }), []);
  const [form, setForm] = useState({
    strategy_type: 'ema_crossover',
    symbol: 'RELIANCE',
    data_source: 'synthetic',
    bars: 500,
    seed: 42,
    initial_capital: 500000,
    slippage_bps: 2,
    stop_loss_pct: '',
    take_profit_pct: '',
    trailing_stop_pct: '',
  });
  const [params, setParams] = useState<Record<string, number>>({});
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const selected = types.data?.find((t) => t.key === form.strategy_type);
  useEffect(() => setParams(defaultsFor(selected)), [selected]);

  const opt = (v: string) => (v === '' ? null : Number(v));
  const run = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await post<BacktestResult>('/backtests', {
        ...form,
        params,
        stop_loss_pct: opt(form.stop_loss_pct),
        take_profit_pct: opt(form.take_profit_pct),
        trailing_stop_pct: opt(form.trailing_stop_pct),
      });
      setResult(r);
      saved.refetch();
    } catch (err) {
      toast.error('Backtest failed', err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const open = async (id: string) => setResult(await get<BacktestResult>(`/backtests/${id}`));
  const m = result?.metrics;

  return (
    <div>
      <PageHeader
        title="Backtester"
        subtitle="Same seed = same result. Every trade pays brokerage, STT, exchange charges, GST, stamp duty and slippage."
      />
      <div className="grid gap-4 xl:grid-cols-4">
        <Card title="Setup">
          {types.loading ? (
            <Loading />
          ) : (
            <form onSubmit={run} className="space-y-3">
              <Field label="Strategy" hint={selected?.description}>
                <Select
                  value={form.strategy_type}
                  onChange={(e) => setForm({ ...form, strategy_type: e.target.value })}
                >
                  {types.data?.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Symbol">
                  <Select value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
                    {SYMBOLS.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </Select>
                </Field>
                <Field label="Data">
                  <Select
                    value={form.data_source}
                    onChange={(e) => setForm({ ...form, data_source: e.target.value })}
                  >
                    <option value="synthetic">Synthetic (seeded)</option>
                    <option value="yfinance">Historical (yfinance)</option>
                  </Select>
                </Field>
                <Field label="Bars (days)">
                  <Input
                    type="number"
                    min={50}
                    max={5000}
                    value={form.bars}
                    onChange={(e) => setForm({ ...form, bars: Number(e.target.value) })}
                  />
                </Field>
                <Field label="Seed">
                  <Input
                    type="number"
                    value={form.seed}
                    onChange={(e) => setForm({ ...form, seed: Number(e.target.value) })}
                  />
                </Field>
                <Field label="Capital (₹)">
                  <Input
                    type="number"
                    min={1000}
                    value={form.initial_capital}
                    onChange={(e) => setForm({ ...form, initial_capital: Number(e.target.value) })}
                  />
                </Field>
                <Field label="Slippage (bps)">
                  <Input
                    type="number"
                    min={0}
                    value={form.slippage_bps}
                    onChange={(e) => setForm({ ...form, slippage_bps: Number(e.target.value) })}
                  />
                </Field>
              </div>
              <ParamFields type={selected} values={params} onChange={setParams} />
              <div className="grid grid-cols-3 gap-2">
                <Field label="SL %">
                  <Input
                    type="number"
                    step="0.1"
                    value={form.stop_loss_pct}
                    onChange={(e) => setForm({ ...form, stop_loss_pct: e.target.value })}
                  />
                </Field>
                <Field label="TP %">
                  <Input
                    type="number"
                    step="0.1"
                    value={form.take_profit_pct}
                    onChange={(e) => setForm({ ...form, take_profit_pct: e.target.value })}
                  />
                </Field>
                <Field label="Trail %">
                  <Input
                    type="number"
                    step="0.1"
                    value={form.trailing_stop_pct}
                    onChange={(e) => setForm({ ...form, trailing_stop_pct: e.target.value })}
                  />
                </Field>
              </div>
              <Button type="submit" loading={busy} className="w-full">
                Run backtest
              </Button>
            </form>
          )}
        </Card>
        <div className="space-y-4 xl:col-span-3">
          {m ? (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <StatCard
                  label="Total return"
                  value={formatPct(m.total_return_pct)}
                  tone={m.total_return_pct >= 0 ? 'buy' : 'sell'}
                  sub={`Buy & hold ${formatPct(m.buy_hold_return_pct)}`}
                />
                <StatCard
                  label="Final equity"
                  value={formatINR(m.final_equity)}
                  sub={`from ${formatINR(m.initial_capital)}`}
                />
                <StatCard label="Max drawdown" value={formatPct(m.max_drawdown_pct)} tone="sell" />
                <StatCard
                  label="Win rate"
                  value={`${formatNum(m.win_rate_pct, 1)}%`}
                  sub={`${m.num_trades} trades`}
                />
                <StatCard label="Sharpe" value={formatNum(m.sharpe)} />
                <StatCard label="Sortino" value={formatNum(m.sortino)} />
                <StatCard
                  label="Profit factor"
                  value={m.profit_factor == null ? '∞ (no losses)' : formatNum(m.profit_factor)}
                />
                <StatCard
                  label="Costs paid"
                  value={formatINR(m.total_costs)}
                  sub={`in market ${formatNum(m.exposure_pct, 0)}% of the time`}
                />
              </div>
              <Card title="Equity curve vs buy & hold">
                <TwoLine
                  data={result!.equity_curve.map((p) => ({ x: p.i, equity: p.equity, buy_hold: p.buy_hold }))}
                  a="equity"
                  b="buy_hold"
                  labels={['Strategy', 'Buy & hold']}
                  height={300}
                />
              </Card>
              <Card title="Trades">
                <Table
                  dense
                  rows={result!.trades}
                  rowKey={(t) => `${t.entry_index}-${t.exit_index}`}
                  empty="The strategy never traded. Try other parameters."
                  columns={[
                    {
                      key: 'e',
                      header: 'Entry (bar)',
                      render: (t) => `#${t.entry_index} @ ${formatNum(t.entry_price)}`,
                    },
                    {
                      key: 'x',
                      header: 'Exit (bar)',
                      render: (t) => `#${t.exit_index} @ ${formatNum(t.exit_price)}`,
                    },
                    { key: 'q', header: 'Qty', align: 'right', render: (t) => t.quantity },
                    { key: 'c', header: 'Costs', align: 'right', render: (t) => formatINR(t.costs) },
                    {
                      key: 'p',
                      header: 'P&L',
                      align: 'right',
                      render: (t) => <span className={pnlClass(t.pnl)}>{signed(t.pnl)}</span>,
                    },
                    {
                      key: 'r',
                      header: 'Why',
                      render: (t) => (
                        <span className="text-xs text-fg-muted" title={t.entry_reason}>
                          {t.exit_reason}
                        </span>
                      ),
                    },
                  ]}
                />
              </Card>
            </>
          ) : (
            <Card>
              <div className="py-16 text-center text-fg-dim">
                Configure a strategy and press <span className="text-amber">Run backtest</span>.
              </div>
            </Card>
          )}
          <Card title="Saved runs">
            <Table<SavedRun>
              dense
              rows={saved.data ?? []}
              rowKey={(r) => r.id}
              empty="No saved backtests yet."
              columns={[
                {
                  key: 't',
                  header: 'When',
                  render: (r) => <span className="text-fg-dim">{formatTime(r.created_at)}</span>,
                },
                { key: 's', header: 'Strategy', render: (r) => `${r.strategy_type} · ${r.symbol}` },
                { key: 'b', header: 'Bars / seed', render: (r) => `${r.bars} / ${r.seed ?? '-'}` },
                {
                  key: 'r',
                  header: 'Return',
                  align: 'right',
                  render: (r) => (
                    <span className={pnlClass(r.metrics.total_return_pct)}>
                      {formatPct(r.metrics.total_return_pct)}
                    </span>
                  ),
                },
                { key: 'sh', header: 'Sharpe', align: 'right', render: (r) => formatNum(r.metrics.sharpe) },
                {
                  key: 'o',
                  header: '',
                  align: 'right',
                  render: (r) => (
                    <button className="text-xs text-amber" onClick={() => open(r.id)}>
                      Open
                    </button>
                  ),
                },
              ]}
            />
          </Card>
        </div>
      </div>
    </div>
  );
}
