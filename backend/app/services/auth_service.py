"""Authentication use cases: register, login, refresh (with rotation), logout, change password."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import AuditAction, Role
from app.core.exceptions import AuthenticationError, Conflict, PermissionDenied
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories.risk_repo import RiskSettingsRepository
from app.repositories.user_repo import RefreshTokenRepository, UserRepository
from app.services.audit_service import AuditService
from app.services.wallet_service import WalletService

# Used to keep login timing similar whether or not the email exists.
_DUMMY_HASH = "$2b$12$S3tlti.fnd9DUj7poHazduvRMI.zQr8Pyf4atrXGZ648FYFRxgRc6"


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass
class ClientInfo:
    ip: str | None = None
    user_agent: str | None = None


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.tokens = RefreshTokenRepository(session)
        self.audit = AuditService(session)

    async def register(
        self, email: str, password: str, full_name: str, client: ClientInfo, role: Role = Role.USER
    ) -> User:
        email = email.lower()
        if await self.users.get_by_email(email):
            raise Conflict("An account with this email already exists", code="EMAIL_TAKEN")
        user = await self.users.add(
            User(email=email, password_hash=hash_password(password), full_name=full_name, role=role)
        )
        await WalletService(self.session).create_for_user(user.id)
        await RiskSettingsRepository(self.session).get_or_create(user.id)
        await self.audit.log(AuditAction.REGISTER, user_id=user.id, ip=client.ip, user_agent=client.user_agent)
        return user

    async def login(self, email: str, password: str, client: ClientInfo) -> tuple[User, TokenPair]:
        user = await self.users.get_by_email(email.lower())
        valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if not user or not valid:
            await self.audit.log(
                AuditAction.LOGIN_FAILED,
                user_id=user.id if user else None,
                ip=client.ip,
                user_agent=client.user_agent,
                details={"email": email},
            )
            raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise PermissionDenied("Account disabled. Contact an administrator.", code="ACCOUNT_DISABLED")
        user.last_login_at = datetime.now(UTC)
        pair = await self._issue(user)
        await self.audit.log(AuditAction.LOGIN, user_id=user.id, ip=client.ip, user_agent=client.user_agent)
        return user, pair

    async def refresh(self, refresh_token: str | None) -> TokenPair:
        """Rotate: the old refresh token is revoked and a new pair is issued.
        Re-use of a revoked token revokes every token for that user (theft detection)."""
        if not refresh_token:
            raise AuthenticationError("Missing refresh token")
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        stored = await self.tokens.get_by_jti(payload["jti"])
        if stored is None:
            raise AuthenticationError("Unknown refresh token")
        if stored.revoked_at is not None:
            await self.tokens.revoke_all_for_user(stored.user_id)
            raise AuthenticationError("Refresh token reuse detected; please log in again")
        user = await self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not available")
        stored.revoked_at = datetime.now(UTC)
        return await self._issue(user)

    async def logout(self, refresh_token: str | None, user_id: str | None, client: ClientInfo) -> None:
        if refresh_token:
            try:
                payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
                stored = await self.tokens.get_by_jti(payload["jti"])
                if stored and stored.revoked_at is None:
                    stored.revoked_at = datetime.now(UTC)
                    user_id = user_id or stored.user_id
            except AuthenticationError:
                pass
        await self.audit.log(AuditAction.LOGOUT, user_id=user_id, ip=client.ip, user_agent=client.user_agent)

    async def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise AuthenticationError("Current password is incorrect", code="INVALID_CREDENTIALS")
        user.password_hash = hash_password(new)
        await self.tokens.revoke_all_for_user(user.id)
        await self.audit.log(AuditAction.PASSWORD_CHANGE, user_id=user.id)

    async def ensure_admin(self, email: str | None, password: str | None) -> None:
        """Seed the first admin from env vars if configured and missing."""
        if not email or not password or await self.users.get_by_email(email):
            return
        await self.register(email, password, "Administrator", ClientInfo(ip="seed"), role=Role.ADMIN)

    async def _issue(self, user: User) -> TokenPair:
        access = create_access_token(user.id, user.role)
        refresh, jti, expires = create_refresh_token(user.id)
        await self.tokens.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires))
        return TokenPair(access, refresh)


def access_ttl_seconds() -> int:
    return get_settings().access_token_expire_minutes * 60
