from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, Money, Price, TimestampMixin, utcnow


class ArbitrageOpportunity(IdMixin, TimestampMixin, Base):
    """A detected NSE-BSE price dislocation (shared across users)."""

    __tablename__ = "arbitrage_opportunities"

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    buy_exchange: Mapped[str] = mapped_column(String(5))
    sell_exchange: Mapped[str] = mapped_column(String(5))
    buy_price: Mapped[Decimal] = mapped_column(Price)
    sell_price: Mapped[Decimal] = mapped_column(Price)
    spread_abs: Mapped[Decimal] = mapped_column(Price)
    spread_pct: Mapped[Decimal] = mapped_column(Numeric(10, 5))
    quantity: Mapped[int] = mapped_column(Integer)
    max_qty: Mapped[int] = mapped_column(Integer)
    est_costs: Mapped[Decimal] = mapped_column(Money)
    est_net_profit: Mapped[Decimal] = mapped_column(Money)
    liquidity_ok: Mapped[bool] = mapped_column(Boolean)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ArbitrageTrade(IdMixin, TimestampMixin, Base):
    """One two-leg arbitrage execution for a user."""

    __tablename__ = "arbitrage_trades"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20))
    buy_exchange: Mapped[str] = mapped_column(String(5))
    sell_exchange: Mapped[str] = mapped_column(String(5))
    quantity: Mapped[int] = mapped_column(Integer)
    matched_qty: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(6))
    buy_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sell_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expected_spread: Mapped[Decimal] = mapped_column(Price)
    captured_spread: Mapped[Decimal] = mapped_column(Price, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(10))
    gross_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    total_costs: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    net_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
