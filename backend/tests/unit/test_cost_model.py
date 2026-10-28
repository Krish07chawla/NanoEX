from decimal import Decimal as D

from app.arbitrage.cost_model import ChargeSchedule, CostModel
from app.core.constants import Side

cm = CostModel()


def test_buy_leg_has_stamp_no_stt():
    c = cm.leg_costs(Side.BUY, "NSE", D("1000"), 100)  # turnover 1,00,000
    assert c.stt == 0 and c.stamp == D("3.00")
    assert c.brokerage == D("20.00")  # flat 20 < 0.03% of 1L (30)
    assert c.exchange_txn == D("2.97")
    assert c.gst == ((c.brokerage + c.exchange_txn + c.sebi) * D("0.18")).quantize(D("0.01"))


def test_sell_leg_has_stt_no_stamp():
    c = cm.leg_costs(Side.SELL, "BSE", D("1000"), 100)
    assert c.stt == D("25.00") and c.stamp == 0
    assert c.exchange_txn == D("3.75")


def test_brokerage_cap_on_small_orders():
    c = cm.leg_costs(Side.BUY, "NSE", D("100"), 10)  # turnover 1000 -> 0.03% = 0.30
    assert c.brokerage == D("0.30")


def test_zero_quantity_costs_nothing():
    assert cm.leg_costs(Side.BUY, "NSE", D("100"), 0).total == 0


def test_slippage_only_when_requested():
    assert cm.leg_costs(Side.BUY, "NSE", D("1000"), 100).slippage == 0
    assert cm.leg_costs(Side.BUY, "NSE", D("1000"), 100, include_slippage=True).slippage == D("10.00")


def test_round_trip_sums_both_legs():
    rt = cm.round_trip("NSE", D("1000"), "BSE", D("1001"), 100, include_slippage=False)
    buy = cm.leg_costs(Side.BUY, "NSE", D("1000"), 100)
    sell = cm.leg_costs(Side.SELL, "BSE", D("1001"), 100)
    assert rt.total == buy.total + sell.total
    assert set(rt.to_dict()) >= {"brokerage", "stt", "gst", "stamp", "total"}


def test_custom_schedule():
    free = CostModel(ChargeSchedule(brokerage_flat=D("0"), brokerage_pct=D("0")))
    assert free.leg_costs(Side.BUY, "NSE", D("1000"), 100).brokerage == 0
