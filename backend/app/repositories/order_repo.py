from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.core.constants import OrderStatus
from app.models.order import Order
from app.models.trade import Trade
from app.repositories.base import BaseRepository

OPEN_STATUSES = (OrderStatus.NEW, OrderStatus.PARTIAL)


class OrderRepository(BaseRepository[Order]):
    model = Order

    def for_user(self, user_id: str, status: str | None = None, symbol: str | None = None):
        stmt = select(Order).where(Order.user_id == user_id)
        if status:
            stmt = stmt.where(Order.status == status)
        if symbol:
            stmt = stmt.where(Order.symbol == symbol)
        return stmt.order_by(Order.created_at.desc())

    async def count_open(self, user_id: str) -> int:
        stmt = select(func.count()).where(Order.user_id == user_id, Order.status.in_(OPEN_STATUSES))
        return int((await self.session.execute(stmt)).scalar_one())

    async def open_orders(self, user_id: str | None = None) -> list[Order]:
        stmt = select(Order).where(Order.status.in_(OPEN_STATUSES))
        if user_id:
            stmt = stmt.where(Order.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())


class TradeRepository(BaseRepository[Trade]):
    model = Trade

    def for_user(
        self,
        user_id: str,
        symbol: str | None = None,
        side: str | None = None,
        source: str | None = None,
        exchange: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ):
        stmt = select(Trade).where(Trade.user_id == user_id)
        if symbol:
            stmt = stmt.where(Trade.symbol == symbol)
        if side:
            stmt = stmt.where(Trade.side == side)
        if source:
            stmt = stmt.where(Trade.source == source)
        if exchange:
            stmt = stmt.where(Trade.exchange == exchange)
        if start:
            stmt = stmt.where(Trade.executed_at >= start)
        if end:
            stmt = stmt.where(Trade.executed_at <= end)
        return stmt.order_by(Trade.executed_at.desc())

    async def all_for_user(self, user_id: str) -> list[Trade]:
        stmt = select(Trade).where(Trade.user_id == user_id).order_by(Trade.executed_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def day_stats(self, user_id: str, since: datetime) -> tuple[Decimal, Decimal]:
        """Return (traded notional, realized pnl net of fees) since a timestamp."""
        stmt = select(
            func.coalesce(func.sum(Trade.price * Trade.quantity), 0),
            func.coalesce(func.sum(Trade.realized_pnl - Trade.fees), 0),
        ).where(Trade.user_id == user_id, Trade.executed_at >= since)
        volume, pnl = (await self.session.execute(stmt)).one()
        return Decimal(str(volume)), Decimal(str(pnl))
