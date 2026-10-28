"""MarketDataService: pulls quotes from the provider on a timer, keeps the latest
quote + short history per (symbol, exchange), notifies tick hooks (engine,
arbitrage scanner) and publishes a batched `tick` event for WebSocket clients."""

import asyncio
import contextlib
import time
from collections import deque
from collections.abc import Awaitable, Callable

from app.core.event_bus import EventBus, Topics
from app.core.exceptions import MarketUnavailable, NotFound
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.market.providers.base import MarketDataProvider, Quote

TickHook = Callable[[list[Quote]], Awaitable[None]]
log = get_logger(__name__)


class MarketDataService:
    def __init__(self, provider: MarketDataProvider, bus: EventBus, interval_ms: int, history_size: int):
        self.provider = provider
        self.bus = bus
        self.interval = interval_ms / 1000
        self._latest: dict[tuple[str, str], Quote] = {}
        self._history: dict[tuple[str, str], deque] = {}
        self._history_size = history_size
        self._hooks: list[TickHook] = []
        self._task: asyncio.Task | None = None
        self.running = False
        self.last_tick_at = 0.0

    def add_hook(self, hook: TickHook) -> None:
        """Register an observer called with every batch of quotes."""
        self._hooks.append(hook)

    async def start(self) -> None:
        await self.step()  # prime prices before serving requests
        self.running = True
        self._task = asyncio.create_task(self._run(), name="market-stream")

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while self.running:
            started = time.perf_counter()
            try:
                await self.step()
            except Exception:  # noqa: BLE001 - keep the feed alive
                log.exception("market_step_failed")
            await asyncio.sleep(max(0.0, self.interval - (time.perf_counter() - started)))

    async def step(self) -> list[Quote]:
        quotes = await self.provider.next_quotes()
        self.ingest(quotes)
        for hook in self._hooks:
            await hook(quotes)
        self.bus.publish(Topics.TICK, [q.to_dict() for q in quotes])
        return quotes

    def ingest(self, quotes: list[Quote]) -> None:
        for q in quotes:
            key = (q.symbol, q.exchange)
            self._latest[key] = q
            hist = self._history.setdefault(key, deque(maxlen=self._history_size))
            hist.append((q.timestamp, float(q.last)))
        metrics.ticks_total += len(quotes)
        self.last_tick_at = time.time()

    # --- queries ---
    def symbols(self) -> list[str]:
        return self.provider.symbols()

    def quote(self, symbol: str, exchange: str) -> Quote:
        q = self._latest.get((symbol, exchange))
        if q is None:
            if symbol not in self.symbols():
                raise NotFound(f"Unknown symbol {symbol}")
            raise MarketUnavailable(f"No quote yet for {symbol} on {exchange}")
        return q

    def quotes(self) -> list[Quote]:
        return list(self._latest.values())

    def history(self, symbol: str, exchange: str, limit: int | None = None) -> list[dict]:
        hist = list(self._history.get((symbol, exchange), ()))
        if limit:
            hist = hist[-limit:]
        return [{"t": t, "price": p} for t, p in hist]
