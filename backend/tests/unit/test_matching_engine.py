import time
from decimal import Decimal as D

from app.core.constants import OrderType, Side
from app.engine.matching_engine import MatchingEngine
from app.engine.order import BookOrder
from app.market.providers.base import Quote


def quote(last: str, half: str = "0.05") -> Quote:
    p, h = D(last), D(half)
    return Quote("SBIN", "NSE", p - h, p + h, p, 100, time.time())


async def test_requote_seeds_both_sides():
    engine = MatchingEngine(depth_levels=5, seed=1)
    await engine.on_quotes([quote("820")])
    depth = engine.depth("SBIN", "NSE", 10)
    assert len(depth["bids"]) == 5 and len(depth["asks"]) == 5
    assert depth["bids"][0]["price"] == 819.95 and depth["asks"][0]["price"] == 820.05


async def test_resting_user_order_fills_when_market_moves():
    engine = MatchingEngine(depth_levels=3, seed=1)
    captured = []

    async def handler(fills):
        captured.extend(fills)

    engine.fill_handler = handler
    await engine.on_quotes([quote("820")])
    await engine.submit("SBIN", "NSE", BookOrder("u-b1", Side.BUY, OrderType.LIMIT, 5, price=D("815"), user_id="u"))
    await engine.on_quotes([quote("814")])  # market falls through the user's bid
    assert captured and captured[0].maker_order_id == "u-b1"
    assert captured[0].price == D("815")


async def test_cancel_and_restore():
    engine = MatchingEngine(depth_levels=1, seed=1)
    order = BookOrder("u1", Side.SELL, OrderType.LIMIT, 3, price=D("900"), user_id="u")
    await engine.restore("SBIN", "NSE", order)
    assert (await engine.cancel("SBIN", "NSE", "u1")).order_id == "u1"
    assert await engine.cancel("SBIN", "NSE", "u1") is None
