from decimal import Decimal as D

import pytest

from app.core.constants import OrderType, Side
from app.engine.order import BookOrder
from app.engine.order_book import OrderBook


def limit(oid, side, qty, price, user="u1"):
    return BookOrder(oid, side, OrderType.LIMIT, qty, price=D(price), user_id=user)


def market(oid, side, qty, user="u9"):
    return BookOrder(oid, side, OrderType.MARKET, qty, user_id=user)


@pytest.fixture
def book():
    return OrderBook("TCS", "NSE")


def test_limit_order_rests_when_not_crossing(book):
    r = book.submit(limit("b1", Side.BUY, 10, "100"))
    assert r.resting and not r.fills
    assert book.best_bid() == D("100") and book.best_ask() is None


def test_price_priority_best_price_fills_first(book):
    book.submit(limit("a1", Side.SELL, 5, "101", "m1"))
    book.submit(limit("a2", Side.SELL, 5, "100", "m2"))
    r = book.submit(market("t", Side.BUY, 5))
    assert [f.maker_order_id for f in r.fills] == ["a2"]
    assert r.fills[0].price == D("100")


def test_time_priority_at_same_price(book):
    book.submit(limit("a1", Side.SELL, 5, "100", "m1"))
    book.submit(limit("a2", Side.SELL, 5, "100", "m2"))
    r = book.submit(market("t", Side.BUY, 7))
    assert [(f.maker_order_id, f.quantity) for f in r.fills] == [("a1", 5), ("a2", 2)]
    assert book.get("a2").remaining == 3


def test_partial_fill_then_rest(book):
    book.submit(limit("a1", Side.SELL, 4, "100", "m1"))
    r = book.submit(limit("b1", Side.BUY, 10, "100.5"))
    assert r.filled_qty == 4 and r.remaining == 6 and r.resting
    assert book.best_bid() == D("100.5")


def test_trade_executes_at_resting_price(book):
    book.submit(limit("a1", Side.SELL, 4, "99", "m1"))
    r = book.submit(limit("b1", Side.BUY, 4, "101"))
    assert r.fills[0].price == D("99")


def test_market_order_remainder_is_dropped(book):
    book.submit(limit("a1", Side.SELL, 3, "100", "m1"))
    r = book.submit(market("t", Side.BUY, 10))
    assert r.filled_qty == 3 and r.remaining == 7 and not r.resting
    assert len(book) == 0


def test_market_order_on_empty_book(book):
    r = book.submit(market("t", Side.SELL, 5))
    assert r.filled_qty == 0 and not r.resting


def test_cancel_removes_order_and_level(book):
    book.submit(limit("b1", Side.BUY, 10, "100"))
    assert book.cancel("b1").order_id == "b1"
    assert book.best_bid() is None
    assert book.cancel("b1") is None


def test_self_trade_prevention_cancels_resting(book):
    book.submit(limit("a1", Side.SELL, 5, "100", "same"))
    book.submit(limit("a2", Side.SELL, 5, "100.5", "other"))
    r = book.submit(market("t", Side.BUY, 5, user="same"))
    assert r.cancelled_ids == ["a1"]
    assert r.fills[0].maker_order_id == "a2"


def test_depth_aggregates_levels(book):
    book.submit(limit("b1", Side.BUY, 5, "99"))
    book.submit(limit("b2", Side.BUY, 7, "99"))
    book.submit(limit("b3", Side.BUY, 1, "98"))
    book.submit(limit("a1", Side.SELL, 2, "101", "m"))
    d = book.depth(10)
    assert d["bids"][0] == {"price": 99.0, "quantity": 12, "orders": 2}
    assert d["bids"][1]["price"] == 98.0 and d["asks"][0]["price"] == 101.0


def test_sweep_vwap_walks_levels(book):
    book.submit(limit("a1", Side.SELL, 10, "100", "m"))
    book.submit(limit("a2", Side.SELL, 10, "102", "m"))
    vwap, qty = book.sweep_vwap(Side.BUY, 15)
    assert qty == 15 and vwap == (D("100") * 10 + D("102") * 5) / 15
    vwap, qty = book.sweep_vwap(Side.BUY, 50)
    assert qty == 20
    assert book.sweep_vwap(Side.SELL, 5) == (None, 0)


def test_remove_makers_keeps_user_orders(book):
    book.submit(BookOrder("mk-1", Side.BUY, OrderType.LIMIT, 5, price=D("99")))
    book.submit(limit("b1", Side.BUY, 5, "98"))
    book.remove_makers()
    assert book.get("mk-1") is None and book.get("b1") is not None


@pytest.mark.parametrize("kwargs", [{"quantity": 0}, {"quantity": -1}])
def test_invalid_quantity(kwargs):
    with pytest.raises(ValueError):
        BookOrder("x", Side.BUY, OrderType.MARKET, **kwargs)


def test_limit_needs_price():
    with pytest.raises(ValueError):
        BookOrder("x", Side.BUY, OrderType.LIMIT, 1)


def test_duplicate_order_id_rejected(book):
    book.submit(limit("b1", Side.BUY, 1, "100"))
    with pytest.raises(ValueError):
        book.submit(limit("b1", Side.BUY, 1, "100"))
