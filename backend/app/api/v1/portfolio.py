import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, get_container
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.responses import ok
from app.models.user import User
from app.repositories.order_repo import TradeRepository
from app.schemas.order import TradeOut
from app.services.portfolio_service import TRADE_CSV_HEADER, PortfolioService, trade_row

router = APIRouter(tags=["portfolio"])
CSV_EXPORT_LIMIT = 50_000


@router.get("/portfolio/summary")
async def summary(user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok(await PortfolioService(session, c).summary(user.id))


@router.get("/portfolio/positions")
async def positions(
    include_closed: bool = False, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(await PortfolioService(session, c).positions_view(user.id, open_only=not include_closed))


@router.get("/portfolio/equity-curve")
async def equity_curve(user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok(await PortfolioService(session, c).equity_curve(user.id))


@router.get("/dashboard/profit")
async def profit_dashboard(user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok(await PortfolioService(session, c).profit_dashboard(user.id))


def _filters(user_id: str, repo: TradeRepository, symbol, side, source, exchange, start, end):
    return repo.for_user(user_id, symbol.upper() if symbol else None, side, source, exchange, start, end)


@router.get("/trades")
async def list_trades(
    symbol: str | None = None,
    side: str | None = None,
    source: str | None = None,
    exchange: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    repo = TradeRepository(session)
    items, total = await repo.page(_filters(user.id, repo, symbol, side, source, exchange, start, end), page, size)
    return ok(
        [TradeOut.model_validate(t).model_dump(mode="json") for t in items],
        meta={"total": total, "page": page, "size": size},
    )


@router.get("/trades/export.csv")
async def export_trades(
    symbol: str | None = None,
    side: str | None = None,
    source: str | None = None,
    exchange: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    repo = TradeRepository(session)
    trades = await repo.list(
        _filters(user.id, repo, symbol, side, source, exchange, start, end), limit=CSV_EXPORT_LIMIT
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TRADE_CSV_HEADER)
    writer.writerows(trade_row(t) for t in trades)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nanoex_trades.csv"},
    )
