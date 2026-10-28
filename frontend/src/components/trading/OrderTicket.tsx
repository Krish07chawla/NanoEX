import clsx from 'clsx';
import { useState, type FormEvent } from 'react';
import { Button, Card, Field, Input, Select } from '../ui';
import { post, ApiError } from '../../services/api';
import { toast } from '../../store/toastStore';
import { useMarketStore, quoteKey } from '../../store/marketStore';
import type { Exchange, Order, OrderType, Side } from '../../types';
import { EXCHANGES, SYMBOLS, TICK_SIZE } from '../../utils/symbols';
import { formatINR, formatNum } from '../../utils/format';

export function OrderTicket({
  symbol,
  exchange,
  onSymbol,
  onPlaced,
}: {
  symbol: string;
  exchange: Exchange;
  onSymbol?: (s: string, e: Exchange) => void;
  onPlaced?: (o: Order) => void;
}) {
  const [side, setSide] = useState<Side>('BUY');
  const [type, setType] = useState<OrderType>('MARKET');
  const [qty, setQty] = useState(10);
  const [price, setPrice] = useState('');
  const [busy, setBusy] = useState(false);
  const quote = useMarketStore((s) => s.quotes[quoteKey(symbol, exchange)]);
  const ref = type === 'LIMIT' ? Number(price) : side === 'BUY' ? quote?.ask : quote?.bid;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const order = await post<Order>('/orders', {
        symbol,
        exchange,
        side,
        order_type: type,
        quantity: qty,
        price: type === 'LIMIT' ? Number(price) : undefined,
      });
      if (order.status === 'NEW')
        toast.info('Limit order placed', `${side} ${qty} ${symbol} @ ${price} is resting in the book`);
      else if (order.status === 'CANCELLED')
        toast.warning('Partially filled', order.reject_reason ?? undefined);
      onPlaced?.(order);
    } catch (err) {
      toast.error('Order rejected', err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Order ticket">
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {(['BUY', 'SELL'] as Side[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSide(s)}
              className={clsx(
                'rounded-md py-2 text-sm font-semibold',
                side === s
                  ? s === 'BUY'
                    ? 'bg-buy text-ink-950'
                    : 'bg-sell text-white'
                  : 'bg-ink-800 text-fg-muted',
              )}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Symbol">
            <Select value={symbol} onChange={(e) => onSymbol?.(e.target.value, exchange)}>
              {SYMBOLS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </Select>
          </Field>
          <Field label="Exchange">
            <Select value={exchange} onChange={(e) => onSymbol?.(symbol, e.target.value as Exchange)}>
              {EXCHANGES.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </Select>
          </Field>
          <Field label="Type">
            <Select value={type} onChange={(e) => setType(e.target.value as OrderType)}>
              <option>MARKET</option>
              <option>LIMIT</option>
            </Select>
          </Field>
          <Field label="Quantity">
            <Input
              type="number"
              min={1}
              value={qty}
              onChange={(e) => setQty(Number(e.target.value))}
              required
            />
          </Field>
        </div>
        {type === 'LIMIT' && (
          <Field label="Limit price" hint={`Tick size ₹${TICK_SIZE}`}>
            <Input
              type="number"
              step={TICK_SIZE}
              min={TICK_SIZE}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={quote ? formatNum(quote.last) : ''}
              required
            />
          </Field>
        )}
        <div className="rounded-md bg-ink-900 px-3 py-2 text-xs text-fg-muted">
          <div className="flex justify-between">
            <span>Bid / Ask</span>
            <span className="font-mono">
              {quote ? `${formatNum(quote.bid)} / ${formatNum(quote.ask)}` : '—'}
            </span>
          </div>
          <div className="mt-1 flex justify-between">
            <span>Est. value</span>
            <span className="font-mono text-fg">{ref ? formatINR(ref * qty) : '—'}</span>
          </div>
        </div>
        <Button type="submit" variant={side === 'BUY' ? 'buy' : 'sell'} loading={busy} className="w-full">
          {side} {qty} {symbol} · {exchange}
        </Button>
      </form>
    </Card>
  );
}
