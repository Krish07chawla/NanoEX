from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import OrderStatus
from app.db.base import Base, IdMixin, Money, Price, TimestampMixin


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    exchange: Mapped[str] = mapped_column(String(5))
    side: Mapped[str] = mapped_column(String(4))
    order_type: Mapped[str] = mapped_column(String(6))
    price: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    filled_qty: Mapped[int] = mapped_column(Integer, default=0)
    avg_fill_price: Mapped[Decimal | None] = mapped_column(Price, nullable=True)
    blocked_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(10), default=OrderStatus.NEW, index=True)
    source: Mapped[str] = mapped_column(String(10))
    strategy_config_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    arbitrage_trade_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    signal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_us: Mapped[int | None] = mapped_column(Integer, nullable=True)
