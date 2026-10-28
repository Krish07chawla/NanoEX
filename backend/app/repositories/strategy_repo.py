from sqlalchemy import select

from app.models.backtest_result import BacktestResult
from app.models.strategy_config import StrategyConfig
from app.repositories.base import BaseRepository


class StrategyConfigRepository(BaseRepository[StrategyConfig]):
    model = StrategyConfig

    async def for_user(self, user_id: str) -> list[StrategyConfig]:
        stmt = select(StrategyConfig).where(StrategyConfig.user_id == user_id)
        return list((await self.session.execute(stmt.order_by(StrategyConfig.created_at))).scalars().all())

    async def active(self) -> list[StrategyConfig]:
        stmt = select(StrategyConfig).where(StrategyConfig.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class BacktestRepository(BaseRepository[BacktestResult]):
    model = BacktestResult

    def for_user(self, user_id: str):
        return (
            select(BacktestResult).where(BacktestResult.user_id == user_id).order_by(BacktestResult.created_at.desc())
        )
