from decimal import Decimal as D

import pytest

from app.arbitrage.cost_model import CostModel
from app.arbitrage.detector import ArbitrageDetector, Confidence, quote_spread
from app.core.constants import OrderType, Side
from app.engine.order import BookOrder
from app.engine.order_book import OrderBook
from app.market.providers.base import Quote

detector = ArbitrageDetector(CostModel())


def make_book(exchange: str, bid: str, ask: str, qty: int = 500) -> OrderBook:
    book = OrderBook("TCS", exchange)
    book.submit(BookOrder(f"{exchange}-b", Side.BUY, OrderType.LIMIT, qty, price=D(bid)))
    book.submit(BookOrder(f"{exchange}-a", Side.SELL, OrderType.LIMIT, qty, price=D(ask)))
    return book


def books(nse_bid, nse_ask, bse_bid, bse_ask, qty=500):
    return {"NSE": make_book("NSE", nse_bid, nse_ask, qty), "BSE": make_book("BSE", bse_bid, bse_ask, qty)}


def test_zero_spread_is_not_an_opportunity():
    opp = detector.evaluate("TCS", books("4100", "4100.05", "4100", "4100.05"), 100)
    assert opp.net_profit < 0 and not opp.is_actionable(D("0"))
    assert opp.confidence == Confidence.LOW


def test_spread_smaller_than_costs():
    # Rs 1.00/share edge = Rs 100 gross, but two legs of ~Rs 4.1L cost ~Rs 270
    opp = detector.evaluate("TCS", books("4100", "4100.05", "4101.05", "4101.10"), 100)
    assert opp.gross_profit == D("100.00")
    assert opp.net_profit < 0
    assert not opp.is_actionable(D("0"))


def test_profitable_opportunity_buys_cheap_sells_dear():
    opp = detector.evaluate("TCS", books("4100", "4100.05", "4110", "4110.05"), 100)
    assert (opp.buy_exchange, opp.sell_exchange) == ("NSE", "BSE")
    assert opp.buy_price == D("4100.05") and opp.sell_price == D("4110")
    assert opp.net_profit == opp.gross_profit - opp.costs.total
    assert opp.is_actionable(D("50")) and opp.confidence == Confidence.HIGH


def test_reverse_direction_when_bse_cheaper():
    opp = detector.evaluate("TCS", books("4110", "4110.05", "4100", "4100.05"), 100)
    assert (opp.buy_exchange, opp.sell_exchange) == ("BSE", "NSE")


def test_threshold_respected():
    opp = detector.evaluate("TCS", books("4100", "4100.05", "4110", "4110.05"), 100)
    assert not opp.is_actionable(opp.net_profit + 1)


def test_insufficient_liquidity_flags_opportunity():
    opp = detector.evaluate("TCS", books("4100", "4100.05", "4110", "4110.05", qty=40), 100)
    assert opp.max_qty == 40 and not opp.liquidity_ok
    assert not opp.is_actionable(D("0"))


def test_empty_book_returns_none():
    empty = {"NSE": OrderBook("TCS", "NSE"), "BSE": OrderBook("TCS", "BSE")}
    assert detector.evaluate("TCS", empty, 100) is None


def test_invalid_quantity():
    with pytest.raises(ValueError):
        detector.evaluate("TCS", books("1", "2", "1", "2"), 0)


def test_quote_spread_is_bse_minus_nse():
    nse = Quote("TCS", "NSE", D("99.95"), D("100.05"), D("100"), 1, 1.0)
    bse = Quote("TCS", "BSE", D("100.45"), D("100.55"), D("100.5"), 1, 2.0)
    s = quote_spread(nse, bse)
    assert s["spread_abs"] == 0.5 and s["spread_pct"] == 0.5


def test_to_dict_has_table_fields():
    d = detector.evaluate("TCS", books("4100", "4100.05", "4110", "4110.05"), 100).to_dict()
    for key in ("symbol", "buy_exchange", "sell_exchange", "spread_abs", "est_costs", "est_net_profit", "confidence"):
        assert key in d
