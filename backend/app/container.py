"""Composition root: builds every long-lived component once and wires them together
(dependency injection without a framework)."""

from app.arbitrage.auto_bot import AutoArbitrageBot
from app.arbitrage.cost_model import CostModel
from app.arbitrage.executor import ArbitrageExecutor
from app.arbitrage.scanner import ArbitrageScanner
from app.bots.runner import BotRunner
from app.core.config import Settings
from app.core.constants import OrderType, Side
from app.core.event_bus import EventBus
from app.core.events import set_bus
from app.db.session import session_factory
from app.engine.matching_engine import MatchingEngine
from app.engine.order import BookOrder
from app.engine.risk import RiskManager
from app.market.providers import MarketDataProvider, build_provider
from app.market.streamer import MarketDataService
from app.repositories.order_repo import OrderRepository
from app.services.settlement_service import SettlementService


class Container:
    def __init__(self, settings: Settings, provider: MarketDataProvider | None = None):
        self.settings = settings
        self.bus = EventBus()
        set_bus(self.bus)
        self.cost_model = CostModel()
        self.risk_manager = RiskManager()
        self.engine = MatchingEngine(settings.book_depth_levels, settings.sim_seed)
        self.engine.fill_handler = self._settle_background_fills
        self.market = MarketDataService(
            provider or build_provider(settings), self.bus, settings.tick_interval_ms, settings.history_buffer_size
        )
        self.arb_scanner = ArbitrageScanner(self)
        self.arb_executor = ArbitrageExecutor(self)
        self.auto_arb = AutoArbitrageBot(self)
        self.bot_runner = BotRunner(self)
        # Observer wiring: engine re-quotes first, then the scanner reads fresh books.
        self.market.add_hook(self.engine.on_quotes)
        self.market.add_hook(self.arb_scanner.on_quotes)

    async def start(self, background: bool = True) -> None:
        await self._restore_open_orders()
        await self.market.start() if background else await self.market.step()
        if background:
            await self.bot_runner.start()
            await self.auto_arb.start()

    async def stop(self) -> None:
        await self.auto_arb.stop()
        await self.bot_runner.stop()
        await self.market.stop()

    async def _settle_background_fills(self, fills) -> None:
        async with session_factory()() as session:
            await SettlementService(session, self.cost_model).settle_fills(fills)
            await session.commit()

    async def _restore_open_orders(self) -> None:
        async with session_factory()() as session:
            for o in await OrderRepository(session).open_orders():
                remaining = o.quantity - o.filled_qty
                await self.engine.restore(
                    o.symbol,
                    o.exchange,
                    BookOrder(o.id, Side(o.side), OrderType(o.order_type), remaining, price=o.price, user_id=o.user_id),
                )
