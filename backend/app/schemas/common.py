"""Shared DTO helpers."""

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

T = TypeVar("T")

# Decimals go over the wire as JSON numbers (rounded) for easy charting in the UI.
MoneyOut = Annotated[Decimal, PlainSerializer(lambda v: float(round(v, 2)), return_type=float)]
PriceOut = Annotated[Decimal, PlainSerializer(lambda v: float(round(v, 4)), return_type=float)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageParams(BaseModel):
    page: int = 1
    size: int = DEFAULT_PAGE_SIZE

    def clamp(self) -> "PageParams":
        return PageParams(page=max(1, self.page), size=min(max(1, self.size), MAX_PAGE_SIZE))


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
