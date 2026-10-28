import { useEffect, useState } from 'react';
import { Badge, Button, Card, PageHeader, Select } from '../components/ui';
import { Table } from '../components/ui/Table';
import { DepthTable } from '../components/trading/DepthTable';
import { OrderTicket } from '../components/trading/OrderTicket';
import { selectDepthBook } from '../hooks/useStreams';
import { useApi } from '../hooks/useApi';
import { ApiError, del, get } from '../services/api';
import { useAccountStore } from '../store/accountStore';
import { useMarketStore } from '../store/marketStore';
import { toast } from '../store/toastStore';
import type { Depth, Exchange, Order } from '../types';
import { EXCHANGES, SYMBOLS } from '../utils/symbols';
import { formatNum, formatTime } from '../utils/format';

export default function OrderBook() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [exchange, setExchange] = useState<Exchange>('NSE');
  const liveDepth = useMarketStore((s) => s.depth);
  const version = useAccountStore((s) => s.version);
  const initial = useApi(() => get<Depth>(`/market/${symbol}/${exchange}/depth`), [symbol, exchange]);
  const open = useApi(
    async () => [
      ...(await get<Order[]>('/orders', { status: 'NEW' })),
      ...(await get<Order[]>('/orders', { status: 'PARTIAL' })),
    ],
    [version],
  );

  useEffect(() => {
    selectDepthBook(symbol, exchange);
  }, [symbol, exchange]);

  const depth =
    liveDepth && liveDepth.symbol === symbol && liveDepth.exchange === exchange ? liveDepth : initial.data;

  const cancel = async (o: Order) => {
    try {
      await del(`/orders/${o.id}`);
      toast.info('Order cancelled', `${o.side} ${o.quantity} ${o.symbol}`);
      open.refetch();
    } catch (e) {
      toast.error('Cancel failed', e instanceof ApiError ? e.message : String(e));
    }
  };

  return (
    <div>
      <PageHeader
        title="Order Book"
        subtitle="Top 10 levels with price-time priority. Your resting limit orders sit in the same book as simulated liquidity."
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card
            title="Market depth"
            actions={
              <div className="flex gap-2">
                <Select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="py-1 text-xs">
                  {SYMBOLS.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </Select>
                <Select
                  value={exchange}
                  onChange={(e) => setExchange(e.target.value as Exchange)}
                  className="py-1 text-xs"
                >
                  {EXCHANGES.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </Select>
              </div>
            }
          >
            <DepthTable depth={depth ?? null} />
          </Card>
          <Card title="My open orders">
            <Table<Order>
              rows={open.data ?? []}
              rowKey={(o) => o.id}
              empty="No resting orders. Place a LIMIT order away from the market to see it here."
              columns={[
                {
                  key: 't',
                  header: 'Time',
                  render: (o) => <span className="text-fg-dim">{formatTime(o.created_at)}</span>,
                },
                {
                  key: 's',
                  header: 'Order',
                  render: (o) => (
                    <span>
                      <Badge tone={o.side === 'BUY' ? 'buy' : 'sell'}>{o.side}</Badge> {o.symbol} ·{' '}
                      {o.exchange}
                    </span>
                  ),
                },
                { key: 'p', header: 'Limit', align: 'right', render: (o) => formatNum(o.price) },
                {
                  key: 'q',
                  header: 'Filled',
                  align: 'right',
                  render: (o) => `${o.filled_qty}/${o.quantity}`,
                },
                {
                  key: 'c',
                  header: '',
                  align: 'right',
                  render: (o) => (
                    <Button variant="danger" className="px-2 py-1 text-xs" onClick={() => cancel(o)}>
                      Cancel
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </div>
        <OrderTicket
          symbol={symbol}
          exchange={exchange}
          onSymbol={(s, e) => (setSymbol(s), setExchange(e))}
          onPlaced={() => open.refetch()}
        />
      </div>
    </div>
  );
}
