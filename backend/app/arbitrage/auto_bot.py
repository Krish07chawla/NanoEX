"""Auto-arbitrage bot: for every user with Auto mode on, executes the best
opportunity that clears their own minimum-profit threshold, within risk limits."""

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

from app.core.constants import ArbMode
from app.core.exceptions import DomainError
from app.core.logging import get_logger
from app.db.session import session_factory
from app.repositories.risk_repo import RiskSettingsRepository

if TYPE_CHECKING:
    from app.container import Container

COOLDOWN_SECONDS = 3.0  # per user + symbol, so one dislocation is not hit repeatedly
log = get_logger(__name__)


class AutoArbitrageBot:
    def __init__(self, container: "Container"):
        self.c = container
        self._task: asyncio.Task | None = None
        self._last: dict[tuple[str, str], float] = {}
        self.running = False

    async def start(self) -> None:
        self.running = True
        self._task = asyncio.create_task(self._run(), name="auto-arbitrage")

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        interval = self.c.settings.arb_auto_interval_ms / 1000
        while self.running:
            try:
                await self.scan_once()
            except Exception:  # noqa: BLE001
                log.exception("auto_arb_failed")
            await asyncio.sleep(interval)

    async def scan_once(self) -> int:
        """One pass over all auto-enabled users. Returns the number of executions."""
        async with session_factory()() as session:
            user_ids = await RiskSettingsRepository(session).users_with_auto_arb()
        executed = 0
        for user_id in user_ids:
            executed += await self._for_user(user_id)
        return executed

    async def _for_user(self, user_id: str) -> int:
        async with session_factory()() as session:
            limits = await RiskSettingsRepository(session).get_or_create(user_id)
            now = time.time()
            best = None
            for symbol in self.c.market.symbols():
                if now - self._last.get((user_id, symbol), 0) < COOLDOWN_SECONDS:
                    continue
                opp = self.c.arb_scanner.evaluate(symbol, limits.arb_quantity)
                if (
                    opp
                    and opp.is_actionable(limits.arb_min_profit)
                    and (best is None or opp.net_profit > best.net_profit)
                ):
                    best = opp
            if best is None:
                return 0
            self._last[(user_id, best.symbol)] = now
            try:
                await self.c.arb_executor.execute(
                    session, user_id, best.symbol, limits.arb_quantity, ArbMode.AUTO, limits.arb_min_profit
                )
                await session.commit()
                return 1
            except DomainError as exc:
                await session.rollback()
                log.info("auto_arb_skipped", user_id=user_id, reason=exc.message)
                return 0
