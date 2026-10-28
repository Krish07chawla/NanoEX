"""Consistent API response envelope: {success, data, error, meta}."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] | None = None


def ok(data: Any = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a success envelope."""
    return {"success": True, "data": data, "error": None, "meta": meta}


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an error envelope."""
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details or {}},
        "meta": None,
    }
