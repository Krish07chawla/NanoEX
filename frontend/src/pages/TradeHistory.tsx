import { useState } from 'react';
import { Badge, Button, Card, ErrorState, Field, Input, Loading, PageHeader, Select } from '../components/ui';
import { Pager, Table } from '../components/ui/Table';
import { useApi } from '../hooks/useApi';
import { api, http } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import { toast } from '../store/toastStore';
import type { Trade } from '../types';
import { formatINR, formatNum, formatTime, pnlClass, signed } from '../utils/format';
import { SYMBOLS } from '../utils/symbols';

const PAGE_SIZE = 20;

export default function TradeHistory() {
  const version = useAccountStore((s) => s.version);
  const [filters, setFilters] = useState({
    symbol: '',
    side: '',
    source: '',
    exchange: '',
    start: '',
    end: '',
  });
  const [page, setPage] = useState(1);
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { data, error, loading, refetch } = useApi(
    () => api<Trade[]>({ url: '/trades', params: { ...params, page, size: PAGE_SIZE } }),
    [JSON.stringify(params), page, version],
  );
  const set = (k: keyof typeof filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setPage(1);
    setFilters({ ...filters, [k]: e.target.value });
  };

  const exportCsv = async () => {
    try {
      const r = await http.get('/trades/export.csv', { params, responseType: 'blob' });
      const url = URL.createObjectURL(r.data as Blob);
      const a = Object.assign(document.createElement('a'), { href: url, download: 'nanoex_trades.csv' });
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Export failed');
    }
  };

  return (
    <div>
      <PageHeader
        title="Trade History"
        subtitle="Every fill with its strategy and the reason for the signal."
        actions={
          <Button variant="ghost" onClick={exportCsv}>
            Export CSV
          </Button>
        }
      />
      <Card>
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-6">
          <Field label="Symbol">
            <Select value={filters.symbol} onChange={set('symbol')}>
              <option value="">All</option>
              {SYMBOLS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </Select>
          </Field>
          <Field label="Side">
            <Select value={filters.side} onChange={set('side')}>
              <option value="">All</option>
              <option>BUY</option>
              <option>SELL</option>
            </Select>
          </Field>
          <Field label="Source">
            <Select value={filters.source} onChange={set('source')}>
              <option value="">All</option>
              <option>MANUAL</option>
              <option>STRATEGY</option>
              <option>ARBITRAGE</option>
            </Select>
          </Field>
          <Field label="Exchange">
            <Select value={filters.exchange} onChange={set('exchange')}>
              <option value="">All</option>
              <option>NSE</option>
              <option>BSE</option>
            </Select>
          </Field>
          <Field label="From">
            <Input type="date" value={filters.start} onChange={set('start')} />
          </Field>
          <Field label="To">
            <Input type="date" value={filters.end} onChange={set('end')} />
          </Field>
        </div>
        {loading && !data ? (
          <Loading />
        ) : error ? (
          <ErrorState message={error.message} onRetry={refetch} />
        ) : (
          <>
            <Table<Trade>
              rows={data?.data ?? []}
              rowKey={(t) => t.id}
              empty="No trades match these filters."
              columns={[
                {
                  key: 't',
                  header: 'Time',
                  render: (t) => <span className="text-fg-dim">{formatTime(t.executed_at)}</span>,
                },
                {
                  key: 's',
                  header: 'Symbol',
                  render: (t) => <span className="font-semibold">{t.symbol}</span>,
                },
                { key: 'x', header: 'Exch', render: (t) => t.exchange },
                {
                  key: 'sd',
                  header: 'Side',
                  render: (t) => <Badge tone={t.side === 'BUY' ? 'buy' : 'sell'}>{t.side}</Badge>,
                },
                { key: 'q', header: 'Qty', align: 'right', render: (t) => t.quantity },
                { key: 'p', header: 'Price', align: 'right', render: (t) => formatNum(t.price) },
                { key: 'f', header: 'Charges', align: 'right', render: (t) => formatINR(t.fees) },
                {
                  key: 'r',
                  header: 'Realized',
                  align: 'right',
                  render: (t) => (
                    <span className={pnlClass(t.realized_pnl)}>
                      {t.realized_pnl ? signed(t.realized_pnl) : '—'}
                    </span>
                  ),
                },
                {
                  key: 'st',
                  header: 'Strategy',
                  render: (t) => t.strategy_name ?? <span className="text-fg-dim">Manual</span>,
                },
                {
                  key: 'why',
                  header: 'Signal reason',
                  render: (t) => (
                    <span
                      className="block max-w-[280px] truncate text-xs text-fg-muted"
                      title={t.signal_reason ?? ''}
                    >
                      {t.signal_reason ?? '—'}
                    </span>
                  ),
                },
              ]}
            />
            <Pager page={page} size={PAGE_SIZE} total={Number(data?.meta?.total ?? 0)} onPage={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}
