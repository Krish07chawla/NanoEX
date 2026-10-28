from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import MoneyOut, ORMModel


class RiskSettingsOut(ORMModel):
    max_order_qty: int
    max_order_notional: MoneyOut
    max_position_value: MoneyOut
    daily_loss_limit: MoneyOut
    daily_volume_cap: MoneyOut
    max_open_orders: int
    kill_switch: bool
    arb_min_profit: MoneyOut
    arb_quantity: int
    arb_auto_enabled: bool


class RiskSettingsUpdate(BaseModel):
    max_order_qty: int | None = Field(default=None, gt=0, le=1_000_000)
    max_order_notional: Decimal | None = Field(default=None, gt=0)
    max_position_value: Decimal | None = Field(default=None, gt=0)
    daily_loss_limit: Decimal | None = Field(default=None, gt=0)
    daily_volume_cap: Decimal | None = Field(default=None, gt=0)
    max_open_orders: int | None = Field(default=None, gt=0, le=1000)
    arb_min_profit: Decimal | None = Field(default=None, ge=0)
    arb_quantity: int | None = Field(default=None, gt=0, le=100_000)
    arb_auto_enabled: bool | None = None


class KillSwitchRequest(BaseModel):
    enabled: bool
    cancel_open_orders: bool = True


class ArbExecuteRequest(BaseModel):
    symbol: str
    quantity: int | None = Field(default=None, gt=0, le=100_000)
    opportunity_id: str | None = None


class ArbAutoRequest(BaseModel):
    enabled: bool
    min_profit: Decimal | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, gt=0, le=100_000)
