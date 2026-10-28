"""ArbitrageScanner: tick hook that keeps the live NSE vs BSE spread board and
the current best opportunity per symbol, publishes them, and logs profitable ones."""

import time
from collections import deque
from decimal import Decimal
from typing import TYPE_CHECKING

from app.arbitrage.detector import ArbitrageDetector, Opportunity, quote_spread
from app.core.constants import DEFAULT_ARB_QTY, Exchange
from app.core.event_bus import Topics
from app.core.logging import get_logger
from app.db.session import session_factory
from app.market.providers.base import Quote
from app.models.arbitrage import ArbitrageOpportunity

if TYPE_CHECKING:
    from app.container import Container

PERSIST_THROTTLE_SECONDS = 2.0
RECENT_LIMIT = 200
log = get_logger(__name__)


class ArbitrageScanner:
    def __init__(self, container: "Container"):
        self.c = container
        self.detector = ArbitrageDetector(container.cost_model)
        self.board: dict[str, dict] = {}
        self.best: dict[str, Opportunity] = {}
        self.recent: deque[dict] = deque(maxlen=RECENT_LIMIT)
        self._last_persist: dict[str, float] = {}

    def evaluate(self, symbol: str, quantity: int) -> Opportunity | None:
        books = {e.value: self.c.engine.book(symbol, e.value) for e in Exchange}
        return self.detector.evaluate(symbol, books, quantity)

    async def on_quotes(self, quotes: list[Quote]) -> None:
        by_symbol: dict[str, dict[str, Quote]] = {}
        for q in quotes:
            by_symbol.setdefault(q.symbol, {})[q.exchange] = q
        to_persist: list[Opportunity] = []
        now = time.time()
        for symbol, pair in by_symbol.items():
            if len(pair) < 2:
                continue
            row = quote_spread(pair[Exchange.NSE.value], pair[Exchange.BSE.value])
            opp = self.evaluate(symbol, DEFAULT_ARB_QTY)
            if opp is not None:
                self.best[symbol] = opp
                row["opportunity"] = opp.to_dict()
                if opp.is_actionable(Decimal("0")):
                    self.recent.appendleft({**opp.to_dict(), "detected_at": now})
                    if now - self._last_persist.get(symbol, 0) >= PERSIST_THROTTLE_SECONDS:
                        self._last_persist[symbol] = now
                        to_persist.append(opp)
            self.board[symbol] = row
        self.c.bus.publish(Topics.ARB_OPPORTUNITY, list(self.board.values()))
        if to_persist:
            await self._persist(to_persist)

    async def _persist(self, opps: list[Opportunity]) -> None:
        try:
            async with session_factory()() as session:
                for o in opps:
                    session.add(
                        ArbitrageOpportunity(
                            symbol=o.symbol,
                            buy_exchange=o.buy_exchange,
                            sell_exchange=o.sell_exchange,
                            buy_price=o.buy_price,
                            sell_price=o.sell_price,
                            spread_abs=o.spread_abs,
                            spread_pct=o.spread_pct,
                            quantity=o.quantity,
                            max_qty=o.max_qty,
                            est_costs=o.costs.total,
                            est_net_profit=o.net_profit,
                            liquidity_ok=o.liquidity_ok,
                        )
                    )
                await session.commit()
        except Exception:  # noqa: BLE001 - logging opportunities must never stop the feed
            log.exception("arb_persist_failed")
