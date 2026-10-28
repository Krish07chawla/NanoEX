from decimal import Decimal as D

from app.core.constants import Side
from app.services.position_math import apply_fill


def test_open_and_add_long_averages_price():
    q, avg, r = apply_fill(0, D("0"), Side.BUY, D("100"), 10)
    q, avg, r = apply_fill(q, avg, Side.BUY, D("110"), 10)
    assert (q, avg, r) == (20, D("105"), 0)


def test_partial_close_realizes_pnl():
    q, avg, r = apply_fill(20, D("105"), Side.SELL, D("115"), 5)
    assert (q, avg, r) == (15, D("105"), D("50"))


def test_full_close_resets_avg():
    assert apply_fill(10, D("100"), Side.SELL, D("90"), 10) == (0, D("0"), D("-100"))


def test_short_then_cover():
    q, avg, r = apply_fill(0, D("0"), Side.SELL, D("100"), 10)
    assert q == -10 and avg == D("100")
    assert apply_fill(q, avg, Side.BUY, D("95"), 10) == (0, D("0"), D("50"))


def test_flip_long_to_short():
    q, avg, r = apply_fill(5, D("100"), Side.SELL, D("110"), 8)
    assert (q, avg, r) == (-3, D("110"), D("50"))


def test_arbitrage_buy_one_exchange_sell_other_nets_flat():
    q, avg, _ = apply_fill(0, D("0"), Side.BUY, D("4100.05"), 100)  # buy NSE
    q, avg, r = apply_fill(q, avg, Side.SELL, D("4110"), 100)  # sell BSE
    assert q == 0 and r == D("995.00")
