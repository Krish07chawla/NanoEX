from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core import constants as c
from app.db.base import Base, IdMixin, Money, TimestampMixin


class RiskSettings(IdMixin, TimestampMixin, Base):
    __tablename__ = "risk_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    max_order_qty: Mapped[int] = mapped_column(Integer, default=c.DEFAULT_MAX_ORDER_QTY)
    max_order_notional: Mapped[Decimal] = mapped_column(Money, default=c.DEFAULT_MAX_ORDER_NOTIONAL)
    max_position_value: Mapped[Decimal] = mapped_column(Money, default=c.DEFAULT_MAX_POSITION_VALUE)
    daily_loss_limit: Mapped[Decimal] = mapped_column(Money, default=c.DEFAULT_DAILY_LOSS_LIMIT)
    daily_volume_cap: Mapped[Decimal] = mapped_column(Money, default=c.DEFAULT_DAILY_VOLUME_CAP)
    max_open_orders: Mapped[int] = mapped_column(Integer, default=c.DEFAULT_MAX_OPEN_ORDERS)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    arb_min_profit: Mapped[Decimal] = mapped_column(Money, default=c.DEFAULT_ARB_MIN_PROFIT)
    arb_quantity: Mapped[int] = mapped_column(Integer, default=c.DEFAULT_ARB_QTY)
    arb_auto_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
