"""Limit order book with price-time priority.

Bids and asks are kept as {price: deque[BookOrder]} plus a sorted price list,
so the best level is O(1) and inserts are O(log n). Orders at the same price
fill in arrival order (FIFO). Trades execute at the resting order's price.
Not thread-safe by itself: MatchingEngine serialises access with a lock per book.
"""

import bisect
from collections import deque
from decimal import Decimal
from itertools import count

from app.core.constants import OrderType, Side
from app.engine.order import BookOrder, Fill, MatchResult


class OrderBook:
    def __init__(self, symbol: str, exchange: str):
        self.symbol = symbol
        self.exchange = exchange
        self._levels: dict[Side, dict[Decimal, deque[BookOrder]]] = {Side.BUY: {}, Side.SELL: {}}
        self._prices: dict[Side, list[Decimal]] = {Side.BUY: [], Side.SELL: []}  # ascending
        self._index: dict[str, BookOrder] = {}
        self._seq = count()

    # ---------- queries ----------
    def best_bid(self) -> Decimal | None:
        prices = self._prices[Side.BUY]
        return prices[-1] if prices else None

    def best_ask(self) -> Decimal | None:
        prices = self._prices[Side.SELL]
        return prices[0] if prices else None

    def get(self, order_id: str) -> BookOrder | None:
        return self._index.get(order_id)

    def __len__(self) -> int:
        return len(self._index)

    def depth(self, levels: int = 10) -> dict:
        """Aggregated top-N levels per side: [{price, quantity, orders}]."""

        def side_levels(side: Side) -> list[dict]:
            prices = self._prices[side]
            ordered = reversed(prices) if side is Side.BUY else iter(prices)
            out = []
            for price in ordered:
                queue = self._levels[side][price]
                out.append({"price": float(price), "quantity": sum(o.remaining for o in queue), "orders": len(queue)})
                if len(out) >= levels:
                    break
            return out

        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "bids": side_levels(Side.BUY),
            "asks": side_levels(Side.SELL),
        }

    def sweep_vwap(self, side: Side, quantity: int) -> tuple[Decimal | None, int]:
        """Average price to BUY or SELL `quantity` now by walking the opposite side.
        Returns (vwap, fillable_qty). Used by the arbitrage detector for liquidity checks."""
        book_side = side.opposite
        prices = self._prices[book_side]
        ordered = iter(prices) if side is Side.BUY else reversed(prices)
        filled, notional = 0, Decimal("0")
        for price in ordered:
            for order in self._levels[book_side][price]:
                take = min(order.remaining, quantity - filled)
                filled += take
                notional += price * take
                if filled >= quantity:
                    return notional / filled, filled
        return (notional / filled if filled else None), filled

    # ---------- commands ----------
    def submit(self, order: BookOrder) -> MatchResult:
        """Match an incoming order, then rest any limit remainder. Market remainders are dropped (IOC)."""
        if order.order_id in self._index:
            raise ValueError(f"duplicate order id {order.order_id}")
        order.seq = next(self._seq)
        result = MatchResult()
        self._match(order, result)
        result.remaining = order.remaining
        if order.remaining > 0 and order.order_type is OrderType.LIMIT:
            self._rest(order)
            result.resting = True
        return result

    def cancel(self, order_id: str) -> BookOrder | None:
        order = self._index.pop(order_id, None)
        if order is None:
            return None
        queue = self._levels[order.side][order.price]
        queue.remove(order)
        if not queue:
            self._drop_level(order.side, order.price)
        return order

    def remove_makers(self) -> None:
        """Pull every simulated liquidity-maker order (before re-quoting)."""
        for order_id in [oid for oid, o in self._index.items() if o.is_maker_bot]:
            self.cancel(order_id)

    # ---------- internals ----------
    def _crosses(self, order: BookOrder, best: Decimal) -> bool:
        if order.order_type is OrderType.MARKET:
            return True
        assert order.price is not None
        return best <= order.price if order.side is Side.BUY else best >= order.price

    def _match(self, order: BookOrder, result: MatchResult) -> None:
        opposite = order.side.opposite
        while order.remaining > 0:
            best = self.best_ask() if order.side is Side.BUY else self.best_bid()
            if best is None or not self._crosses(order, best):
                return
            queue = self._levels[opposite][best]
            resting = queue[0]
            # Self-trade prevention: cancel the user's own resting order instead of trading with it.
            if order.user_id is not None and resting.user_id == order.user_id:
                self.cancel(resting.order_id)
                result.cancelled_ids.append(resting.order_id)
                continue
            qty = min(order.remaining, resting.remaining)
            order.remaining -= qty
            resting.remaining -= qty
            result.fills.append(
                Fill(
                    self.symbol,
                    self.exchange,
                    best,
                    qty,
                    order.order_id,
                    order.user_id,
                    order.side,
                    resting.order_id,
                    resting.user_id,
                )
            )
            if resting.remaining == 0:
                queue.popleft()
                del self._index[resting.order_id]
                if not queue:
                    self._drop_level(opposite, best)

    def _rest(self, order: BookOrder) -> None:
        assert order.price is not None
        levels = self._levels[order.side]
        if order.price not in levels:
            levels[order.price] = deque()
            bisect.insort(self._prices[order.side], order.price)
        levels[order.price].append(order)
        self._index[order.order_id] = order

    def _drop_level(self, side: Side, price: Decimal) -> None:
        del self._levels[side][price]
        prices = self._prices[side]
        prices.pop(bisect.bisect_left(prices, price))
