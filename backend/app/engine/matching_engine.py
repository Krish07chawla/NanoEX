"""MatchingEngine: owns one OrderBook per (symbol, exchange), serialised by an
asyncio.Lock per book so different symbols never block each other."""

import asyncio
from collections.abc import Awaitable, Callable

from app.engine.liquidity_maker import LiquidityMaker
from app.engine.order import BookOrder, Fill, MatchResult
from app.engine.order_book import OrderBook
from app.market.providers.base import Quote

FillHandler = Callable[[list[Fill]], Awaitable[None]]


class MatchingEngine:
    def __init__(self, depth_levels: int = 10, seed: int | None = None):
        self._books: dict[tuple[str, str], OrderBook] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self.maker = LiquidityMaker(depth_levels, seed)
        self.fill_handler: FillHandler | None = None  # settles fills that happen on re-quote

    def book(self, symbol: str, exchange: str) -> OrderBook:
        key = (symbol, exchange)
        if key not in self._books:
            self._books[key] = OrderBook(symbol, exchange)
            self._locks[key] = asyncio.Lock()
        return self._books[key]

    def _lock(self, symbol: str, exchange: str) -> asyncio.Lock:
        self.book(symbol, exchange)
        return self._locks[(symbol, exchange)]

    async def submit(self, symbol: str, exchange: str, order: BookOrder) -> MatchResult:
        async with self._lock(symbol, exchange):
            return self.book(symbol, exchange).submit(order)

    async def cancel(self, symbol: str, exchange: str, order_id: str) -> BookOrder | None:
        async with self._lock(symbol, exchange):
            return self.book(symbol, exchange).cancel(order_id)

    async def restore(self, symbol: str, exchange: str, order: BookOrder) -> None:
        """Put a persisted open limit order back in the book after a restart."""
        async with self._lock(symbol, exchange):
            book = self.book(symbol, exchange)
            if book.get(order.order_id) is None:
                book.submit(order)

    async def on_quotes(self, quotes: list[Quote]) -> None:
        """Tick hook: re-quote maker liquidity; any fills against resting user orders are settled."""
        user_fills: list[Fill] = []
        for quote in quotes:
            async with self._lock(quote.symbol, quote.exchange):
                book = self.book(quote.symbol, quote.exchange)
                book.remove_makers()
                for maker_order in self.maker.quotes_for(quote):
                    result = book.submit(maker_order)
                    user_fills.extend(f for f in result.fills if f.maker_user_id is not None)
        if user_fills and self.fill_handler:
            await self.fill_handler(user_fills)

    def depth(self, symbol: str, exchange: str, levels: int = 10) -> dict:
        return self.book(symbol, exchange).depth(levels)
