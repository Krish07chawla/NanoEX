"""StrategyTrader: turns strategy signals + exit rules into long-only trade decisions.
Shared by the live bot runner and the backtester so both behave identically."""

from dataclasses import dataclass

from app.strategies.base import Action, BaseStrategy
from app.strategies.exits import ExitRules, PositionTracker


@dataclass(frozen=True)
class Decision:
    action: Action  # BUY to open, SELL to close
    reason: str


class StrategyTrader:
    def __init__(self, strategy: BaseStrategy, exits: ExitRules | None = None):
        self.strategy = strategy
        self.tracker = PositionTracker(exits or ExitRules())

    @property
    def in_position(self) -> bool:
        return self.tracker.in_position

    def on_price(self, price: float) -> Decision | None:
        signal = self.strategy.update(price)
        if self.tracker.in_position:
            exit_reason = self.tracker.check_exit(price)
            if exit_reason:
                return Decision(Action.SELL, exit_reason)
            if signal.action is Action.SELL:
                return Decision(Action.SELL, signal.reason)
        elif signal.action is Action.BUY:
            return Decision(Action.BUY, signal.reason)
        return None

    def confirm(self, decision: Decision, fill_price: float) -> None:
        """Call after the order actually filled."""
        if decision.action is Action.BUY:
            self.tracker.open(fill_price)
        else:
            self.tracker.close()
