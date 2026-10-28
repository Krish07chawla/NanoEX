from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, Money, Price, TimestampMixin, utcnow


class Trade(IdMixin, TimestampMixin, Base):
    """One fill. An order with partial fills has several trades."""

    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_user_time", "user_id", "executed_at"),)

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20))
    exchange: Mapped[str] = mapped_column(String(5))
    side: Mapped[str] = mapped_column(String(4))
    price: Mapped[Decimal] = mapped_column(Price)
    quantity: Mapped[int] = mapped_column(Integer)
    fees: Mapped[Decimal] = mapped_column(Money)
    realized_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    source: Mapped[str] = mapped_column(String(10))
    strategy_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
