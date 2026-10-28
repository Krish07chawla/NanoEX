"""Auth routes. Refresh token lives in an httpOnly cookie scoped to /api/v1/auth."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, client_info
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import ok
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth_service import AuthService, ClientInfo, TokenPair, access_ttl_seconds

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=_settings.cookie_secure,
        samesite="strict",
        max_age=_settings.refresh_token_expire_days * 86400,
        path=f"{_settings.api_prefix}/auth",
    )


def _token_body(pair: TokenPair, user: User | None = None) -> dict:
    body = TokenResponse(access_token=pair.access_token, expires_in=access_ttl_seconds()).model_dump()
    if user is not None:
        body["user"] = UserOut.model_validate(user).model_dump(mode="json")
    return body


@router.post("/register", status_code=201)
@limiter.limit(_settings.rate_limit_auth)
async def register(
    request: Request,
    body: RegisterRequest,
    session: AsyncSession = SessionDep,
    client: ClientInfo = Depends(client_info),
):
    user = await AuthService(session).register(body.email, body.password, body.full_name, client)
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/login")
@limiter.limit(_settings.rate_limit_auth)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: AsyncSession = SessionDep,
    client: ClientInfo = Depends(client_info),
):
    user, pair = await AuthService(session).login(body.email, body.password, client)
    _set_refresh_cookie(response, pair.refresh_token)
    return ok(_token_body(pair, user))


@router.post("/refresh")
async def refresh(request: Request, response: Response, session: AsyncSession = SessionDep):
    token = request.cookies.get(_settings.refresh_cookie_name)
    pair = await AuthService(session).refresh(token)
    _set_refresh_cookie(response, pair.refresh_token)
    return ok(_token_body(pair))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = SessionDep,
    client: ClientInfo = Depends(client_info),
):
    token = request.cookies.get(_settings.refresh_cookie_name)
    await AuthService(session).logout(token, None, client)
    response.delete_cookie(_settings.refresh_cookie_name, path=f"{_settings.api_prefix}/auth")
    return ok({"logged_out": True})


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, user: User = CurrentUser, session: AsyncSession = SessionDep):
    await AuthService(session).change_password(user, body.current_password, body.new_password)
    return ok({"changed": True})
