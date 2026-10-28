from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, get_container
from app.arbitrage.executor import arb_to_dict
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ArbMode
from app.core.exceptions import ValidationFailed
from app.core.responses import ok
from app.models.user import User
from app.repositories.arbitrage_repo import ArbitrageOpportunityRepository, ArbitrageTradeRepository
from app.schemas.risk import ArbAutoRequest, ArbExecuteRequest
from app.services.arbitrage_service import ArbitrageStatsService
from app.services.risk_service import RiskService

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])

INFO_NOTE = (
    "Educational simulation. Real NSE-BSE arbitrage is dominated by low-latency firms with co-located "
    "servers; real spreads are usually a few paise and vanish in microseconds, so retail traders rarely "
    "capture them after costs."
)


@router.get("/spreads")
async def spreads(_: User = CurrentUser, c=Depends(get_container)):
    return ok(list(c.arb_scanner.board.values()), meta={"note": INFO_NOTE})


@router.get("/opportunities")
async def opportunities(
    live: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
    c=Depends(get_container),
):
    """live=true: best current opportunity per symbol at the user's quantity; live=false: logged history."""
    if live:
        limits = await RiskService(session, c).get(user.id)
        rows = []
        for symbol in c.market.symbols():
            opp = c.arb_scanner.evaluate(symbol, limits.arb_quantity)
            if opp:
                rows.append({**opp.to_dict(), "actionable": opp.is_actionable(limits.arb_min_profit)})
        rows.sort(key=lambda r: r["est_net_profit"], reverse=True)
        return ok(rows, meta={"min_profit": float(limits.arb_min_profit), "quantity": limits.arb_quantity})
    repo = ArbitrageOpportunityRepository(session)
    items, total = await repo.page(repo.recent(), page, size)
    data = [
        {
            "id": o.id,
            "symbol": o.symbol,
            "buy_exchange": o.buy_exchange,
            "sell_exchange": o.sell_exchange,
            "buy_price": float(o.buy_price),
            "sell_price": float(o.sell_price),
            "spread_abs": float(o.spread_abs),
            "spread_pct": float(o.spread_pct),
            "quantity": o.quantity,
            "est_costs": float(o.est_costs),
            "est_net_profit": float(o.est_net_profit),
            "detected_at": o.detected_at.isoformat(),
        }
        for o in items
    ]
    return ok(data, meta={"total": total, "page": page, "size": size})


@router.post("/execute")
async def execute(
    body: ArbExecuteRequest, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    symbol = body.symbol.upper()
    if symbol not in c.market.symbols():
        raise ValidationFailed(f"Unknown symbol {symbol}")
    limits = await RiskService(session, c).get(user.id)
    record = await c.arb_executor.execute(
        session,
        user.id,
        symbol,
        body.quantity or limits.arb_quantity,
        ArbMode.MANUAL,
        opportunity_id=body.opportunity_id,
    )
    return ok(arb_to_dict(record))


@router.put("/auto")
async def set_auto(
    body: ArbAutoRequest, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    from app.schemas.risk import RiskSettingsUpdate

    settings = await RiskService(session, c).get(user.id)
    if body.enabled and settings.kill_switch:
        raise ValidationFailed("Turn off the kill switch before enabling auto mode")
    update = RiskSettingsUpdate(
        arb_auto_enabled=body.enabled, arb_min_profit=body.min_profit, arb_quantity=body.quantity
    )
    s = await RiskService(session, c).update(user.id, update)
    return ok({"enabled": s.arb_auto_enabled, "min_profit": float(s.arb_min_profit), "quantity": s.arb_quantity})


@router.get("/trades")
async def trades(
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    repo = ArbitrageTradeRepository(session)
    items, total = await repo.page(repo.for_user(user.id), page, size)
    return ok([arb_to_dict(t) for t in items], meta={"total": total, "page": page, "size": size})


@router.get("/stats")
async def stats(user: User = CurrentUser, session: AsyncSession = SessionDep):
    return ok(await ArbitrageStatsService(session).stats(user.id), meta={"note": INFO_NOTE})
