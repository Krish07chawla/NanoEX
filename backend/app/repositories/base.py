"""Generic async repository (Repository pattern). Services never write SQL directly."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, entity_id: str) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def list(self, stmt: Select, *, offset: int = 0, limit: int = 50) -> Sequence[ModelT]:
        result = await self.session.execute(stmt.offset(offset).limit(limit))
        return result.scalars().all()

    async def count(self, stmt: Select) -> int:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        return int((await self.session.execute(count_stmt)).scalar_one())

    async def page(self, stmt: Select, page: int, size: int) -> tuple[Sequence[ModelT], int]:
        total = await self.count(stmt)
        items = await self.list(stmt, offset=(page - 1) * size, limit=size)
        return items, total

    def base_query(self, **filters: Any) -> Select:
        stmt = select(self.model)
        for column, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, column) == value)
        return stmt
