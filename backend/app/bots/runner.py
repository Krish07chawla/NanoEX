"""BotRunner: runs every active strategy config against live ticks.

Each config gets its own StrategyTrader (strategy + SL/TP/trailing exits).
Signals become MARKET orders through OrderService, so bots obey the same risk
rules as manual trading. Bot holdings are tracked in memory; after a restart
bots start flat (open positions stay in the portfolio for manual handling).
"""

import asyncio
import contextlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.constants import OrderSource, OrderType, Side
from app.core.event_bus import Topics
from app.core.exceptions import DomainError
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.db.session import session_factory
from app.models.strategy_config import StrategyConfig
from app.repositories.strategy_repo import StrategyConfigRepository
from app.schemas.order import PlaceOrderRequest
from app.services.order_service import OrderContext, OrderService
from app.strategies.base import Action
from app.strategies.exits import ExitRules
from app.strategies.factory import StrategyFactory
from app.strategies.trader import Decision, StrategyTrader

if TYPE_CHECKING:
    from app.container import Container

REFRESH_SECONDS = 3.0
log = get_logger(__name__)


@dataclass
class _Bot:
    config_id: str
    user_id: str
    name: str
    strategy_key: str
    symbol: str
    exchange: str
    quantity: int
    trader: StrategyTrader
    held: int = 0
    last_signal: str | None = None


def _f(value) -> float | None:
    return float(value) if value is not None else None


class BotRunner:
    def __init__(self, container: "Container"):
        self.c = container
        self.bots: dict[str, _Bot] = {}
        self._task: asyncio.Task | None = None
        self._queue: asyncio.Queue | None = None
        self._last_refresh = 0.0
        self.running = False

    async def start(self) -> None:
        self.running = True
        self._queue = self.c.bus.subscribe(Topics.TICK)
        self._task = asyncio.create_task(self._run(), name="bot-runner")

    async def stop(self) -> None:
        self.running = False
        if self._queue is not None:
            self.c.bus.unsubscribe(self._queue)
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def status(self, config_id: str) -> dict | None:
        bot = self.bots.get(config_id)
        if not bot:
            return None
        return {"running": True, "held": bot.held, "last_signal": bot.last_signal}

    async def refresh(self) -> None:
        """Sync running bots with active configs in the database."""
        async with session_factory()() as session:
            active = {c.id: c for c in await StrategyConfigRepository(session).active()}
        for cid in list(self.bots):
            if cid not in active:
                del self.bots[cid]
        for cid, cfg in active.items():
            if cid not in self.bots:
                self.bots[cid] = self._build(cfg)
        self._last_refresh = time.time()

    def _build(self, cfg: StrategyConfig) -> _Bot:
        exits = ExitRules(_f(cfg.stop_loss_pct), _f(cfg.take_profit_pct), _f(cfg.trailing_stop_pct))
        trader = StrategyTrader(StrategyFactory.create(cfg.strategy_type, cfg.params), exits)
        return _Bot(cfg.id, cfg.user_id, cfg.name, cfg.strategy_type, cfg.symbol, cfg.exchange, cfg.quantity, trader)

    async def _run(self) -> None:
        assert self._queue is not None
        while self.running:
            message = await self._queue.get()
            try:
                if time.time() - self._last_refresh > REFRESH_SECONDS:
                    await self.refresh()
                await self.on_ticks(message["data"])
            except Exception:  # noqa: BLE001
                log.exception("bot_runner_failed")

    async def on_ticks(self, ticks: list[dict]) -> None:
        prices = {(t["symbol"], t["exchange"]): (t["last"], t["timestamp"]) for t in ticks}
        for bot in list(self.bots.values()):
            if (bot.symbol, bot.exchange) not in prices:
                continue
            price, tick_ts = prices[(bot.symbol, bot.exchange)]
            decision = bot.trader.on_price(price)
            if decision and (decision.action is Action.BUY) == (bot.held == 0):
                await self._act(bot, decision, tick_ts)

    async def _act(self, bot: _Bot, decision: Decision, tick_ts: float) -> None:
        side = Side.BUY if decision.action is Action.BUY else Side.SELL
        qty = bot.quantity if side is Side.BUY else bot.held
        bot.last_signal = f"{side}: {decision.reason}"
        async with session_factory()() as session:
            try:
                order = await OrderService(session, self.c).place(
                    bot.user_id,
                    PlaceOrderRequest(
                        symbol=bot.symbol,
                        exchange=bot.exchange,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=qty,
                    ),
                    OrderContext(OrderSource.STRATEGY, bot.config_id, bot.name, decision.reason[:255]),
                )
                await session.commit()
            except DomainError as exc:
                await session.commit()  # keep the rejected order for the user to see
                bot.last_signal = f"{side} rejected: {exc.message}"
                return
        metrics.record_tick_to_trade((time.time() - tick_ts) * 1_000_000)
        if order.filled_qty > 0:
            bot.held += order.filled_qty if side is Side.BUY else -order.filled_qty
            bot.trader.confirm(decision, float(order.avg_fill_price or 0))
