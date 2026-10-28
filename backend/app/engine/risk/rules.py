"""Concrete risk rules. Add a new rule by writing a class and listing it in DEFAULT_RULES."""

from decimal import Decimal

from app.core.constants import Side
from app.core.exceptions import InsufficientFunds
from app.engine.risk.base_rule import RiskContext, RiskRule

SHORT_MARGIN_PCT = Decimal("0.20")  # intraday short sells need 20% of notional as margin


class KillSwitchRule(RiskRule):
    name = "kill_switch"

    def check(self, ctx: RiskContext) -> None:
        if ctx.kill_switch:
            self.reject("Kill switch is ON: all trading is stopped")


class MaxOrderQtyRule(RiskRule):
    name = "max_order_qty"

    def check(self, ctx: RiskContext) -> None:
        if ctx.quantity > ctx.max_order_qty:
            self.reject(f"Order quantity {ctx.quantity} exceeds limit {ctx.max_order_qty}")


class MaxOrderNotionalRule(RiskRule):
    name = "max_order_notional"

    def check(self, ctx: RiskContext) -> None:
        if ctx.notional > ctx.max_order_notional:
            self.reject(f"Order value Rs {ctx.notional:,.2f} exceeds limit Rs {ctx.max_order_notional:,.2f}")


class MaxOpenOrdersRule(RiskRule):
    name = "max_open_orders"

    def check(self, ctx: RiskContext) -> None:
        if ctx.open_orders >= ctx.max_open_orders:
            self.reject(f"Too many open orders (limit {ctx.max_open_orders})")


class MaxPositionValueRule(RiskRule):
    name = "max_position_value"

    def check(self, ctx: RiskContext) -> None:
        value = abs(ctx.new_position_qty) * ctx.price
        if not ctx.reduces_exposure and value > ctx.max_position_value:
            self.reject(f"Position value Rs {value:,.2f} would exceed limit Rs {ctx.max_position_value:,.2f}")


class DailyLossLimitRule(RiskRule):
    name = "daily_loss_limit"

    def check(self, ctx: RiskContext) -> None:
        if not ctx.reduces_exposure and ctx.day_pnl <= -ctx.daily_loss_limit:
            self.reject(f"Daily loss limit Rs {ctx.daily_loss_limit:,.2f} reached; only exits allowed today")


class DailyVolumeCapRule(RiskRule):
    name = "daily_volume_cap"

    def check(self, ctx: RiskContext) -> None:
        if ctx.day_volume + ctx.notional > ctx.daily_volume_cap:
            self.reject(f"Daily traded value cap Rs {ctx.daily_volume_cap:,.2f} reached")


class FundsRule(RiskRule):
    """Buys need cash for value + fees. Short sells need margin; closing a long needs nothing."""

    name = "funds"

    def check(self, ctx: RiskContext) -> None:
        if ctx.side is Side.BUY:
            required = ctx.notional + ctx.est_fees
        else:
            short_qty = max(0, -ctx.new_position_qty) - max(0, -ctx.position_qty)
            required = ctx.price * short_qty * SHORT_MARGIN_PCT + ctx.est_fees
        if required > ctx.available_funds:
            raise InsufficientFunds(
                f"Insufficient funds: need Rs {required:,.2f}, available Rs {ctx.available_funds:,.2f}",
                details={"rule": self.name},
            )


DEFAULT_RULES: tuple[type[RiskRule], ...] = (
    KillSwitchRule,
    MaxOrderQtyRule,
    MaxOrderNotionalRule,
    MaxOpenOrdersRule,
    MaxPositionValueRule,
    DailyLossLimitRule,
    DailyVolumeCapRule,
    FundsRule,
)
