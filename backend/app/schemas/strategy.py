from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import Exchange
from app.schemas.common import ORMModel

PCT_LIMIT = 50


class StrategyConfigIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    strategy_type: str
    symbol: str = Field(min_length=1, max_length=20)
    exchange: Exchange = Exchange.NSE
    params: dict[str, Any] = {}
    quantity: int = Field(gt=0, le=100_000)
    stop_loss_pct: Decimal | None = Field(default=None, gt=0, le=PCT_LIMIT)
    take_profit_pct: Decimal | None = Field(default=None, gt=0, le=PCT_LIMIT * 4)
    trailing_stop_pct: Decimal | None = Field(default=None, gt=0, le=PCT_LIMIT)


class StrategyConfigOut(ORMModel):
    id: str
    name: str
    strategy_type: str
    symbol: str
    exchange: str
    params: dict[str, Any]
    quantity: int
    stop_loss_pct: float | None
    take_profit_pct: float | None
    trailing_stop_pct: float | None
    is_active: bool
    created_at: datetime


class BacktestRequest(BaseModel):
    strategy_type: str
    params: dict[str, Any] = {}
    symbol: str = "RELIANCE"
    data_source: str = Field(default="synthetic", pattern="^(synthetic|yfinance)$")
    bars: int = Field(default=500, ge=50, le=5000)
    seed: int | None = 42
    initial_capital: Decimal = Field(default=Decimal("500000"), gt=0, le=Decimal("100000000"))
    position_size_pct: float = Field(default=100, gt=0, le=100)
    slippage_bps: float = Field(default=2, ge=0, le=100)
    stop_loss_pct: float | None = Field(default=None, gt=0, le=PCT_LIMIT)
    take_profit_pct: float | None = Field(default=None, gt=0, le=PCT_LIMIT * 4)
    trailing_stop_pct: float | None = Field(default=None, gt=0, le=PCT_LIMIT)
    save: bool = True
