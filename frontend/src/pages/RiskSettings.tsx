import { useEffect, useState, type FormEvent } from 'react';
import { Button, Card, ErrorState, Field, Input, Loading, PageHeader } from '../components/ui';
import { useApi } from '../hooks/useApi';
import { ApiError, get, post, put } from '../services/api';
import { toast } from '../store/toastStore';
import type { RiskSettings as Risk } from '../types';

const FIELDS: { key: keyof Risk; label: string; hint: string }[] = [
  { key: 'max_order_qty', label: 'Max quantity per order', hint: 'Shares' },
  { key: 'max_order_notional', label: 'Max value per order (₹)', hint: 'Price × quantity' },
  { key: 'max_position_value', label: 'Max position value (₹)', hint: 'Per symbol, long or short' },
  {
    key: 'daily_loss_limit',
    label: 'Daily loss limit (₹)',
    hint: 'After this, only exits are allowed today',
  },
  { key: 'daily_volume_cap', label: 'Daily traded value cap (₹)', hint: 'Total buy + sell value per day' },
  { key: 'max_open_orders', label: 'Max open orders', hint: 'Resting limit orders' },
];

export default function RiskSettings() {
  const { data, error, loading, refetch, setData } = useApi(() => get<Risk>('/risk'), []);
  const [form, setForm] = useState<Partial<Risk>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const body = Object.fromEntries(FIELDS.map((f) => [f.key, Number(form[f.key])]));
      setData(await put<Risk>('/risk', body));
      toast.success('Risk limits saved');
    } catch (err) {
      toast.error('Could not save', err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const kill = async (enabled: boolean) => {
    if (
      enabled &&
      !window.confirm(
        'Stop ALL trading now? This cancels open orders, stops bots and turns off auto-arbitrage.',
      )
    )
      return;
    try {
      const r = await post<{ cancelled_orders: number; stopped_bots: number }>('/risk/kill-switch', {
        enabled,
        cancel_open_orders: true,
      });
      toast[enabled ? 'warning' : 'success'](
        enabled ? 'Kill switch ON' : 'Kill switch OFF',
        enabled
          ? `${r.cancelled_orders} orders cancelled, ${r.stopped_bots} bots stopped`
          : 'Trading re-enabled',
      );
      refetch();
    } catch (err) {
      toast.error('Kill switch failed', err instanceof ApiError ? err.message : String(err));
    }
  };

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error?.message ?? 'Failed'} onRetry={refetch} />;

  return (
    <div>
      <PageHeader
        title="Risk Settings"
        subtitle="Every order (manual, bot or arbitrage leg) passes these checks before it reaches the matching engine."
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Limits" className="xl:col-span-2">
          <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
            {FIELDS.map((f) => (
              <Field key={f.key} label={f.label} hint={f.hint}>
                <Input
                  type="number"
                  min={1}
                  value={String(form[f.key] ?? '')}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  required
                />
              </Field>
            ))}
            <div className="md:col-span-2">
              <Button type="submit" loading={busy}>
                Save limits
              </Button>
            </div>
          </form>
        </Card>
        <Card title="Kill switch">
          <div className={`rounded-md p-4 text-center ${data.kill_switch ? 'bg-sell-soft' : 'bg-buy-soft'}`}>
            <div
              className={`font-mono text-2xl font-semibold ${data.kill_switch ? 'text-sell' : 'text-buy'}`}
            >
              {data.kill_switch ? 'TRADING STOPPED' : 'TRADING ACTIVE'}
            </div>
          </div>
          <p className="mt-3 text-sm text-fg-muted">
            The kill switch blocks every new order, cancels resting orders, stops your strategy bots and turns
            off auto-arbitrage.
          </p>
          {data.kill_switch ? (
            <Button variant="buy" className="mt-4 w-full" onClick={() => kill(false)}>
              Resume trading
            </Button>
          ) : (
            <Button variant="sell" className="mt-4 w-full" onClick={() => kill(true)}>
              STOP ALL TRADING
            </Button>
          )}
        </Card>
      </div>
    </div>
  );
}
