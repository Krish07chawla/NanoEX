"""Stop-loss, take-profit and trailing-stop handling for a long position."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitRules:
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    trailing_stop_pct: float | None = None


class PositionTracker:
    """Tracks one long position (entry and peak) and reports when an exit rule fires."""

    def __init__(self, rules: ExitRules):
        self.rules = rules
        self.entry: float | None = None
        self.peak: float | None = None

    @property
    def in_position(self) -> bool:
        return self.entry is not None

    def open(self, price: float) -> None:
        self.entry = self.peak = price

    def close(self) -> None:
        self.entry = self.peak = None

    def check_exit(self, price: float) -> str | None:
        if self.entry is None or self.peak is None:
            return None
        self.peak = max(self.peak, price)
        change = (price / self.entry - 1) * 100
        r = self.rules
        if r.stop_loss_pct and change <= -r.stop_loss_pct:
            return f"Stop loss hit ({change:.2f}%)"
        if r.take_profit_pct and change >= r.take_profit_pct:
            return f"Take profit hit (+{change:.2f}%)"
        if r.trailing_stop_pct:
            drawdown = (price / self.peak - 1) * 100
            if drawdown <= -r.trailing_stop_pct:
                return f"Trailing stop hit ({drawdown:.2f}% from peak {self.peak:.2f})"
        return None
