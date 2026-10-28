from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, Money, Price, TimestampMixin


class Position(IdMixin, TimestampMixin, Base):
    """Net holding per symbol. Exchange-agnostic, like a demat account:
    buying on NSE and selling on BSE nets to zero (that is what makes arbitrage work).
    quantity > 0 = long, < 0 = short."""

    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_position_user_symbol"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[Decimal] = mapped_column(Price, default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
