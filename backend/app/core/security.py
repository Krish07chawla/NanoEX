"""Password hashing (bcrypt) and JWT creation/validation."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    """Hash a password with bcrypt and a per-password salt."""
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time comparison of a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _create_token(
    subject: str, token_type: str, expires: timedelta, extra: dict[str, Any]
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    exp = now + expires
    payload = {"sub": subject, "type": token_type, "jti": jti, "iat": now, "exp": exp, **extra}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, exp


def create_access_token(user_id: str, role: str) -> str:
    """Short-lived token sent in the Authorization header."""
    minutes = get_settings().access_token_expire_minutes
    token, _, _ = _create_token(user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=minutes), {"role": role})
    return token


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Long-lived token stored in an httpOnly cookie. Returns (token, jti, expires_at)."""
    days = get_settings().refresh_token_expire_days
    return _create_token(user_id, REFRESH_TOKEN_TYPE, timedelta(days=days), {})


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising AuthenticationError on any problem."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Wrong token type")
    return payload
