from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.core.metrics import metrics
from app.core.responses import ok

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/performance")
async def performance(_=CurrentUser):
    """Orders/sec, average order latency, tick-to-trade latency and uptime for the dashboard cards."""
    return ok(metrics.snapshot())
