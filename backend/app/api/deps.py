"""FastAPI dependencies: DB session, current user, admin guard, client info."""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Role
from app.core.exceptions import AuthenticationError, PermissionDenied
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import ClientInfo

bearer = HTTPBearer(auto_error=False)

SessionDep = Depends(get_session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = SessionDep,
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    payload = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)
    user = await UserRepository(session).get(payload["sub"])
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or disabled")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise PermissionDenied("Admin access required")
    return user


def client_info(request: Request) -> ClientInfo:
    ip = request.client.host if request.client else None
    return ClientInfo(ip=ip, user_agent=request.headers.get("user-agent"))


def get_container(request: Request):
    """The app-wide service container (market, engine, bots) built at startup."""
    return request.app.state.container


CurrentUser = Depends(get_current_user)
AdminUser = Depends(require_admin)
