import pytest

from app.backtest import metrics as m
from app.backtest.data_loader import load_prices
from app.backtest.runner import BacktestConfig, Backtester
from app.core.exceptions import ValidationFailed


def test_metrics_helpers():
    assert m.max_drawdown_pct([100, 120, 90, 130]) == -25.0
    assert m.win_rate_pct([10, -5, 3, 0]) == 50.0
    assert m.profit_factor([10, -5]) == 2.0
    assert m.profit_factor([10, 5]) is None
    assert m.sharpe([0.01, 0.01], 252) == 0.0
    assert m.sharpe([0.01, -0.005, 0.02], 252) > 0
    assert m.sortino([0.01, 0.02], 252) == 0.0
    assert m.returns([100, 110]) == [pytest.approx(0.1)]


def test_seeded_data_is_reproducible():
    assert load_prices("TCS", 100, seed=3) == load_prices("TCS", 100, seed=3)
    assert load_prices("TCS", 100, seed=3) != load_prices("TCS", 100, seed=4)


def test_unknown_symbol_or_source():
    with pytest.raises(ValidationFailed):
        load_prices("NOPE", 10)
    with pytest.raises(ValidationFailed):
        load_prices("TCS", 10, source="csv")


def test_runner_produces_metrics_and_costs():
    prices = load_prices("RELIANCE", 400, seed=11)
    report = Backtester().run(BacktestConfig("ema_crossover", {"fast": 5, "slow": 20}), prices)
    mt = report.metrics
    assert mt["num_trades"] == len(report.trades) > 0
    assert mt["total_costs"] > 0
    assert len(report.equity_curve) == 400 and "buy_hold" in report.equity_curve[0]
    for key in (
        "total_return_pct",
        "win_rate_pct",
        "max_drawdown_pct",
        "sharpe",
        "sortino",
        "profit_factor",
        "buy_hold_return_pct",
    ):
        assert key in mt


def test_runner_is_deterministic():
    prices = load_prices("INFY", 300, seed=5)
    cfg = BacktestConfig("rsi_reversal", stop_loss_pct=3)
    assert Backtester().run(cfg, prices).metrics == Backtester().run(cfg, prices).metrics


def test_open_position_closed_at_end():
    prices = [100.0 + i for i in range(30)]
    report = Backtester().run(BacktestConfig("momentum", {"lookback": 3, "threshold_pct": 0.5}), prices)
    assert report.trades[-1]["exit_reason"] == "End of data"
    assert report.metrics["total_return_pct"] > 0


def test_needs_two_prices():
    with pytest.raises(ValueError):
        Backtester().run(BacktestConfig("momentum"), [100.0])
