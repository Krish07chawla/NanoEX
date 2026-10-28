from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.core.metrics import metrics
from app.core.responses import ok
from app.db.session import session_factory

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(request: Request):
    db_ok = True
    try:
        async with session_factory()() as session:
            await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - health must never raise
        db_ok = False
    container = getattr(request.app.state, "container", None)
    market_ok = bool(container and container.market.running)
    status = "ok" if db_ok and market_ok else "degraded"
    return ok(
        {
            "status": status,
            "database": db_ok,
            "market_stream": market_ok,
            "uptime_seconds": metrics.snapshot()["uptime_seconds"],
        }
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    return metrics.prometheus()
