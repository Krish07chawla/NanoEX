"""Risk rule interface (Chain of Responsibility). Each rule checks one thing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.core.constants import Side
from app.core.exceptions import RiskLimitExceeded


@dataclass(frozen=True)
class RiskContext:
    """Everything a rule needs to decide, gathered once by the service."""

    side: Side
    quantity: int
    price: Decimal  # limit price, or reference price for market orders
    est_fees: Decimal
    available_funds: Decimal
    position_qty: int  # current net position in the symbol
    open_orders: int
    day_volume: Decimal  # traded notional today
    day_pnl: Decimal  # realized net P&L today
    # limits
    kill_switch: bool
    max_order_qty: int
    max_order_notional: Decimal
    max_position_value: Decimal
    daily_loss_limit: Decimal
    daily_volume_cap: Decimal
    max_open_orders: int

    @property
    def notional(self) -> Decimal:
        return self.price * self.quantity

    @property
    def new_position_qty(self) -> int:
        return self.position_qty + (self.quantity if self.side is Side.BUY else -self.quantity)

    @property
    def reduces_exposure(self) -> bool:
        return abs(self.new_position_qty) < abs(self.position_qty)


class RiskRule(ABC):
    name: str = "rule"

    @abstractmethod
    def check(self, ctx: RiskContext) -> None:
        """Raise RiskLimitExceeded if the order violates this rule."""

    def reject(self, message: str) -> None:
        raise RiskLimitExceeded(message, details={"rule": self.name})
