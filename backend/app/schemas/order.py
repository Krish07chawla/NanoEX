from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.core.constants import Exchange, OrderType, Side
from app.schemas.common import MoneyOut, ORMModel, PriceOut


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    exchange: Exchange
    side: Side
    order_type: OrderType = OrderType.MARKET
    quantity: int = Field(gt=0, le=1_000_000)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)

    @model_validator(mode="after")
    def check_price(self) -> "PlaceOrderRequest":
        self.symbol = self.symbol.upper()
        if self.order_type is OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for LIMIT orders")
        if self.order_type is OrderType.MARKET:
            self.price = None
        return self


class OrderOut(ORMModel):
    id: str
    symbol: str
    exchange: str
    side: str
    order_type: str
    price: PriceOut | None
    quantity: int
    filled_qty: int
    avg_fill_price: PriceOut | None
    status: str
    source: str
    strategy_name: str | None
    signal_reason: str | None
    reject_reason: str | None
    latency_us: int | None
    created_at: datetime


class TradeOut(ORMModel):
    id: str
    order_id: str
    symbol: str
    exchange: str
    side: str
    price: PriceOut
    quantity: int
    fees: MoneyOut
    realized_pnl: MoneyOut
    source: str
    strategy_name: str | None
    signal_reason: str | None
    executed_at: datetime
