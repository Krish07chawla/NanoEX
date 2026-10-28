"""Wallet use cases: create, top-up, reset, trade settlement and admin adjustments.

Every balance change appends a WalletTransaction so the balance is auditable.
Top-ups increase `capital_added`, which the profit dashboard subtracts from
equity, so adding money never shows up as profit.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import PAISE, AuditAction, WalletTxnType
from app.core.exceptions import Conflict, InsufficientFunds, NotFound, ValidationFailed
from app.models.wallet import Wallet, WalletTransaction
from app.repositories.position_repo import PositionRepository
from app.repositories.wallet_repo import WalletRepository, WalletTransactionRepository
from app.services.audit_service import AuditService


class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.wallets = WalletRepository(session)
        self.txns = WalletTransactionRepository(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def create_for_user(self, user_id: str) -> Wallet:
        amount = self.settings.initial_wallet_balance
        wallet = await self.wallets.add(
            Wallet(
                user_id=user_id,
                balance=amount,
                blocked_margin=Decimal("0"),
                initial_balance=amount,
                capital_added=amount,
            )
        )
        await self._record(wallet, WalletTxnType.INITIAL, amount, note="Opening virtual balance")
        return wallet

    async def get(self, user_id: str) -> Wallet:
        wallet = await self.wallets.get_by_user(user_id)
        if wallet is None:
            raise NotFound("Wallet not found")
        return wallet

    async def top_up(self, user_id: str, amount: Decimal, note: str | None = None) -> Wallet:
        amount = amount.quantize(PAISE)
        if amount > self.settings.max_topup_amount:
            raise ValidationFailed(
                f"Maximum top-up is Rs {self.settings.max_topup_amount:,.0f} per request",
                code="TOPUP_LIMIT",
            )
        wallet = await self.get(user_id)
        since = datetime.now(UTC) - timedelta(days=1)
        if await self.txns.count_since(wallet.id, WalletTxnType.TOPUP, since) >= self.settings.max_daily_topups:
            raise ValidationFailed("Daily top-up limit reached, try again tomorrow", code="TOPUP_LIMIT")
        wallet.balance += amount
        wallet.capital_added += amount
        await self._record(wallet, WalletTxnType.TOPUP, amount, note=note or "Virtual top-up")
        await self.audit.log(
            AuditAction.WALLET_TOPUP,
            user_id=user_id,
            entity="wallet",
            entity_id=wallet.id,
            details={"amount": str(amount)},
        )
        return wallet

    async def reset(self, user_id: str) -> Wallet:
        """Reset to the opening balance. Only allowed when flat (no open positions/orders)."""
        wallet = await self.get(user_id)
        open_positions = await PositionRepository(self.session).for_user(user_id, open_only=True)
        if open_positions or wallet.blocked_margin > 0:
            raise Conflict("Close all positions and cancel open orders before resetting", code="NOT_FLAT")
        amount = self.settings.initial_wallet_balance
        delta = amount - wallet.balance
        wallet.balance = amount
        wallet.capital_added = amount
        wallet.initial_balance = amount
        await self._record(wallet, WalletTxnType.RESET, delta, note="Wallet reset")
        await self.audit.log(AuditAction.WALLET_RESET, user_id=user_id, entity="wallet", entity_id=wallet.id)
        return wallet

    async def admin_adjust(self, admin_id: str, user_id: str, amount: Decimal, note: str) -> Wallet:
        wallet = await self.get(user_id)
        amount = amount.quantize(PAISE)
        if wallet.available + amount < 0:
            raise InsufficientFunds("Adjustment would make the balance negative")
        wallet.balance += amount
        wallet.capital_added += amount
        await self._record(wallet, WalletTxnType.ADMIN_ADJUST, amount, note=note)
        await self.audit.log(
            AuditAction.ADMIN_ACTION,
            user_id=admin_id,
            entity="wallet",
            entity_id=wallet.id,
            details={"target_user": user_id, "amount": str(amount), "note": note},
        )
        return wallet

    # --- used by trade settlement ---
    async def block(self, wallet: Wallet, amount: Decimal) -> None:
        if amount > wallet.available:
            raise InsufficientFunds(f"Insufficient funds: need Rs {amount:,.2f}, available Rs {wallet.available:,.2f}")
        wallet.blocked_margin += amount

    @staticmethod
    def release(wallet: Wallet, amount: Decimal) -> None:
        wallet.blocked_margin = max(Decimal("0"), wallet.blocked_margin - amount)

    async def apply_trade(self, wallet: Wallet, cash_delta: Decimal, fees: Decimal, trade_id: str, note: str) -> None:
        """Debit/credit the trade value and fees as two ledger rows."""
        wallet.balance += cash_delta
        txn_type = WalletTxnType.TRADE_CREDIT if cash_delta >= 0 else WalletTxnType.TRADE_DEBIT
        await self._record(wallet, txn_type, cash_delta, reference_id=trade_id, note=note)
        if fees:
            wallet.balance -= fees
            await self._record(wallet, WalletTxnType.FEE, -fees, reference_id=trade_id, note="Charges")

    async def _record(
        self,
        wallet: Wallet,
        txn_type: str,
        amount: Decimal,
        *,
        reference_id: str | None = None,
        note: str | None = None,
    ) -> None:
        await self.txns.add(
            WalletTransaction(
                wallet_id=wallet.id,
                type=txn_type,
                amount=amount.quantize(PAISE),
                balance_after=wallet.balance.quantize(PAISE),
                reference_id=reference_id,
                note=note,
            )
        )
