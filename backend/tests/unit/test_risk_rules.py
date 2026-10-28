from dataclasses import replace
from decimal import Decimal as D

import pytest

from app.core.constants import Side
from app.core.exceptions import InsufficientFunds, RiskLimitExceeded
from app.engine.risk import RiskContext, RiskManager

BASE = RiskContext(
    side=Side.BUY,
    quantity=10,
    price=D("100"),
    est_fees=D("1"),
    available_funds=D("100000"),
    position_qty=0,
    open_orders=0,
    day_volume=D("0"),
    day_pnl=D("0"),
    kill_switch=False,
    max_order_qty=100,
    max_order_notional=D("5000"),
    max_position_value=D("8000"),
    daily_loss_limit=D("1000"),
    daily_volume_cap=D("50000"),
    max_open_orders=5,
)
rm = RiskManager()


def test_passes_when_within_limits():
    rm.check(BASE)


@pytest.mark.parametrize(
    "change,rule",
    [
        ({"kill_switch": True}, "kill_switch"),
        ({"quantity": 101}, "max_order_qty"),
        ({"quantity": 60}, "max_order_notional"),
        ({"open_orders": 5}, "max_open_orders"),
        ({"position_qty": 75}, "max_position_value"),
        ({"day_pnl": D("-1000")}, "daily_loss_limit"),
        ({"day_volume": D("49500")}, "daily_volume_cap"),
    ],
)
def test_each_rule_rejects(change, rule):
    with pytest.raises(RiskLimitExceeded) as exc:
        rm.check(replace(BASE, **change))
    assert exc.value.details["rule"] == rule


def test_insufficient_funds_for_buy():
    with pytest.raises(InsufficientFunds):
        rm.check(replace(BASE, available_funds=D("500")))


def test_closing_a_long_needs_no_funds():
    rm.check(replace(BASE, side=Side.SELL, position_qty=10, available_funds=D("0"), est_fees=D("0")))


def test_short_sale_needs_margin():
    with pytest.raises(InsufficientFunds):
        rm.check(replace(BASE, side=Side.SELL, available_funds=D("100")))  # needs 20% of 1000 + fees
    rm.check(replace(BASE, side=Side.SELL, available_funds=D("201")))


def test_exits_allowed_after_daily_loss():
    rm.check(replace(BASE, side=Side.SELL, position_qty=10, day_pnl=D("-5000")))
