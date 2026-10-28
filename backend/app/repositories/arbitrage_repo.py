from sqlalchemy import select

from app.models.arbitrage import ArbitrageOpportunity, ArbitrageTrade
from app.repositories.base import BaseRepository


class ArbitrageOpportunityRepository(BaseRepository[ArbitrageOpportunity]):
    model = ArbitrageOpportunity

    def recent(self, symbol: str | None = None):
        stmt = select(ArbitrageOpportunity)
        if symbol:
            stmt = stmt.where(ArbitrageOpportunity.symbol == symbol)
        return stmt.order_by(ArbitrageOpportunity.detected_at.desc())


class ArbitrageTradeRepository(BaseRepository[ArbitrageTrade]):
    model = ArbitrageTrade

    def for_user(self, user_id: str):
        return (
            select(ArbitrageTrade).where(ArbitrageTrade.user_id == user_id).order_by(ArbitrageTrade.created_at.desc())
        )

    async def all_for_user(self, user_id: str) -> list[ArbitrageTrade]:
        stmt = select(ArbitrageTrade).where(ArbitrageTrade.user_id == user_id).order_by(ArbitrageTrade.created_at)
        return list((await self.session.execute(stmt)).scalars().all())
