from datetime import datetime

from sqlalchemy import func, select

from app.models.wallet import Wallet, WalletTransaction
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    model = Wallet

    async def get_by_user(self, user_id: str) -> Wallet | None:
        result = await self.session.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()


class WalletTransactionRepository(BaseRepository[WalletTransaction]):
    model = WalletTransaction

    def for_wallet(self, wallet_id: str, txn_type: str | None = None):
        stmt = select(WalletTransaction).where(WalletTransaction.wallet_id == wallet_id)
        if txn_type:
            stmt = stmt.where(WalletTransaction.type == txn_type)
        return stmt.order_by(WalletTransaction.created_at.desc())

    async def count_since(self, wallet_id: str, txn_type: str, since: datetime) -> int:
        stmt = select(func.count()).where(
            WalletTransaction.wallet_id == wallet_id,
            WalletTransaction.type == txn_type,
            WalletTransaction.created_at >= since,
        )
        return int((await self.session.execute(stmt)).scalar_one())
