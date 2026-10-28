import pytest

from app.strategies import Action, StrategyFactory
from app.strategies.exits import ExitRules, PositionTracker
from app.strategies.trader import StrategyTrader

ALL = [
    "momentum",
    "mean_reversion",
    "bollinger",
    "rsi_reversal",
    "breakout",
    "macd_crossover",
    "ema_crossover",
    "zscore",
    "ensemble",
]


def run(key, prices, **params):
    s = StrategyFactory.create(key, params)
    return [s.update(p) for p in prices]


def actions(signals):
    return {s.action for s in signals}


def test_factory_lists_all_nine():
    assert sorted(StrategyFactory.keys()) == sorted(ALL)
    assert all("params" in d for d in StrategyFactory.available())


def test_unknown_strategy():
    with pytest.raises(ValueError):
        StrategyFactory.create("nope")


def test_param_out_of_range_and_unknown_param():
    with pytest.raises(ValueError):
        StrategyFactory.create("momentum", {"lookback": 0})
    with pytest.raises(ValueError):
        StrategyFactory.create("momentum", {"bogus": 1})


@pytest.mark.parametrize(
    "key,params",
    [
        ("ema_crossover", {"fast": 30, "slow": 10}),
        ("macd_crossover", {"fast": 30, "slow": 20}),
        ("rsi_reversal", {"oversold": 50, "overbought": 50}),
    ],
)
def test_cross_param_validation(key, params):
    with pytest.raises(ValueError):
        StrategyFactory.create(key, params)


@pytest.mark.parametrize("key", ALL)
def test_holds_during_warmup(key):
    assert run(key, [100.0])[0].action is Action.HOLD


UP = [100 + i for i in range(40)]
DOWN = [140 - i for i in range(40)]


def test_momentum_buy_and_sell():
    assert run("momentum", UP, lookback=5, threshold_pct=1)[-1].action is Action.BUY
    assert run("momentum", DOWN, lookback=5, threshold_pct=1)[-1].action is Action.SELL


def test_breakout_buy_and_sell():
    assert run("breakout", UP, lookback=10)[-1].action is Action.BUY
    assert run("breakout", DOWN, lookback=10)[-1].action is Action.SELL


def test_mean_reversion_buys_dip_sells_spike():
    flat = [100.0] * 20
    assert run("mean_reversion", flat + [95.0], period=20, deviation_pct=2)[-1].action is Action.BUY
    assert run("mean_reversion", flat + [105.0], period=20, deviation_pct=2)[-1].action is Action.SELL


def test_bollinger_band_breaks():
    base = [100.0, 101.0] * 10
    assert run("bollinger", base + [90.0], period=20)[-1].action is Action.BUY
    assert run("bollinger", base + [110.0], period=20)[-1].action is Action.SELL


def test_zscore_extremes():
    base = [100.0, 101.0] * 10
    assert run("zscore", base + [95.0], period=20, entry_z=2)[-1].action is Action.BUY
    assert run("zscore", base + [106.0], period=20, entry_z=2)[-1].action is Action.SELL


def test_rsi_reversal():
    assert run("rsi_reversal", DOWN, period=14)[-1].action is Action.BUY
    assert run("rsi_reversal", UP, period=14)[-1].action is Action.SELL


def test_ema_crossover_detects_cross():
    prices = [100.0] * 30 + [100 - i for i in range(1, 15)] + [86 + 3 * i for i in range(1, 20)]
    acts = actions(run("ema_crossover", prices, fast=3, slow=8))
    assert Action.BUY in acts and Action.SELL in acts


def test_macd_crossover_detects_cross():
    prices = [100.0 + i * 0.5 for i in range(40)] + [120.0 - i for i in range(30)] + [90.0 + i for i in range(30)]
    acts = actions(run("macd_crossover", prices, fast=5, slow=10, signal=4))
    assert Action.BUY in acts and Action.SELL in acts


def test_ensemble_needs_votes():
    sig = run("ensemble", DOWN, min_votes=2)[-1]
    assert sig.action in (Action.BUY, Action.HOLD)
    assert run("ensemble", [100.0] * 40, min_votes=5)[-1].action is Action.HOLD


def test_signal_has_reason():
    s = run("momentum", UP, lookback=5, threshold_pct=1)[-1]
    assert "Momentum" in s.reason


def test_position_tracker_stop_loss_take_profit_trailing():
    t = PositionTracker(ExitRules(stop_loss_pct=2, take_profit_pct=5, trailing_stop_pct=3))
    assert t.check_exit(100) is None
    t.open(100)
    assert "Stop loss" in t.check_exit(97.9)
    t.open(100)
    assert "Take profit" in t.check_exit(105.1)
    t.open(100)
    t.check_exit(104)
    assert "Trailing" in t.check_exit(100.8)


def test_trader_long_only_flow():
    trader = StrategyTrader(
        StrategyFactory.create("momentum", {"lookback": 2, "threshold_pct": 1}), ExitRules(stop_loss_pct=50)
    )
    decisions = [trader.on_price(p) for p in (100, 100, 103)]
    buy = decisions[-1]
    assert buy.action is Action.BUY
    trader.confirm(buy, 103)
    sell = None
    for p in (100, 97, 94):
        sell = trader.on_price(p) or sell
    assert sell.action is Action.SELL
