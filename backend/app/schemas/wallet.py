from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import MoneyOut, ORMModel


class WalletOut(ORMModel):
    id: str
    balance: MoneyOut
    blocked_margin: MoneyOut
    available: MoneyOut
    initial_balance: MoneyOut
    capital_added: MoneyOut
    updated_at: datetime


class WalletTxnOut(ORMModel):
    id: str
    type: str
    amount: MoneyOut
    balance_after: MoneyOut
    reference_id: str | None
    note: str | None
    created_at: datetime


class TopUpRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class AdminWalletAdjust(BaseModel):
    amount: Decimal = Field(decimal_places=2)  # may be negative
    note: str = Field(min_length=3, max_length=255)
