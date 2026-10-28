import type { Depth } from '../../types';
import { formatInt, formatNum } from '../../utils/format';

/** Top-N bids and asks with size bars. */
export function DepthTable({ depth, levels = 10 }: { depth: Depth | null; levels?: number }) {
  if (!depth) return <div className="py-8 text-center text-sm text-fg-dim">Waiting for depth…</div>;
  const bids = depth.bids.slice(0, levels);
  const asks = depth.asks.slice(0, levels);
  const max = Math.max(1, ...bids.map((b) => b.quantity), ...asks.map((a) => a.quantity));
  const spread = asks[0] && bids[0] ? asks[0].price - bids[0].price : null;

  const Row = ({
    price,
    qty,
    orders,
    side,
  }: {
    price: number;
    qty: number;
    orders: number;
    side: 'bid' | 'ask';
  }) => (
    <div className="relative grid grid-cols-3 px-2 py-[3px] font-mono text-xs">
      <div
        className={`absolute inset-y-0 ${side === 'bid' ? 'right-0 bg-buy-soft' : 'left-0 bg-sell-soft'}`}
        style={{ width: `${(qty / max) * 100}%` }}
      />
      <span className={`relative ${side === 'bid' ? 'text-buy' : 'text-sell'}`}>{formatNum(price)}</span>
      <span className="relative text-right">{formatInt(qty)}</span>
      <span className="relative text-right text-fg-dim">{orders}</span>
    </div>
  );

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <div className="mb-1 grid grid-cols-3 px-2 text-[10px] uppercase tracking-wider text-fg-dim">
          <span>Bid</span>
          <span className="text-right">Qty</span>
          <span className="text-right">Orders</span>
        </div>
        {bids.map((b) => (
          <Row key={`b${b.price}`} price={b.price} qty={b.quantity} orders={b.orders} side="bid" />
        ))}
      </div>
      <div>
        <div className="mb-1 grid grid-cols-3 px-2 text-[10px] uppercase tracking-wider text-fg-dim">
          <span>Ask</span>
          <span className="text-right">Qty</span>
          <span className="text-right">Orders</span>
        </div>
        {asks.map((a) => (
          <Row key={`a${a.price}`} price={a.price} qty={a.quantity} orders={a.orders} side="ask" />
        ))}
      </div>
      {spread != null && (
        <div className="text-xs text-fg-muted md:col-span-2">Bid-ask spread: ₹{formatNum(spread)}</div>
      )}
    </div>
  );
}
