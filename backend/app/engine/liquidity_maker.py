"""Simulated market maker that keeps both sides of every book populated
around the current quote, so user orders have realistic depth to trade against."""

import random
from decimal import Decimal
from itertools import count

from app.core.constants import TICK_SIZE, OrderType, Side
from app.engine.order import BookOrder
from app.market.providers.base import Quote

LEVEL_NOTIONAL = 150_000  # rough rupee value resting per level
SIZE_MULTIPLIER_RANGE = (0.4, 2.5)
DEPTH_GROWTH = 0.25  # deeper levels hold a bit more size


class LiquidityMaker:
    def __init__(self, levels: int, seed: int | None = None):
        self.levels = levels
        self.rng = random.Random(seed)
        self._ids = count()

    def quotes_for(self, quote: Quote) -> list[BookOrder]:
        base = max(1, int(LEVEL_NOTIONAL / float(quote.last)))
        orders: list[BookOrder] = []
        for i in range(self.levels):
            offset = TICK_SIZE * i
            for side, price in ((Side.BUY, quote.bid - offset), (Side.SELL, quote.ask + offset)):
                if price <= 0:
                    continue
                size = int(base * self.rng.uniform(*SIZE_MULTIPLIER_RANGE) * (1 + DEPTH_GROWTH * i))
                orders.append(
                    BookOrder(f"mk-{next(self._ids)}", side, OrderType.LIMIT, max(1, size), price=Decimal(price))
                )
        return orders
