from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_container
from app.core.constants import SYMBOL_UNIVERSE, Exchange
from app.core.exceptions import NotFound
from app.core.responses import ok

router = APIRouter(prefix="/market", tags=["market"], dependencies=[CurrentUser])


@router.get("/symbols")
async def symbols(c=Depends(get_container)):
    return ok(
        [{"symbol": s, "exchanges": [e.value for e in Exchange]} for s in c.market.symbols()],
        meta={"provider": c.market.provider.name, "realtime": c.market.provider.is_realtime},
    )


@router.get("/quotes")
async def quotes(c=Depends(get_container)):
    return ok([q.to_dict() for q in c.market.quotes()])


@router.get("/{symbol}/history")
async def history(
    symbol: str, exchange: Exchange = Exchange.NSE, limit: int = Query(300, ge=1, le=5000), c=Depends(get_container)
):
    symbol = symbol.upper()
    if symbol not in SYMBOL_UNIVERSE and symbol not in c.market.symbols():
        raise NotFound(f"Unknown symbol {symbol}")
    return ok(c.market.history(symbol, exchange.value, limit))


@router.get("/{symbol}/{exchange}/depth")
async def depth(symbol: str, exchange: Exchange, levels: int = Query(10, ge=1, le=50), c=Depends(get_container)):
    symbol = symbol.upper()
    if symbol not in c.market.symbols():
        raise NotFound(f"Unknown symbol {symbol}")
    return ok(c.engine.depth(symbol, exchange.value, levels))
