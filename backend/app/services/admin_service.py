"""Admin: user management and system metrics."""

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.event_bus import Topics
from app.core.exceptions import NotFound, ValidationFailed
from app.core.metrics import metrics
from app.models.order import Order
from app.models.trade import Trade
from app.models.user import User
from app.models.wallet import Wallet
from app.repositories.user_repo import RefreshTokenRepository, UserRepository
from app.schemas.user import AdminUserUpdate
from app.services.audit_service import AuditService

if TYPE_CHECKING:
    from app.container import Container


class AdminService:
    def __init__(self, session: AsyncSession, container: "Container"):
        self.session = session
        self.c = container
        self.users = UserRepository(session)

    async def list_users(self, offset: int, limit: int) -> tuple[list[dict], int]:
        stmt = select(User, Wallet).join(Wallet, Wallet.user_id == User.id).order_by(User.created_at.desc())
        total = int((await self.session.execute(select(func.count(User.id)))).scalar_one())
        rows = (await self.session.execute(stmt.offset(offset).limit(limit))).all()
        data = [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "balance": float(w.balance),
                "capital_added": float(w.capital_added),
            }
            for u, w in rows
        ]
        return data, total

    async def update_user(self, admin: User, user_id: str, body: AdminUserUpdate) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFound("User not found")
        if user.id == admin.id and body.is_active is False:
            raise ValidationFailed("You cannot disable your own account")
        if body.is_active is not None:
            user.is_active = body.is_active
            if not body.is_active:
                await RefreshTokenRepository(self.session).revoke_all_for_user(user.id)
        if body.role is not None:
            user.role = body.role
        await AuditService(self.session).log(
            AuditAction.ADMIN_ACTION,
            user_id=admin.id,
            entity="user",
            entity_id=user.id,
            details=body.model_dump(exclude_none=True),
        )
        await self.session.flush()
        return user

    async def system_metrics(self) -> dict:
        async def count(model) -> int:
            return int((await self.session.execute(select(func.count(model.id)))).scalar_one())

        return {
            **metrics.snapshot(),
            "users": await count(User),
            "orders": await count(Order),
            "trades": await count(Trade),
            "active_bots": len(self.c.bot_runner.bots),
            "ws_market_clients": self.c.bus.subscriber_count(Topics.ARB_OPPORTUNITY),
            "market_provider": self.c.market.provider.name,
            "market_running": self.c.market.running,
        }
