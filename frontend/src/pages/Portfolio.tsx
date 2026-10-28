import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, Field, Input, PageHeader, StatCard } from '../components/ui';
import { Pager, Table } from '../components/ui/Table';
import { PositionsTable } from './ProfitDashboard';
import { useApi } from '../hooks/useApi';
import { ApiError, api, get, post } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import { toast } from '../store/toastStore';
import type { Position, PortfolioSummary, Wallet, WalletTxn } from '../types';
import { formatINR, formatTime, pnlClass, signed } from '../utils/format';

const QUICK_AMOUNTS = [50000, 100000, 500000];

export default function Portfolio() {
  const { wallet, setWallet, version } = useAccountStore();
  const [page, setPage] = useState(1);
  const summary = useApi(() => get<PortfolioSummary>('/portfolio/summary'), [version], 5000);
  const positions = useApi(() => get<Position[]>('/portfolio/positions'), [version], 5000);
  const ledger = useApi(
    () => api<WalletTxn[]>({ url: '/wallet/transactions', params: { page, size: 10 } }),
    [page, version],
  );
  const [amount, setAmount] = useState(100000);
  const [busy, setBusy] = useState(false);

  const topUp = async (e?: FormEvent, value = amount) => {
    e?.preventDefault();
    setBusy(true);
    try {
      const w = await post<Wallet>('/wallet/topup', { amount: value });
      setWallet(w);
      toast.success('Wallet topped up', `Added ${formatINR(value)} of virtual money`);
      ledger.refetch();
      summary.refetch();
    } catch (err) {
      toast.error('Top-up failed', err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    if (!window.confirm('Reset your wallet to ₹5,00,000 and start a fresh P&L baseline?')) return;
    try {
      setWallet(await post<Wallet>('/wallet/reset'));
      toast.info('Wallet reset to ₹5,00,000');
      ledger.refetch();
      summary.refetch();
    } catch (err) {
      toast.error('Reset failed', err instanceof ApiError ? err.message : String(err));
    }
  };

  const close = async (p: Position) => {
    try {
      await post('/orders', {
        symbol: p.symbol,
        exchange: 'NSE',
        side: p.quantity > 0 ? 'SELL' : 'BUY',
        order_type: 'MARKET',
        quantity: Math.abs(p.quantity),
      });
      positions.refetch();
    } catch (err) {
      toast.error('Close failed', err instanceof ApiError ? err.message : String(err));
    }
  };

  const s = summary.data;
  return (
    <div>
      <PageHeader
        title="Portfolio & Wallet"
        subtitle="Your virtual cash, holdings and every rupee that moved in or out."
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Wallet balance"
          value={wallet ? formatINR(wallet.balance) : '—'}
          sub={wallet ? `Available ${formatINR(wallet.available)}` : undefined}
        />
        <StatCard label="Holdings value" value={s ? formatINR(s.market_value) : '—'} />
        <StatCard label="Equity" value={s ? formatINR(s.equity) : '—'} tone="amber" />
        <StatCard
          label="Total P&L"
          value={s ? signed(s.total_pnl) : '—'}
          tone={s && s.total_pnl >= 0 ? 'buy' : 'sell'}
          sub={s ? `vs ${formatINR(s.capital_added)} added` : undefined}
        />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card title="Open positions" className="xl:col-span-2">
          <PositionsTable
            rows={positions.data ?? []}
            action={(p) => (
              <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => close(p)}>
                Close
              </Button>
            )}
          />
        </Card>
        <Card title="Add virtual money">
          <form onSubmit={topUp} className="space-y-3">
            <Field
              label="Amount (₹)"
              hint="Up to ₹10,00,000 per top-up, 5 top-ups a day. Top-ups count as capital, not profit."
            >
              <Input
                type="number"
                min={1}
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </Field>
            <div className="flex gap-2">
              {QUICK_AMOUNTS.map((a) => (
                <button
                  type="button"
                  key={a}
                  onClick={() => setAmount(a)}
                  className="rounded border border-ink-600 px-2 py-1 text-xs text-fg-muted hover:text-fg"
                >
                  {formatINR(a).replace('.00', '')}
                </button>
              ))}
            </div>
            <Button type="submit" loading={busy} className="w-full">
              Top up wallet
            </Button>
            <Button type="button" variant="danger" className="w-full" onClick={reset}>
              Reset to ₹5,00,000
            </Button>
          </form>
        </Card>
      </div>
      <Card title="Wallet ledger" className="mt-4">
        <Table<WalletTxn>
          dense
          rows={ledger.data?.data ?? []}
          rowKey={(t) => t.id}
          columns={[
            {
              key: 't',
              header: 'Time',
              render: (t) => <span className="text-fg-dim">{formatTime(t.created_at)}</span>,
            },
            {
              key: 'y',
              header: 'Type',
              render: (t) => (
                <Badge
                  tone={
                    t.type === 'TOPUP' || t.type === 'INITIAL' ? 'amber' : t.type === 'FEE' ? 'muted' : 'info'
                  }
                >
                  {t.type}
                </Badge>
              ),
            },
            { key: 'n', header: 'Note', render: (t) => <span className="text-fg-muted">{t.note}</span> },
            {
              key: 'a',
              header: 'Amount',
              align: 'right',
              render: (t) => <span className={pnlClass(t.amount)}>{signed(t.amount)}</span>,
            },
            { key: 'b', header: 'Balance after', align: 'right', render: (t) => formatINR(t.balance_after) },
          ]}
        />
        {ledger.data?.meta && (
          <Pager page={page} size={10} total={Number(ledger.data.meta.total)} onPage={setPage} />
        )}
      </Card>
    </div>
  );
}
