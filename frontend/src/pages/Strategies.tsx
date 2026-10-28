import { useEffect, useState, type FormEvent } from 'react';
import { Badge, Button, Card, ErrorState, Field, Input, Loading, PageHeader, Select } from '../components/ui';
import { Table } from '../components/ui/Table';
import { ParamFields, defaultsFor } from '../components/trading/ParamFields';
import { useApi } from '../hooks/useApi';
import { ApiError, del, get, post } from '../services/api';
import { toast } from '../store/toastStore';
import type { StrategyConfig, StrategyType } from '../types';
import { EXCHANGES, SYMBOLS } from '../utils/symbols';

export default function Strategies() {
  const types = useApi(() => get<StrategyType[]>('/strategies/types'), []);
  const configs = useApi(() => get<StrategyConfig[]>('/strategies'), [], 3000);
  const [form, setForm] = useState({
    name: '',
    strategy_type: 'ema_crossover',
    symbol: 'RELIANCE',
    exchange: 'NSE',
    quantity: 10,
    stop_loss_pct: '',
    take_profit_pct: '',
    trailing_stop_pct: '',
  });
  const [params, setParams] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const selected = types.data?.find((t) => t.key === form.strategy_type);

  useEffect(() => setParams(defaultsFor(selected)), [selected]);

  const optional = (v: string) => (v === '' ? null : Number(v));
  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await post('/strategies', {
        ...form,
        name: form.name || `${selected?.name} · ${form.symbol}`,
        params,
        stop_loss_pct: optional(form.stop_loss_pct),
        take_profit_pct: optional(form.take_profit_pct),
        trailing_stop_pct: optional(form.trailing_stop_pct),
      });
      toast.success('Strategy saved', 'Press Start to run it on live ticks.');
      configs.refetch();
    } catch (err) {
      toast.error('Could not save', err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const act = async (cfg: StrategyConfig, action: 'start' | 'stop' | 'delete') => {
    try {
      if (action === 'delete') await del(`/strategies/${cfg.id}`);
      else await post(`/strategies/${cfg.id}/${action}`);
      configs.refetch();
    } catch (err) {
      toast.error('Action failed', err instanceof ApiError ? err.message : String(err));
    }
  };

  if (types.loading) return <Loading />;
  if (types.error) return <ErrorState message={types.error.message} onRetry={types.refetch} />;

  return (
    <div>
      <PageHeader
        title="Strategies"
        subtitle="Strategy bots trade live simulated ticks through the same risk manager as manual orders (long-only)."
      />
      <div className="grid gap-4 xl:grid-cols-5">
        <Card title="My strategy bots" className="xl:col-span-3">
          <Table<StrategyConfig>
            rows={configs.data ?? []}
            rowKey={(c) => c.id}
            empty="No strategies yet. Create one on the right."
            columns={[
              {
                key: 'n',
                header: 'Name',
                render: (c) => (
                  <div>
                    <div className="font-semibold">{c.name}</div>
                    <div className="text-[11px] text-fg-dim">
                      {c.strategy_type} ·{' '}
                      {Object.entries(c.params)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(', ')}
                    </div>
                  </div>
                ),
              },
              { key: 's', header: 'Market', render: (c) => `${c.symbol} · ${c.exchange} ×${c.quantity}` },
              {
                key: 'x',
                header: 'Exits',
                render: (c) => (
                  <span className="text-xs text-fg-muted">
                    SL {c.stop_loss_pct ?? '-'}% · TP {c.take_profit_pct ?? '-'}% · Trail{' '}
                    {c.trailing_stop_pct ?? '-'}%
                  </span>
                ),
              },
              {
                key: 'st',
                header: 'Status',
                render: (c) => (
                  <div>
                    <Badge tone={c.is_active ? 'buy' : 'muted'}>{c.is_active ? 'RUNNING' : 'STOPPED'}</Badge>
                    {c.runtime?.last_signal && (
                      <div
                        className="mt-1 max-w-[220px] truncate text-[11px] text-fg-dim"
                        title={c.runtime.last_signal}
                      >
                        {c.runtime.last_signal}
                      </div>
                    )}
                  </div>
                ),
              },
              {
                key: 'a',
                header: '',
                align: 'right',
                render: (c) => (
                  <div className="flex justify-end gap-1">
                    {c.is_active ? (
                      <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => act(c, 'stop')}>
                        Stop
                      </Button>
                    ) : (
                      <Button variant="buy" className="px-2 py-1 text-xs" onClick={() => act(c, 'start')}>
                        Start
                      </Button>
                    )}
                    <Button variant="danger" className="px-2 py-1 text-xs" onClick={() => act(c, 'delete')}>
                      Delete
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        </Card>
        <Card title="New strategy bot" className="xl:col-span-2">
          <form onSubmit={create} className="space-y-3">
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
            <Field label="Name (optional)">
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder={`${selected?.name ?? ''} · ${form.symbol}`}
              />
            </Field>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Symbol">
                <Select value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
                  {SYMBOLS.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Exchange">
                <Select
                  value={form.exchange}
                  onChange={(e) => setForm({ ...form, exchange: e.target.value })}
                >
                  {EXCHANGES.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Quantity">
                <Input
                  type="number"
                  min={1}
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
                />
              </Field>
            </div>
            <ParamFields type={selected} values={params} onChange={setParams} />
            <div className="grid grid-cols-3 gap-3">
              <Field label="Stop loss %">
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.stop_loss_pct}
                  onChange={(e) => setForm({ ...form, stop_loss_pct: e.target.value })}
                />
              </Field>
              <Field label="Take profit %">
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.take_profit_pct}
                  onChange={(e) => setForm({ ...form, take_profit_pct: e.target.value })}
                />
              </Field>
              <Field label="Trailing %">
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.trailing_stop_pct}
                  onChange={(e) => setForm({ ...form, trailing_stop_pct: e.target.value })}
                />
              </Field>
            </div>
            <Button type="submit" loading={busy} className="w-full">
              Save strategy
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
