"""NanoEX Web - FastAPI application factory."""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1 import ws
from app.api.v1.router import api_router
from app.api.v1.system import router as system_router
from app.container import Container
from app.core.config import Settings, get_settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.responses import fail
from app.db.session import create_all, session_factory
from app.market.providers.base import MarketDataProvider
from app.services.auth_service import AuthService

log = get_logger(__name__)


def create_app(
    settings: Settings | None = None, provider: MarketDataProvider | None = None, background: bool = True
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.debug)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_create_tables:
            await create_all()
        async with session_factory()() as session:
            await AuthService(session).ensure_admin(settings.admin_email, settings.admin_password)
            await session.commit()
        container = Container(settings, provider)
        app.state.container = container
        await container.start(background=background)
        log.info("startup_complete", provider=container.market.provider.name)
        yield
        await container.stop()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        description="Educational paper-trading HFT simulator for NSE/BSE. No real orders are placed.",
    )
    app.state.limiter = limiter
    limiter.enabled = settings.rate_limit_auth != "off"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        structlog.contextvars.clear_contextvars()
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content=fail(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content=fail("VALIDATION_ERROR", "Invalid input", {"errors": errors}))

    @app.exception_handler(RateLimitExceeded)
    async def rate_limited(_: Request, exc: RateLimitExceeded):
        return JSONResponse(status_code=429, content=fail("RATE_LIMITED", f"Too many requests: {exc.detail}"))

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("unhandled_error", error=str(exc))
        return JSONResponse(status_code=500, content=fail("INTERNAL_ERROR", "Something went wrong"))

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(system_router)  # also expose /health and /metrics at the root
    app.include_router(ws.router)
    return app


app = create_app()
