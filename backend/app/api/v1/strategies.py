from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, get_container
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.exceptions import NotFound
from app.core.responses import ok
from app.models.user import User
from app.repositories.strategy_repo import BacktestRepository
from app.schemas.strategy import BacktestRequest, StrategyConfigIn, StrategyConfigOut
from app.services.strategy_service import StrategyService
from app.strategies.factory import StrategyFactory

router = APIRouter(tags=["strategies"])


def _out(cfg, c) -> dict:
    data = StrategyConfigOut.model_validate(cfg).model_dump(mode="json")
    data["runtime"] = c.bot_runner.status(cfg.id)
    return data


@router.get("/strategies/types")
async def strategy_types(_: User = CurrentUser):
    return ok(StrategyFactory.available())


@router.get("/strategies")
async def list_strategies(user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)):
    return ok([_out(s, c) for s in await StrategyService(session, c).list(user.id)])


@router.post("/strategies", status_code=201)
async def create_strategy(
    body: StrategyConfigIn, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(_out(await StrategyService(session, c).create(user.id, body), c))


@router.put("/strategies/{config_id}")
async def update_strategy(
    config_id: str,
    body: StrategyConfigIn,
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
    c=Depends(get_container),
):
    return ok(_out(await StrategyService(session, c).update(user.id, config_id, body), c))


@router.delete("/strategies/{config_id}")
async def delete_strategy(
    config_id: str, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    await StrategyService(session, c).delete(user.id, config_id)
    return ok({"deleted": True})


@router.post("/strategies/{config_id}/start")
async def start_strategy(
    config_id: str, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(_out(await StrategyService(session, c).set_active(user.id, config_id, True), c))


@router.post("/strategies/{config_id}/stop")
async def stop_strategy(
    config_id: str, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(_out(await StrategyService(session, c).set_active(user.id, config_id, False), c))


@router.post("/backtests", status_code=201)
async def run_backtest(
    body: BacktestRequest, user: User = CurrentUser, session: AsyncSession = SessionDep, c=Depends(get_container)
):
    return ok(await StrategyService(session, c).backtest(user.id, body))


@router.get("/backtests")
async def list_backtests(
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = CurrentUser,
    session: AsyncSession = SessionDep,
):
    repo = BacktestRepository(session)
    items, total = await repo.page(repo.for_user(user.id), page, size)
    data = [
        {
            "id": b.id,
            "strategy_type": b.strategy_type,
            "symbol": b.symbol,
            "params": b.params,
            "data_source": b.data_source,
            "bars": b.bars,
            "seed": b.seed,
            "metrics": b.metrics,
            "created_at": b.created_at.isoformat(),
        }
        for b in items
    ]
    return ok(data, meta={"total": total, "page": page, "size": size})


@router.get("/backtests/{backtest_id}")
async def get_backtest(backtest_id: str, user: User = CurrentUser, session: AsyncSession = SessionDep):
    b = await BacktestRepository(session).get(backtest_id)
    if b is None or b.user_id != user.id:
        raise NotFound("Backtest not found")
    return ok(
        {
            "id": b.id,
            "strategy_type": b.strategy_type,
            "symbol": b.symbol,
            "params": b.params,
            "metrics": b.metrics,
            "equity_curve": b.equity_curve,
            "trades": b.trades,
            "created_at": b.created_at.isoformat(),
        }
    )
