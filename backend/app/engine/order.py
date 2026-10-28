"""In-memory order and fill types used by the order book (separate from ORM models)."""

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.constants import OrderType, Side


@dataclass(slots=True)
class BookOrder:
    order_id: str
    side: Side
    order_type: OrderType
    quantity: int
    price: Decimal | None = None  # None for market orders
    user_id: str | None = None  # None = simulated liquidity maker
    remaining: int = field(default=-1)
    seq: int = 0  # arrival sequence, for time priority

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type is OrderType.LIMIT and (self.price is None or self.price <= 0):
            raise ValueError("limit orders need a positive price")
        if self.remaining < 0:
            self.remaining = self.quantity

    @property
    def is_maker_bot(self) -> bool:
        return self.user_id is None


@dataclass(frozen=True, slots=True)
class Fill:
    symbol: str
    exchange: str
    price: Decimal
    quantity: int
    taker_order_id: str
    taker_user_id: str | None
    taker_side: Side
    maker_order_id: str
    maker_user_id: str | None


@dataclass(slots=True)
class MatchResult:
    fills: list[Fill] = field(default_factory=list)
    remaining: int = 0
    resting: bool = False  # remainder now rests in the book
    cancelled_ids: list[str] = field(default_factory=list)  # e.g. self-trade prevention

    @property
    def filled_qty(self) -> int:
        return sum(f.quantity for f in self.fills)
