from sqlalchemy import select

from app.models.position import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def get_for(self, user_id: str, symbol: str) -> Position | None:
        result = await self.session.execute(
            select(Position).where(Position.user_id == user_id, Position.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: str, symbol: str) -> Position:
        pos = await self.get_for(user_id, symbol)
        if pos is None:
            pos = await self.add(Position(user_id=user_id, symbol=symbol, quantity=0))
        return pos

    async def for_user(self, user_id: str, open_only: bool = False) -> list[Position]:
        stmt = select(Position).where(Position.user_id == user_id)
        if open_only:
            stmt = stmt.where(Position.quantity != 0)
        return list((await self.session.execute(stmt.order_by(Position.symbol))).scalars().all())
