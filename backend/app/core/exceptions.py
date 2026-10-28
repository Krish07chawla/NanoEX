"""Custom exception hierarchy. Services raise these; one handler maps them to HTTP."""


class DomainError(Exception):
    """Base class for all expected business errors."""

    status_code: int = 400
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ValidationFailed(DomainError):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthenticationError(DomainError):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class PermissionDenied(DomainError):
    status_code = 403
    code = "PERMISSION_DENIED"


class NotFound(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class Conflict(DomainError):
    status_code = 409
    code = "CONFLICT"


class InsufficientFunds(DomainError):
    status_code = 400
    code = "INSUFFICIENT_FUNDS"


class RiskLimitExceeded(DomainError):
    status_code = 400
    code = "RISK_LIMIT_EXCEEDED"


class MarketUnavailable(DomainError):
    status_code = 503
    code = "MARKET_UNAVAILABLE"
