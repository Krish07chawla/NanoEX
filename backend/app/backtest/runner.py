"""Event-driven backtester. Feeds prices bar by bar into the same StrategyTrader the
live bots use, fills at the bar close with slippage, and charges Indian trading costs."""

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.arbitrage.cost_model import CostModel
from app.backtest import metrics as m
from app.core.constants import Exchange, Side
from app.strategies.base import Action
from app.strategies.exits import ExitRules
from app.strategies.factory import StrategyFactory
from app.strategies.trader import StrategyTrader

BPS = 10_000
COST_HEADROOM = 1.002  # keep a little cash for charges when sizing a position


@dataclass
class BacktestConfig:
    strategy_key: str
    params: dict[str, Any] = field(default_factory=dict)
    symbol: str = "RELIANCE"
    exchange: str = Exchange.NSE.value
    initial_capital: float = 500_000.0
    position_size_pct: float = 100.0
    slippage_bps: float = 2.0
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    trailing_stop_pct: float | None = None
    periods_per_year: int = 252


@dataclass
class BacktestReport:
    metrics: dict[str, Any]
    equity_curve: list[dict[str, float]]
    trades: list[dict[str, Any]]


class Backtester:
    def __init__(self, cost_model: CostModel | None = None):
        self.cost_model = cost_model or CostModel()

    def run(self, cfg: BacktestConfig, prices: list[float]) -> BacktestReport:
        if len(prices) < 2:
            raise ValueError("Need at least 2 prices to backtest")
        trader = StrategyTrader(
            StrategyFactory.create(cfg.strategy_key, cfg.params),
            ExitRules(cfg.stop_loss_pct, cfg.take_profit_pct, cfg.trailing_stop_pct),
        )
        cash, qty = cfg.initial_capital, 0
        entry: dict[str, Any] | None = None
        trades: list[dict[str, Any]] = []
        curve: list[dict[str, float]] = []
        total_costs = 0.0
        bars_in_market = 0
        slip = cfg.slippage_bps / BPS

        for i, price in enumerate(prices):
            decision = trader.on_price(price)
            if decision and decision.action is Action.BUY and qty == 0:
                fill = price * (1 + slip)
                size = math.floor(cash * cfg.position_size_pct / 100 / (fill * COST_HEADROOM))
                if size > 0:
                    cost = self._charges(Side.BUY, cfg.exchange, fill, size)
                    cash -= fill * size + cost
                    total_costs += cost
                    qty = size
                    entry = {
                        "entry_index": i,
                        "entry_price": round(fill, 4),
                        "quantity": size,
                        "entry_reason": decision.reason,
                        "entry_cost": cost,
                    }
                    trader.confirm(decision, fill)
            elif decision and decision.action is Action.SELL and qty > 0 and entry:
                fill = price * (1 - slip)
                cost = self._charges(Side.SELL, cfg.exchange, fill, qty)
                cash += fill * qty - cost
                total_costs += cost
                trades.append(self._close(entry, i, fill, qty, cost, decision.reason))
                qty, entry = 0, None
                trader.confirm(decision, fill)
            bars_in_market += 1 if qty else 0
            curve.append({"i": i, "price": round(price, 4), "equity": round(cash + qty * price, 2)})

        if qty and entry:  # close any open position at the last price
            fill = prices[-1] * (1 - slip)
            cost = self._charges(Side.SELL, cfg.exchange, fill, qty)
            cash += fill * qty - cost
            total_costs += cost
            trades.append(self._close(entry, len(prices) - 1, fill, qty, cost, "End of data"))
            curve[-1]["equity"] = round(cash, 2)

        bh_qty = math.floor(cfg.initial_capital / (prices[0] * COST_HEADROOM))
        for point in curve:
            point["buy_hold"] = round(cfg.initial_capital - bh_qty * prices[0] + bh_qty * point["price"], 2)

        return BacktestReport(self._metrics(cfg, curve, trades, total_costs, bars_in_market, prices), curve, trades)

    def _charges(self, side: Side, exchange: str, price: float, qty: int) -> float:
        return float(self.cost_model.leg_costs(side, exchange, Decimal(str(round(price, 4))), qty).charges)

    @staticmethod
    def _close(entry: dict, i: int, fill: float, qty: int, cost: float, reason: str) -> dict:
        pnl = (fill - entry["entry_price"]) * qty - entry["entry_cost"] - cost
        return {
            **{k: v for k, v in entry.items() if k != "entry_cost"},
            "exit_index": i,
            "exit_price": round(fill, 4),
            "exit_reason": reason,
            "costs": round(entry["entry_cost"] + cost, 2),
            "pnl": round(pnl, 2),
            "return_pct": round((fill / entry["entry_price"] - 1) * 100, 3),
        }

    @staticmethod
    def _metrics(cfg: BacktestConfig, curve, trades, total_costs, bars_in_market, prices) -> dict[str, Any]:
        equity = [p["equity"] for p in curve]
        rets = m.returns(equity)
        pnls = [t["pnl"] for t in trades]
        final = equity[-1]
        bh_final = curve[-1]["buy_hold"]
        return {
            "initial_capital": cfg.initial_capital,
            "final_equity": round(final, 2),
            "total_return_pct": round((final / cfg.initial_capital - 1) * 100, 4),
            "buy_hold_return_pct": round((bh_final / cfg.initial_capital - 1) * 100, 4),
            "win_rate_pct": m.win_rate_pct(pnls),
            "max_drawdown_pct": m.max_drawdown_pct(equity),
            "sharpe": m.sharpe(rets, cfg.periods_per_year),
            "sortino": m.sortino(rets, cfg.periods_per_year),
            "profit_factor": m.profit_factor(pnls),
            "num_trades": len(trades),
            "avg_trade_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "total_costs": round(total_costs, 2),
            "exposure_pct": round(100 * bars_in_market / len(prices), 2),
            "bars": len(prices),
        }
