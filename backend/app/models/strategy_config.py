from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class StrategyConfig(IdMixin, TimestampMixin, Base):
    """A user's configured live strategy bot."""

    __tablename__ = "strategies_config"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    strategy_type: Mapped[str] = mapped_column(String(40))
    symbol: Mapped[str] = mapped_column(String(20))
    exchange: Mapped[str] = mapped_column(String(5))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    quantity: Mapped[int] = mapped_column(Integer)
    stop_loss_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    take_profit_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    trailing_stop_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
