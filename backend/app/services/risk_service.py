"""Risk settings and the kill switch."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.models.risk_settings import RiskSettings
from app.models.user import User
from app.repositories.order_repo import OrderRepository
from app.repositories.risk_repo import RiskSettingsRepository
from app.repositories.strategy_repo import StrategyConfigRepository
from app.schemas.risk import RiskSettingsUpdate
from app.services.audit_service import AuditService
from app.services.order_service import OrderService

if TYPE_CHECKING:
    from app.container import Container


class RiskService:
    def __init__(self, session: AsyncSession, container: "Container"):
        self.session = session
        self.c = container
        self.repo = RiskSettingsRepository(session)
        self.audit = AuditService(session)

    async def get(self, user_id: str) -> RiskSettings:
        return await self.repo.get_or_create(user_id)

    async def update(self, user_id: str, body: RiskSettingsUpdate) -> RiskSettings:
        settings = await self.get(user_id)
        changes = body.model_dump(exclude_none=True)
        for key, value in changes.items():
            setattr(settings, key, value)
        await self.audit.log(
            AuditAction.RISK_CHANGE,
            user_id=user_id,
            entity="risk_settings",
            entity_id=settings.id,
            details={k: str(v) for k, v in changes.items()},
        )
        await self.session.flush()
        return settings

    async def kill_switch(self, user: User, enabled: bool, cancel_open_orders: bool) -> dict:
        """Stop everything: block new orders, stop bots and auto-arbitrage, optionally cancel open orders."""
        settings = await self.get(user.id)
        settings.kill_switch = enabled
        cancelled = stopped = 0
        if enabled:
            settings.arb_auto_enabled = False
            for cfg in await StrategyConfigRepository(self.session).for_user(user.id):
                if cfg.is_active:
                    cfg.is_active = False
                    self.c.bot_runner.bots.pop(cfg.id, None)
                    stopped += 1
            if cancel_open_orders:
                svc = OrderService(self.session, self.c)
                for order in await OrderRepository(self.session).open_orders(user.id):
                    removed = await self.c.engine.cancel(order.symbol, order.exchange, order.id)
                    if removed:
                        await svc._mark_cancelled(order, "Cancelled by kill switch")
                        cancelled += 1
        await self.audit.log(
            AuditAction.KILL_SWITCH,
            user_id=user.id,
            details={"enabled": enabled, "cancelled_orders": cancelled, "stopped_bots": stopped},
        )
        await self.session.flush()
        return {"kill_switch": enabled, "cancelled_orders": cancelled, "stopped_bots": stopped}
