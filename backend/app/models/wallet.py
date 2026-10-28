from decimal import Decimal

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, Money, TimestampMixin


class Wallet(IdMixin, TimestampMixin, Base):
    """Virtual cash. available = balance - blocked_margin."""

    __tablename__ = "wallets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    balance: Mapped[Decimal] = mapped_column(Money)
    blocked_margin: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    initial_balance: Mapped[Decimal] = mapped_column(Money)
    # Sum of INITIAL + TOPUP (+ ADMIN_ADJUST) since last reset; profit = equity - capital_added
    capital_added: Mapped[Decimal] = mapped_column(Money)

    user = relationship("User", back_populates="wallet", lazy="raise")

    @property
    def available(self) -> Decimal:
        return self.balance - self.blocked_margin


class WalletTransaction(IdMixin, TimestampMixin, Base):
    """Append-only ledger of every balance change."""

    __tablename__ = "wallet_transactions"

    wallet_id: Mapped[str] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Money)
    balance_after: Mapped[Decimal] = mapped_column(Money)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
