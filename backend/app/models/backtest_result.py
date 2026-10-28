from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, Money, TimestampMixin


class BacktestResult(IdMixin, TimestampMixin, Base):
    __tablename__ = "backtest_results"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    strategy_type: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    symbol: Mapped[str] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(20))
    bars: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_capital: Mapped[Decimal] = mapped_column(Money)
    metrics: Mapped[dict] = mapped_column(JSON)
    equity_curve: Mapped[list] = mapped_column(JSON)
    trades: Mapped[list] = mapped_column(JSON)
